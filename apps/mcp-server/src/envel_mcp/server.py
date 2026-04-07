import logging
import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import TokenVerifier, AccessToken
from mcp.types import Icon
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from envel_mcp.deps import _db_path, _db_username
from envel_mcp.prompts.budget import mcp as _budget_prompts_mcp
from envel_mcp.prompts.onboarding import mcp as _onboarding_prompts_mcp
from envel_mcp.tools.accounts import mcp as _accounts_mcp
from envel_mcp.tools.analytics import mcp as _analytics_mcp
from envel_mcp.tools.apps import mcp as _apps_mcp
from envel_mcp.tools.envelopes import mcp as _envelopes_mcp
from envel_mcp.tools.scheduled import mcp as _scheduled_mcp
from envel_mcp.tools.transactions import mcp as _transactions_mcp
from envel_mcp.tools.wishlist import mcp as _wishlist_mcp

load_dotenv()

logger = logging.getLogger("envel_mcp")

# ─── CONFIG ──────────────────────────────────────────────────────────────────

INTROSPECT_URL = os.environ.get("INTROSPECT_URL", "http://127.0.0.1:9004/introspect")


# ─── TOKEN VERIFIER ──────────────────────────────────────────────────────────

class EnvelTokenVerifier(TokenVerifier):
    """Validates OAuth tokens via introspection and injects per-user db_path."""

    async def verify_token(self, token: str) -> AccessToken | None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.post(
                    INTROSPECT_URL,
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except Exception:
                logger.warning("token_verify_error: introspection request failed")
                return None

        if resp.status_code != 200:
            logger.warning("token_verify_error: introspection returned %d", resp.status_code)
            return None

        data = resp.json()
        if not data.get("active"):
            logger.info("token_verify: inactive token")
            return None

        username = data.get("username", data.get("client_id", "unknown"))
        db = data.get("db", os.path.expanduser("~/envel.db"))
        _db_path.set(db)
        _db_username.set(username)

        logger.info("token_verify_ok: user=%s", username)

        return AccessToken(
            token=token,
            client_id=username,
            scopes=data.get("scope", "").split(),
        )


class TestTokenVerifier(TokenVerifier):
    """Static single-token verifier for local development / evaluation."""

    def __init__(self, token: str):
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self._token:
            return None
        # _db_path and _db_username fall back to TEST_DB/TEST_USERNAME env vars in get_user_db()
        _db_username.set("test-user-eval-001")
        return AccessToken(
            token=token,
            client_id="test-user-eval-001",
            scopes=["envel"],
        )


# ─── MCP SERVER ──────────────────────────────────────────────────────────────

_test_token = os.environ.get("TEST_TOKEN")
if _test_token:
    _token_verifier: TokenVerifier = TestTokenVerifier(_test_token)
else:
    _token_verifier = EnvelTokenVerifier()

_envel_icon = Icon(
    src="data:image/svg+xml," + quote(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<text y="26" font-size="28">💰</text></svg>'
    ),
    mimeType="image/svg+xml",
)

mcp = FastMCP(
    "envel",
    icons=[_envel_icon],
    auth=_token_verifier,
    instructions=(
        "Personal envelope-budgeting application. "
        "Tracks accounts, envelope categories, transactions, and assets. "
        "Date format: YYYY-MM-DD. Amounts in IDR. "
        "Tools for actions: add, edit, delete, assign, approve. "
        "Available prompts for workflows: budget_review, monthly_planning, onboarding_guide."
    ),
)


# ---------------------------------------------------------------------------
# Compose sub-servers
# ---------------------------------------------------------------------------

mcp.mount(_accounts_mcp,     namespace="finance")
mcp.mount(_envelopes_mcp,    namespace="finance")
mcp.mount(_transactions_mcp, namespace="finance")
mcp.mount(_scheduled_mcp,    namespace="finance")
mcp.mount(_analytics_mcp,    namespace="finance")
mcp.mount(_apps_mcp)
mcp.mount(_wishlist_mcp,     namespace="finance")
mcp.mount(_budget_prompts_mcp)
mcp.mount(_onboarding_prompts_mcp)


# ---------------------------------------------------------------------------
# ASGI app
# ---------------------------------------------------------------------------

mcp_app = mcp.http_app(path="/", stateless_http=True)

app = Starlette(
    routes=[
        Route("/health", lambda r: PlainTextResponse("ok")),
        Mount("/mcp", app=mcp_app),
    ],
    lifespan=mcp_app.lifespan,
)


def main():
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(
        "envel_mcp.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
