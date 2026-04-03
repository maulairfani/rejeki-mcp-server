"""
Rejeki MCP — Authorization Server
Handles OAuth 2.1 flow for claude.ai integration.

Flow:
  claude.ai → /auth/.well-known/oauth-authorization-server  (discovery)
  claude.ai → /auth/register                                 (dynamic client reg)
  claude.ai → /auth/authorize  → browser login form
  user      → POST /auth/login/callback  (username + password)
  claude.ai → /auth/token                                    (code → token)
  mcp server→ /auth/introspect                               (token validation)
"""

import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl
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

logger = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────

USERS_FILE = os.environ.get("USERS_CONFIG")
if not USERS_FILE:
    raise RuntimeError("USERS_CONFIG env var must be set to the path of users.json")
AS_BASE_URL = os.environ.get("AS_BASE_URL", "https://maulairfani.my.id/rejeki/auth")
MCP_SCOPE = "rejeki"


def load_users() -> dict[str, dict]:
    with open(USERS_FILE) as f:
        return json.load(f)


# ─── OAUTH PROVIDER ──────────────────────────────────────────────────────────

class RejekiOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """OAuth provider backed by users.json credentials."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.token_user: dict[str, str] = {}
        self.state_mapping: dict[str, dict[str, Any]] = {}

    def _check_credentials(self, username: str, password: str) -> bool:
        users = load_users()
        user = users.get(username)
        if not user:
            return False
        return user.get("password") == password

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

        token_str = f"rejeki_{secrets.token_hex(32)}"
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
        self.tokens.pop(token, None)
        self.token_user.pop(token, None)

    # ── Login flow ──

    def login_page_html(self, state: str, error: bool = False) -> str:
        error_html = '<p class="error">Username atau password salah.</p>' if error else ""
        return f"""<!DOCTYPE html>
<html>
<head>
  <title>Rejeki MCP — Sign In</title>
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
  <h2>Rejeki MCP</h2>
  <p class="sub">Masuk untuk mengakses data keuanganmu.</p>
  <form method="post" action="{self.base_url}/login/callback">
    <input type="hidden" name="state" value="{state}">
    <label>Username</label>
    <input type="text" name="username" autofocus required>
    <label>Password</label>
    <input type="password" name="password" required>
    {error_html}
    <button type="submit">Masuk</button>
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

def make_introspect_handler(provider: RejekiOAuthProvider):
    async def introspect(request: Request) -> Response:
        form = await request.form()
        token = form.get("token")
        if not token or not isinstance(token, str):
            return JSONResponse({"active": False})

        access_token = await provider.load_access_token(token)
        if not access_token:
            return JSONResponse({"active": False})

        username = provider.token_user.get(token, "unknown")
        users = load_users()
        db_path = users.get(username, {}).get("db", "")

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


# ─── APP FACTORY ─────────────────────────────────────────────────────────────

def create_app() -> Starlette:
    provider = RejekiOAuthProvider(base_url=AS_BASE_URL)

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
    ]

    return Starlette(routes=routes)


app = create_app()


def main():
    import uvicorn
    port = int(os.environ.get("AUTH_PORT", 9004))
    logging.basicConfig(level=logging.INFO)
    print(f"Rejeki Auth Server on port {port}")
    uvicorn.run("rejeki_auth.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
