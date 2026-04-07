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
AS_BASE_URL = os.environ.get("AS_BASE_URL", "https://maulairfani.my.id/envel/auth")
MCP_SCOPE = "envel"

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    db_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _get_users_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_USERS_TABLE)
    return conn


def _get_user(username: str) -> dict | None:
    with _get_users_conn() as conn:
        row = conn.execute(
            "SELECT username, password_hash, db_path FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(row) if row else None


# ─── OAUTH PROVIDER ──────────────────────────────────────────────────────────

class EnvelOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """OAuth provider backed by users.db credentials."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.token_user: dict[str, str] = {}
        self.state_mapping: dict[str, dict[str, Any]] = {}

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
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        if not client_info.client_id:
            raise ValueError("No client_id")
        self.clients[client_info.client_id] = client_info

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

        self.tokens[token_str] = AccessToken(
            token=token_str,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + 3600 * 8,
            resource=authorization_code.resource,
        )
        self.token_user[token_str] = username
        del self.auth_codes[authorization_code.code]

        logger.info("token_issued", extra={"username": username, "client_id": client.client_id})

        return OAuthToken(
            access_token=token_str,
            token_type="Bearer",
            expires_in=3600 * 8,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self.tokens.get(token)
        if not access_token:
            return None
        if access_token.expires_at and access_token.expires_at < time.time():
            del self.tokens[token]
            self.token_user.pop(token, None)
            return None
        return access_token

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        raise NotImplementedError

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        username = self.token_user.pop(token, "unknown")
        self.tokens.pop(token, None)
        logger.info("token_revoked", extra={"username": username})

    # ── Login flow ──

    def login_page_html(self, state: str, error: bool = False) -> str:
        error_html = '<p class="error">Invalid username or password.</p>' if error else ""
        return f"""<!DOCTYPE html>
<html>
<head>
  <title>Finance MCP — Sign In</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 400px; margin: 80px auto; padding: 0 20px; }}
    h2 {{ margin-bottom: 4px; }}
    p.sub {{ color: #666; margin-top: 0; margin-bottom: 24px; font-size: 14px; }}
    label {{ display: block; font-size: 13px; font-weight: 600; margin-bottom: 4px; }}
    input[type=text], input[type=password] {{
      width: 100%; padding: 10px; margin-bottom: 16px;
      border: 1px solid #ccc; border-radius: 6px; font-size: 15px; box-sizing: border-box;
    }}
    button {{
      width: 100%; padding: 11px; background: #16a34a; color: #fff;
      border: none; border-radius: 6px; font-size: 15px; cursor: pointer;
    }}
    button:hover {{ background: #15803d; }}
    .error {{ color: #dc2626; font-size: 13px; margin-top: -12px; margin-bottom: 12px; }}
  </style>
</head>
<body>
  <h2>Finance MCP</h2>
  <p class="sub">Sign in to access your financial data.</p>
  <form method="post" action="{self.base_url}/login/callback">
    <input type="hidden" name="state" value="{state}">
    <label>Username</label>
    <input type="text" name="username" autofocus required>
    <label>Password</label>
    <input type="password" name="password" required>
    {error_html}
    <button type="submit">Sign In</button>
  </form>
</body>
</html>"""

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

        username = provider.token_user.get(token, "unknown")
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
        expires_in = 3600 * 8
        provider.tokens[token_str] = AccessToken(
            token=token_str,
            client_id="platform",
            scopes=[MCP_SCOPE],
            expires_at=int(time.time()) + expires_in,
            resource=None,
        )
        provider.token_user[token_str] = username

        logger.info("service_token_issued", extra={"username": username})
        return JSONResponse({"access_token": token_str, "expires_in": expires_in})

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
