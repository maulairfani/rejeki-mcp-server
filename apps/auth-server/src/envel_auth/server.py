"""
Finance MCP — Authorization Server
Handles OAuth 2.1 flow for MCP client integration.

Flow:
  MCP client → /auth/.well-known/oauth-authorization-server  (discovery)
  MCP client → /auth/register                                 (dynamic client reg)
  MCP client → /auth/authorize  → browser login form
  user       → POST /auth/login/callback  (username + password)
  MCP client → /auth/token                                    (code → token)
  mcp server → /auth/introspect                               (token validation)
"""

import logging
import os
import secrets
import sqlite3
import time
from typing import Any

import bcrypt
from pydantic import AnyHttpUrl
from pythonjsonlogger.json import JsonFormatter
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.server.auth.routes import cors_middleware, create_auth_routes
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

logger = logging.getLogger("envel_auth")

# ─── CONFIG ──────────────────────────────────────────────────────────────────

USERS_DB = os.environ.get("USERS_DB")
if not USERS_DB:
    raise RuntimeError("USERS_DB env var must be set to the path of users.db")
PLATFORM_SERVICE_SECRET = os.environ.get("PLATFORM_SERVICE_SECRET", "")
AS_BASE_URL = os.environ.get("AS_BASE_URL", "https://envel.dev/auth")
PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://platform.envel.dev")
MCP_SCOPE = "envel"

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = f"{AS_BASE_URL}/google/callback"
PLATFORM_GOOGLE_REDIRECT_URI = f"{AS_BASE_URL}/platform/google/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile https://www.googleapis.com/auth/drive.file"

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    username             TEXT PRIMARY KEY,
    name                 TEXT,
    email                TEXT COLLATE NOCASE,
    password_hash        TEXT,
    db_path              TEXT NOT NULL,
    google_sub           TEXT,
    google_email         TEXT,
    google_refresh_token TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    first_connected_at   TEXT,
    last_active_at       TEXT
);
"""

CREATE_AUTH_TABLES = """
CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id   TEXT PRIMARY KEY,
    client_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token      TEXT PRIMARY KEY,
    client_id  TEXT NOT NULL,
    username   TEXT NOT NULL,
    scopes     TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    resource   TEXT
);
"""

TOKEN_TTL = 3600 * 24 * 30  # 30 days


def _get_users_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(CREATE_USERS_TABLE)
    conn.executescript(CREATE_AUTH_TABLES)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Auto-apply schema changes. Safe to run repeatedly."""
    for col, definition in [
        ("name",                 "TEXT"),
        ("email",                "TEXT COLLATE NOCASE"),
        ("google_sub",           "TEXT"),
        ("google_email",         "TEXT"),
        ("google_refresh_token", "TEXT"),
        ("first_connected_at",   "TEXT"),
        ("last_active_at",       "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
    # Also ensure partial unique indexes exist on migrated tables
    for stmt in [
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email      ON users(email)      WHERE email      IS NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL",
    ]:
        try:
            conn.execute(stmt)
            conn.commit()
        except sqlite3.OperationalError:
            pass


def _get_user(username: str) -> dict | None:
    with _get_users_conn() as conn:
        row = conn.execute(
            "SELECT username, password_hash, db_path FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(row) if row else None


_USERNAME_SAFE_RE = __import__("re").compile(r"[^a-zA-Z0-9_-]")


def _suggest_username(email: str) -> str:
    """Generate a unique username from an email address.

    Strips the local-part of the email, removes disallowed chars, trims to 32 chars,
    and appends a counter if the candidate is taken. Returns a string that is
    guaranteed to be available in users.db at call time.
    """
    local = (email or "").split("@", 1)[0].lower()
    candidate = _USERNAME_SAFE_RE.sub("", local)[:32]
    if len(candidate) < 3:
        candidate = "user"
    base = candidate
    with _get_users_conn() as conn:
        i = 1
        while True:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ? LIMIT 1", (candidate,)
            ).fetchone()
            if row is None:
                return candidate
            i += 1
            candidate = f"{base}{i}"[:32]


def _default_user_db_path(username: str) -> str:
    """Mirror scripts/add_user.py: <project_root>/users/<username>.db"""
    from pathlib import Path
    root = Path(__file__).resolve().parents[4]  # apps/auth-server/src/envel_auth/server.py → up 4 to project root
    return str(root / "users" / f"{username}.db")


def _init_user_db_file(db_path: str, username: str) -> None:
    """Create the user's per-user SQLite DB file, encrypted if DB_ENCRYPTION_KEY set."""
    from pathlib import Path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    master = os.environ.get("DB_ENCRYPTION_KEY")
    if master:
        try:
            import hashlib
            import hmac
            import sqlcipher3  # type: ignore[import-not-found]
            key = hmac.new(master.encode(), username.encode(), hashlib.sha256).hexdigest()
            conn = sqlcipher3.connect(db_path)
            conn.execute(f"PRAGMA key = '{key}'")
            conn.close()
            return
        except ImportError:
            logger.warning("sqlcipher_missing", extra={"username": username})
    conn = sqlite3.connect(db_path)
    conn.close()


def _create_google_user(
    username: str,
    name: str,
    email: str,
    google_sub: str,
    refresh_token: str | None,
) -> str:
    """Create a new user record for a Google-authenticated signup. Returns the username."""
    db_path = _default_user_db_path(username)
    with _get_users_conn() as conn:
        conn.execute(
            """INSERT INTO users (username, name, email, db_path, google_sub, google_email, google_refresh_token)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (username, name, email, db_path, google_sub, email, refresh_token or None),
        )
        conn.commit()
    _init_user_db_file(db_path, username)
    logger.info("google_signup_success", extra={"username": username, "email": email})
    return username


# ─── OAUTH PROVIDER ──────────────────────────────────────────────────────────

class EnvelOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """OAuth provider backed by users.db credentials. Clients and tokens are persisted to SQLite."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        # Short-lived state — in-memory only (minutes lifetime, no need to persist)
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.state_mapping: dict[str, dict[str, Any]] = {}
        # Google OAuth (MCP flow): maps google_state → mcp_state
        self.google_state_mapping: dict[str, str] = {}
        # Pending account links: maps link_token → google user info + mcp_state
        self.pending_links: dict[str, dict[str, Any]] = {}
        # Platform Google OAuth state: maps google_state → {intent}
        self.platform_google_state: dict[str, dict[str, Any]] = {}
        # Pending platform Google signups: handoff_token → {google_sub, google_email, google_name, refresh_token, suggested_username, expires_at}
        self.pending_platform_signups: dict[str, dict[str, Any]] = {}
        # Pending platform Google logins: handoff_token → {username, expires_at}
        self.pending_platform_logins: dict[str, dict[str, Any]] = {}

    def _check_credentials(self, username: str, password: str) -> bool:
        user = _get_user(username)
        if not user:
            logger.warning("login_failed", extra={"username": username, "reason": "unknown_user"})
            return False
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            logger.warning("login_failed", extra={"username": username, "reason": "bad_password"})
            return False
        logger.info("login_success", extra={"username": username})
        return True

    # ── OAuthAuthorizationServerProvider interface ──

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT client_json FROM oauth_clients WHERE client_id = ?", (client_id,)
            ).fetchone()
        if not row:
            return None
        return OAuthClientInformationFull.model_validate_json(row["client_json"])

    async def register_client(self, client_info: OAuthClientInformationFull):
        if not client_info.client_id:
            raise ValueError("No client_id")
        with _get_users_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO oauth_clients (client_id, client_json) VALUES (?, ?)",
                (client_info.client_id, client_info.model_dump_json()),
            )
            conn.commit()

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        state = params.state or secrets.token_hex(16)
        self.state_mapping[state] = {
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": str(params.redirect_uri_provided_explicitly),
            "client_id": client.client_id,
            "resource": params.resource,
        }
        return f"{self.base_url}/login?state={state}&client_id={client.client_id}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        if authorization_code.code not in self.auth_codes:
            raise ValueError("Invalid authorization code")
        if not client.client_id:
            raise ValueError("No client_id")

        token_str = f"envel_{secrets.token_hex(32)}"
        username = getattr(authorization_code, "_username", "unknown")
        expires_at = int(time.time()) + TOKEN_TTL
        scopes_str = " ".join(authorization_code.scopes)
        resource = str(authorization_code.resource) if authorization_code.resource else None

        with _get_users_conn() as conn:
            conn.execute(
                """INSERT INTO oauth_tokens (token, client_id, username, scopes, expires_at, resource)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (token_str, client.client_id, username, scopes_str, expires_at, resource),
            )
            conn.commit()

        del self.auth_codes[authorization_code.code]
        logger.info("token_issued", extra={"username": username, "client_id": client.client_id})

        return OAuthToken(
            access_token=token_str,
            token_type="Bearer",
            expires_in=TOKEN_TTL,
            scope=scopes_str,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT * FROM oauth_tokens WHERE token = ?", (token,)
            ).fetchone()
        if not row:
            return None
        if row["expires_at"] < time.time():
            with _get_users_conn() as conn:
                conn.execute("DELETE FROM oauth_tokens WHERE token = ?", (token,))
                conn.commit()
            return None
        return AccessToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=row["scopes"].split(),
            expires_at=row["expires_at"],
            resource=row["resource"],
        )

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        raise NotImplementedError

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT username FROM oauth_tokens WHERE token = ?", (token,)
            ).fetchone()
            username = row["username"] if row else "unknown"
            conn.execute("DELETE FROM oauth_tokens WHERE token = ?", (token,))
            conn.commit()
        logger.info("token_revoked", extra={"username": username})

    # ── Google OAuth flow ──

    async def handle_google_authorize(self, request: Request) -> Response:
        """Step 1: redirect to Google, embedding the MCP state."""
        mcp_state = request.query_params.get("mcp_state")
        if not mcp_state or mcp_state not in self.state_mapping:
            raise HTTPException(400, "Invalid MCP state")

        google_state = secrets.token_hex(16)
        self.google_state_mapping[google_state] = mcp_state

        import urllib.parse
        params = urllib.parse.urlencode({
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": google_state,
        })
        return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}", status_code=302)

    async def handle_google_callback(self, request: Request) -> Response:
        """Step 2: Google redirects back here with auth code."""
        import httpx

        code = request.query_params.get("code")
        google_state = request.query_params.get("state")

        if not code or not google_state:
            raise HTTPException(400, "Missing code or state from Google")

        mcp_state = self.google_state_mapping.pop(google_state, None)
        if not mcp_state or mcp_state not in self.state_mapping:
            raise HTTPException(400, "Expired or invalid state")

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            if token_resp.status_code != 200:
                raise HTTPException(502, "Google token exchange failed")
            token_data = token_resp.json()

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(502, "Google userinfo fetch failed")
            userinfo = userinfo_resp.json()

        google_sub = userinfo["sub"]
        google_email = userinfo.get("email", "")
        refresh_token = token_data.get("refresh_token", "")

        # Find user by google_sub or email
        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT username FROM users WHERE google_sub = ? OR google_email = ?",
                (google_sub, google_email),
            ).fetchone()

        if row:
            # Known user — update tokens and complete MCP flow
            with _get_users_conn() as conn:
                conn.execute(
                    """UPDATE users SET google_sub = ?, google_email = ?, google_refresh_token = ?
                       WHERE username = ?""",
                    (google_sub, google_email, refresh_token or None, row["username"]),
                )
                conn.commit()
            return self._complete_mcp_flow(mcp_state, row["username"])

        # Unknown Google account — ask user to link to existing account
        link_token = secrets.token_hex(16)
        self.pending_links[link_token] = {
            "google_sub": google_sub,
            "google_email": google_email,
            "refresh_token": refresh_token,
            "mcp_state": mcp_state,
        }
        return HTMLResponse(self._link_page_html(link_token, google_email))

    async def handle_link_callback(self, request: Request) -> Response:
        """User enters username/password to link their existing account to Google."""
        form = await request.form()
        link_token = str(form.get("link_token", ""))
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        pending = self.pending_links.get(link_token)
        if not pending:
            raise HTTPException(400, "Expired link session — please try again")

        if not self._check_credentials(username, password):
            return HTMLResponse(
                self._link_page_html(link_token, pending["google_email"], error=True),
                status_code=401,
            )

        # Link Google account to this user
        with _get_users_conn() as conn:
            conn.execute(
                """UPDATE users SET google_sub = ?, google_email = ?, google_refresh_token = ?
                   WHERE username = ?""",
                (pending["google_sub"], pending["google_email"], pending["refresh_token"] or None, username),
            )
            conn.commit()

        del self.pending_links[link_token]
        logger.info("google_account_linked", extra={"username": username, "google_email": pending["google_email"]})
        return self._complete_mcp_flow(pending["mcp_state"], username)

    # ── Platform Google OAuth flow (signup/login via platform.envel.dev) ──

    async def handle_platform_google_authorize(self, request: Request) -> Response:
        """Start Google OAuth for platform signup/login (separate from MCP flow)."""
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(503, "Google OAuth is not configured")
        intent = request.query_params.get("intent", "signup")
        if intent not in ("signup", "login"):
            intent = "signup"

        google_state = secrets.token_hex(16)
        self.platform_google_state[google_state] = {
            "intent": intent,
            "created_at": time.time(),
        }

        import urllib.parse
        params = urllib.parse.urlencode({
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": PLATFORM_GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "access_type": "offline",
            "prompt": "select_account",
            "state": google_state,
        })
        return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}", status_code=302)

    async def handle_platform_google_callback(self, request: Request) -> Response:
        """Google redirects here after user consents in the platform signup/login flow."""
        import httpx

        code = request.query_params.get("code")
        google_state = request.query_params.get("state")
        if not code or not google_state:
            raise HTTPException(400, "Missing code or state")

        meta = self.platform_google_state.pop(google_state, None)
        if not meta:
            raise HTTPException(400, "Expired or invalid state")

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": PLATFORM_GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            if token_resp.status_code != 200:
                raise HTTPException(502, "Google token exchange failed")
            token_data = token_resp.json()

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(502, "Google userinfo fetch failed")
            userinfo = userinfo_resp.json()

        google_sub = userinfo["sub"]
        google_email = (userinfo.get("email") or "").lower()
        google_name = userinfo.get("name") or google_email.split("@", 1)[0]
        refresh_token = token_data.get("refresh_token", "")

        # Look up existing user by google_sub or email
        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT username FROM users WHERE google_sub = ? OR email = ? LIMIT 1",
                (google_sub, google_email),
            ).fetchone()

        if row:
            # Existing user — log them in. Also ensure google_sub and refresh_token are stored.
            username = row["username"]
            with _get_users_conn() as conn:
                conn.execute(
                    """UPDATE users SET
                         google_sub = COALESCE(google_sub, ?),
                         google_email = COALESCE(google_email, ?),
                         google_refresh_token = COALESCE(?, google_refresh_token)
                       WHERE username = ?""",
                    (google_sub, google_email, refresh_token or None, username),
                )
                conn.commit()
            handoff = f"gh_login_{secrets.token_hex(32)}"
            self.pending_platform_logins[handoff] = {
                "username": username,
                "expires_at": time.time() + 300,
            }
            logger.info("platform_google_login", extra={"username": username})
            return RedirectResponse(
                url=f"{PLATFORM_URL}/api/auth/google-handoff?token={handoff}",
                status_code=302,
            )

        # New Google user — stage a pending signup. Platform confirms username before creation.
        suggested = _suggest_username(google_email)
        handoff = f"gh_signup_{secrets.token_hex(32)}"
        self.pending_platform_signups[handoff] = {
            "google_sub": google_sub,
            "google_email": google_email,
            "google_name": google_name,
            "refresh_token": refresh_token,
            "suggested_username": suggested,
            "expires_at": time.time() + 600,
        }
        logger.info("platform_google_pending_signup", extra={"email": google_email, "suggested": suggested})
        return RedirectResponse(
            url=f"{PLATFORM_URL}/api/auth/google-handoff?token={handoff}",
            status_code=302,
        )

    def _check_service_secret(self, body: dict) -> None:
        if not PLATFORM_SERVICE_SECRET:
            raise HTTPException(503, "Service endpoint not configured")
        if body.get("service_secret", "") != PLATFORM_SERVICE_SECRET:
            raise HTTPException(403, "Forbidden")

    async def handle_platform_handoff_resolve(self, request: Request) -> Response:
        """Platform calls this to exchange a handoff token for user info.

        For login handoffs: returns {type:'login', username}.
        For signup handoffs: returns {type:'signup', google_email, google_name, suggested_username}.
        The handoff token remains valid until TTL so platform can call signup-complete.
        """
        body = await request.json()
        self._check_service_secret(body)
        token = body.get("token", "")
        now = time.time()

        login = self.pending_platform_logins.get(token)
        if login:
            if login["expires_at"] < now:
                self.pending_platform_logins.pop(token, None)
                return JSONResponse({"error": "expired"}, status_code=410)
            # Login handoffs are one-shot
            self.pending_platform_logins.pop(token, None)
            return JSONResponse({"type": "login", "username": login["username"]})

        signup = self.pending_platform_signups.get(token)
        if signup:
            if signup["expires_at"] < now:
                self.pending_platform_signups.pop(token, None)
                return JSONResponse({"error": "expired"}, status_code=410)
            return JSONResponse({
                "type": "signup",
                "google_email": signup["google_email"],
                "google_name": signup["google_name"],
                "suggested_username": signup["suggested_username"],
            })

        return JSONResponse({"error": "not_found"}, status_code=404)

    async def handle_platform_signup_complete(self, request: Request) -> Response:
        """Platform calls this with token + chosen username to create the user."""
        body = await request.json()
        self._check_service_secret(body)
        token = body.get("token", "")
        username = (body.get("username") or "").strip()

        pending = self.pending_platform_signups.get(token)
        if not pending:
            return JSONResponse({"error": "not_found"}, status_code=404)
        if pending["expires_at"] < time.time():
            self.pending_platform_signups.pop(token, None)
            return JSONResponse({"error": "expired"}, status_code=410)

        import re as _re
        if not _re.match(r"^[a-zA-Z0-9_-]{3,32}$", username):
            return JSONResponse({"error": "invalid_username"}, status_code=400)

        with _get_users_conn() as conn:
            taken = conn.execute(
                "SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,)
            ).fetchone()
        if taken:
            return JSONResponse({"error": "username_taken"}, status_code=409)

        try:
            _create_google_user(
                username=username,
                name=pending["google_name"],
                email=pending["google_email"],
                google_sub=pending["google_sub"],
                refresh_token=pending["refresh_token"],
            )
        except sqlite3.IntegrityError as e:
            logger.warning("google_signup_conflict", extra={"email": pending["google_email"], "err": str(e)})
            return JSONResponse({"error": "conflict"}, status_code=409)

        self.pending_platform_signups.pop(token, None)
        return JSONResponse({"username": username})

    async def handle_platform_connection_status(self, request: Request) -> Response:
        """Platform calls this to check whether a user has ever used the MCP server."""
        body = await request.json()
        self._check_service_secret(body)
        username = (body.get("username") or "").strip()
        if not username:
            return JSONResponse({"error": "missing_username"}, status_code=400)
        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT first_connected_at, last_active_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not row:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return JSONResponse({
            "username": username,
            "first_connected_at": row["first_connected_at"],
            "last_active_at": row["last_active_at"],
        })

    def _complete_mcp_flow(self, mcp_state: str, username: str) -> Response:
        """Issue MCP auth code and redirect back to MCP client."""
        state_data = self.state_mapping.get(mcp_state)
        if not state_data:
            raise HTTPException(400, "MCP state expired")

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = state_data["redirect_uri_provided_explicitly"] == "True"
        client_id = state_data["client_id"]
        resource = state_data.get("resource")

        code_str = f"code_{secrets.token_hex(16)}"
        auth_code = AuthorizationCode(
            code=code_str,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,
            scopes=[MCP_SCOPE],
            code_challenge=code_challenge,
            resource=resource,
        )
        auth_code._username = username  # type: ignore[attr-defined]
        self.auth_codes[code_str] = auth_code
        del self.state_mapping[mcp_state]

        redirect = construct_redirect_uri(redirect_uri, code=code_str, state=mcp_state)
        return RedirectResponse(url=redirect, status_code=302)

    # ── Login flow ──

    def _auth_shell(self, title: str, body: str) -> str:
        """Shared HTML shell for auth pages (Envel design system)."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --brand: oklch(50% 0.16 145);
      --brand-hover: oklch(44% 0.16 145);
      --brand-light: oklch(94% 0.06 145);
      --brand-text: oklch(36% 0.13 145);

      --bg: oklch(97% 0.012 75);
      --bg-surface: oklch(99.5% 0.008 75);
      --bg-elevated: oklch(100% 0 0);
      --bg-muted: oklch(94% 0.014 75);

      --text-primary: oklch(18% 0.018 65);
      --text-secondary: oklch(46% 0.015 65);
      --text-muted: oklch(62% 0.012 65);
      --text-placeholder: oklch(74% 0.01 65);

      --border: oklch(90% 0.012 75);
      --border-muted: oklch(93% 0.01 75);

      --danger: oklch(52% 0.19 25);
      --danger-light: oklch(95% 0.06 25);

      --shadow-md: 0 4px 16px oklch(0% 0 0 / 0.1), 0 0 0 1px oklch(0% 0 0 / 0.04);
      --font: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: oklch(12% 0.015 55);
        --bg-surface: oklch(15.5% 0.018 55);
        --bg-elevated: oklch(18.5% 0.02 55);
        --bg-muted: oklch(20% 0.018 55);
        --brand-light: oklch(22% 0.08 145);
        --brand-text: oklch(72% 0.14 145);
        --text-primary: oklch(93% 0.01 75);
        --text-secondary: oklch(68% 0.012 70);
        --text-muted: oklch(52% 0.01 65);
        --text-placeholder: oklch(42% 0.01 65);
        --border: oklch(24% 0.018 55);
        --border-muted: oklch(21% 0.015 55);
        --danger: oklch(62% 0.19 25);
        --danger-light: oklch(26% 0.08 25);
        --shadow-md: 0 4px 16px oklch(0% 0 0 / 0.35), 0 0 0 1px oklch(100% 0 0 / 0.04);
      }}
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; }}
    body {{
      font-family: var(--font);
      color: var(--text-primary);
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
      display: flex; align-items: center; justify-content: center;
      padding: 24px;
      font-size: 14px;
    }}
    .auth-wrap {{ width: 380px; max-width: 100%; display: flex; flex-direction: column; align-items: center; }}
    .auth-head {{ margin-bottom: 28px; display: flex; flex-direction: column; align-items: center; gap: 12px; }}
    .logo-mark {{
      width: 52px; height: 52px; border-radius: 16px;
      background: var(--brand);
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 8px 24px oklch(50% 0.16 145 / 0.35);
    }}
    .auth-title {{ text-align: center; }}
    .auth-title h1 {{ font-weight: 800; font-size: 22px; color: var(--text-primary); line-height: 1.2; }}
    .auth-title p {{ font-size: 13.5px; color: var(--text-muted); margin-top: 4px; }}
    .auth-card {{
      width: 100%;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 28px 28px 24px;
      box-shadow: var(--shadow-md);
    }}
    form {{ display: flex; flex-direction: column; gap: 16px; }}
    label {{ display: block; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }}
    input[type=text], input[type=password] {{
      width: 100%; padding: 10px 14px;
      background: var(--bg);
      border: 1.5px solid var(--border);
      border-radius: 10px;
      font-family: var(--font);
      font-size: 14px;
      color: var(--text-primary);
      transition: border-color 120ms;
    }}
    input::placeholder {{ color: var(--text-placeholder); }}
    input:focus {{ outline: none; border-color: var(--brand); }}
    .email-pill {{
      font-weight: 600; color: var(--text-primary); font-size: 14px;
      padding: 8px 14px; background: var(--bg-muted); border-radius: 10px;
      word-break: break-all;
    }}
    .btn-primary {{
      margin-top: 4px; padding: 11px; border-radius: 10px;
      background: var(--brand); color: #fff;
      font-family: var(--font); font-size: 14.5px; font-weight: 700;
      border: none; cursor: pointer;
      transition: background 120ms, box-shadow 120ms;
      box-shadow: 0 2px 8px oklch(50% 0.16 145 / 0.3);
    }}
    .btn-primary:hover {{ background: var(--brand-hover); }}
    .error {{
      font-size: 12.5px; font-weight: 500; color: var(--danger);
      background: var(--danger-light); padding: 8px 12px; border-radius: 8px;
    }}
    .divider {{
      display: flex; align-items: center; gap: 10px;
      margin: 4px 0;
      color: var(--text-muted); font-size: 12px; font-weight: 500;
    }}
    .divider::before, .divider::after {{
      content: ""; flex: 1; height: 1px; background: var(--border);
    }}
    .google-btn {{
      display: flex; align-items: center; justify-content: center; gap: 10px;
      width: 100%; padding: 10px 14px;
      background: var(--bg-elevated);
      border: 1.5px solid var(--border);
      border-radius: 10px;
      color: var(--text-primary);
      font-family: var(--font); font-size: 14px; font-weight: 600;
      text-decoration: none;
      transition: background 120ms, border-color 120ms;
      cursor: pointer;
    }}
    .google-btn:hover {{ background: var(--bg-muted); border-color: var(--text-muted); }}
    .context-note {{
      font-size: 12.5px; color: var(--text-muted);
      text-align: center; margin-bottom: 8px;
    }}
  </style>
</head>
<body>
  {body}
</body>
</html>"""

    def _logo_mark_svg(self) -> str:
        """Envelope mark matching platform LogoMark (Option C)."""
        return (
            '<svg width="32" height="32" viewBox="0 0 48 48" fill="none" aria-hidden="true">'
            '<rect x="8" y="16" width="32" height="22" rx="4" fill="white" fill-opacity="0.2"/>'
            '<path d="M8 20 L24 30 L40 20 L40 16 Q40 12 36 12 L12 12 Q8 12 8 16 Z" fill="white" fill-opacity="0.95"/>'
            '<path d="M8 34 L16 26 M40 34 L32 26" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>'
            '</svg>'
        )

    def login_page_html(self, state: str, error: bool = False) -> str:
        error_html = '<p class="error">Invalid username or password.</p>' if error else ""
        google_section = ""
        if GOOGLE_CLIENT_ID:
            google_section = f"""
        <div class="divider"><span>or</span></div>
        <a href="{self.base_url}/google/authorize?mcp_state={state}" class="google-btn">
          <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
          Continue with Google
        </a>"""

        body = f"""
  <main class="auth-wrap">
    <div class="auth-head">
      <div class="logo-mark">{self._logo_mark_svg()}</div>
      <div class="auth-title">
        <h1>Welcome back</h1>
        <p>Sign in to your Envel account</p>
      </div>
    </div>
    <div class="auth-card">
      <form method="post" action="{self.base_url}/login/callback">
        <input type="hidden" name="state" value="{state}">
        <div>
          <label for="username">Username</label>
          <input id="username" type="text" name="username" autofocus required autocomplete="username" placeholder="Your username">
        </div>
        <div>
          <label for="password">Password</label>
          <input id="password" type="password" name="password" required autocomplete="current-password" placeholder="••••••••">
        </div>
        {error_html}
        <button type="submit" class="btn-primary">Sign in</button>
        {google_section}
      </form>
    </div>
  </main>"""
        return self._auth_shell("Envel — Sign In", body)

    def _link_page_html(self, link_token: str, google_email: str, error: bool = False) -> str:
        error_html = '<p class="error">Invalid username or password.</p>' if error else ""
        # Escape email for safety (very basic — just for display)
        safe_email = google_email.replace("<", "&lt;").replace(">", "&gt;")
        body = f"""
  <main class="auth-wrap">
    <div class="auth-head">
      <div class="logo-mark">{self._logo_mark_svg()}</div>
      <div class="auth-title">
        <h1>Link your account</h1>
        <p>Signed in with Google as</p>
      </div>
    </div>
    <div class="auth-card">
      <div class="email-pill" style="margin-bottom:18px;">{safe_email}</div>
      <p class="context-note">Enter your existing Envel credentials to link this Google account.</p>
      <form method="post" action="{self.base_url}/link/callback">
        <input type="hidden" name="link_token" value="{link_token}">
        <div>
          <label for="username">Username</label>
          <input id="username" type="text" name="username" autofocus required autocomplete="username" placeholder="Your username">
        </div>
        <div>
          <label for="password">Password</label>
          <input id="password" type="password" name="password" required autocomplete="current-password" placeholder="••••••••">
        </div>
        {error_html}
        <button type="submit" class="btn-primary">Link &amp; Sign in</button>
      </form>
    </div>
  </main>"""
        return self._auth_shell("Envel — Link Account", body)

    async def handle_login(self, request: Request) -> Response:
        state = request.query_params.get("state")
        if not state or state not in self.state_mapping:
            raise HTTPException(400, "Invalid state")
        return HTMLResponse(self.login_page_html(state))

    async def handle_login_callback(self, request: Request) -> Response:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        state = str(form.get("state", ""))

        state_data = self.state_mapping.get(state)
        if not state_data:
            raise HTTPException(400, "Invalid state")

        if not self._check_credentials(username, password):
            return HTMLResponse(self.login_page_html(state, error=True), status_code=401)

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = state_data["redirect_uri_provided_explicitly"] == "True"
        client_id = state_data["client_id"]
        resource = state_data.get("resource")

        assert redirect_uri and code_challenge and client_id

        code_str = f"code_{secrets.token_hex(16)}"
        auth_code = AuthorizationCode(
            code=code_str,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,
            scopes=[MCP_SCOPE],
            code_challenge=code_challenge,
            resource=resource,
        )
        auth_code._username = username  # type: ignore[attr-defined]
        self.auth_codes[code_str] = auth_code

        del self.state_mapping[state]
        redirect = construct_redirect_uri(redirect_uri, code=code_str, state=state)
        return RedirectResponse(url=redirect, status_code=302)


# ─── INTROSPECT ENDPOINT ─────────────────────────────────────────────────────

def make_introspect_handler(provider: EnvelOAuthProvider):
    async def introspect(request: Request) -> Response:
        form = await request.form()
        token = form.get("token")
        if not token or not isinstance(token, str):
            return JSONResponse({"active": False})

        access_token = await provider.load_access_token(token)
        if not access_token:
            logger.debug("introspect_inactive", extra={"token_prefix": str(token)[:12]})
            return JSONResponse({"active": False})

        with _get_users_conn() as conn:
            row = conn.execute(
                "SELECT username FROM oauth_tokens WHERE token = ?", (token,)
            ).fetchone()
            username = row["username"] if row else "unknown"
            conn.execute(
                """UPDATE users
                   SET last_active_at = datetime('now'),
                       first_connected_at = COALESCE(first_connected_at, datetime('now'))
                   WHERE username = ?""",
                (username,),
            )
            conn.commit()
        user = _get_user(username)
        db_path = user["db_path"] if user else ""

        logger.debug("introspect_ok", extra={"username": username})

        return JSONResponse({
            "active": True,
            "client_id": access_token.client_id,
            "scope": " ".join(access_token.scopes),
            "exp": access_token.expires_at,
            "token_type": "Bearer",
            "username": username,
            "db": db_path,
        })

    return introspect


# ─── SERVICE TOKEN ENDPOINT ──────────────────────────────────────────────────

def make_service_token_handler(provider: EnvelOAuthProvider):
    """Allows trusted platform backend to mint a token for a user without browser OAuth."""

    async def service_token(request: Request) -> Response:
        if not PLATFORM_SERVICE_SECRET:
            return JSONResponse({"error": "service tokens disabled"}, status_code=403)

        body = await request.json()
        secret = body.get("service_secret", "")
        username = body.get("username", "")

        if not secret or secret != PLATFORM_SERVICE_SECRET:
            logger.warning("service_token_bad_secret", extra={"username": username})
            return JSONResponse({"error": "forbidden"}, status_code=403)

        user = _get_user(username)
        if not user:
            return JSONResponse({"error": "user not found"}, status_code=404)

        token_str = f"envel_{secrets.token_hex(32)}"
        expires_at = int(time.time()) + TOKEN_TTL
        with _get_users_conn() as conn:
            conn.execute(
                """INSERT INTO oauth_tokens (token, client_id, username, scopes, expires_at, resource)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (token_str, "platform", username, MCP_SCOPE, expires_at),
            )
            conn.commit()

        logger.info("service_token_issued", extra={"username": username})
        return JSONResponse({"access_token": token_str, "expires_in": TOKEN_TTL})

    return service_token


# ─── APP FACTORY ─────────────────────────────────────────────────────────────

def create_app() -> Starlette:
    provider = EnvelOAuthProvider(base_url=AS_BASE_URL)

    issuer_url = AnyHttpUrl(AS_BASE_URL)
    auth_settings = AuthSettings(
        issuer_url=issuer_url,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[MCP_SCOPE],
            default_scopes=[MCP_SCOPE],
        ),
        required_scopes=[MCP_SCOPE],
        resource_server_url=None,
    )

    routes = create_auth_routes(
        provider=provider,
        issuer_url=issuer_url,
        service_documentation_url=None,
        client_registration_options=auth_settings.client_registration_options,
        revocation_options=auth_settings.revocation_options,
    )

    async def openid_config(request: Request) -> Response:
        return RedirectResponse(url="/.well-known/oauth-authorization-server", status_code=301)

    routes += [
        Route("/.well-known/openid-configuration", endpoint=openid_config, methods=["GET"]),
        Route("/login", endpoint=provider.handle_login, methods=["GET"]),
        Route("/login/callback", endpoint=provider.handle_login_callback, methods=["POST"]),
        Route("/google/authorize", endpoint=provider.handle_google_authorize, methods=["GET"]),
        Route("/google/callback", endpoint=provider.handle_google_callback, methods=["GET"]),
        Route("/link/callback", endpoint=provider.handle_link_callback, methods=["POST"]),
        Route(
            "/platform/google/authorize",
            endpoint=provider.handle_platform_google_authorize,
            methods=["GET"],
        ),
        Route(
            "/platform/google/callback",
            endpoint=provider.handle_platform_google_callback,
            methods=["GET"],
        ),
        Route(
            "/platform/handoff/resolve",
            endpoint=provider.handle_platform_handoff_resolve,
            methods=["POST"],
        ),
        Route(
            "/platform/signup/complete",
            endpoint=provider.handle_platform_signup_complete,
            methods=["POST"],
        ),
        Route(
            "/platform/user/connection-status",
            endpoint=provider.handle_platform_connection_status,
            methods=["POST"],
        ),
        Route(
            "/introspect",
            endpoint=cors_middleware(make_introspect_handler(provider), ["POST", "OPTIONS"]),
            methods=["POST", "OPTIONS"],
        ),
        Route(
            "/service-token",
            endpoint=make_service_token_handler(provider),
            methods=["POST"],
        ),
    ]

    return Starlette(routes=routes)


app = create_app()


def main():
    import uvicorn

    port = int(os.environ.get("AUTH_PORT", 9004))

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)

    logger.info("server_start", extra={"port": port})
    uvicorn.run("envel_auth.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
