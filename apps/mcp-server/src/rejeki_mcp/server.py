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

from rejeki_mcp.deps import _db_path
from rejeki_mcp.prompts.budget import mcp as _budget_prompts_mcp
from rejeki_mcp.prompts.onboarding import mcp as _onboarding_prompts_mcp
from rejeki_mcp.tools.accounts import mcp as _accounts_mcp
from rejeki_mcp.tools.analytics import mcp as _analytics_mcp
from rejeki_mcp.tools.apps import mcp as _apps_mcp
from rejeki_mcp.tools.envelopes import mcp as _envelopes_mcp
from rejeki_mcp.tools.scheduled import mcp as _scheduled_mcp
from rejeki_mcp.tools.transactions import mcp as _transactions_mcp
from rejeki_mcp.tools.wishlist import mcp as _wishlist_mcp

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

INTROSPECT_URL = os.environ.get("INTROSPECT_URL", "http://127.0.0.1:9004/introspect")


# ─── TOKEN VERIFIER ──────────────────────────────────────────────────────────

class RejekiTokenVerifier(TokenVerifier):
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
                return None

        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data.get("active"):
            return None

        db = data.get("db", os.path.expanduser("~/rejeki.db"))
        _db_path.set(db)

        return AccessToken(
            token=token,
            client_id=data.get("username", data.get("client_id", "unknown")),
            scopes=data.get("scope", "").split(),
        )


class TestTokenVerifier(TokenVerifier):
    """Static single-token verifier for local development / evaluation."""

    def __init__(self, token: str):
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self._token:
            return None
        # _db_path falls back to TEST_DB env var in get_user_db()
        return AccessToken(
            token=token,
            client_id="test-user-eval-001",
            scopes=["rejeki"],
        )


# ─── MCP SERVER ──────────────────────────────────────────────────────────────

_test_token = os.environ.get("TEST_TOKEN")
if _test_token:
    _token_verifier: TokenVerifier = TestTokenVerifier(_test_token)
else:
    _token_verifier = RejekiTokenVerifier()

_rejeki_icon = Icon(
    src="data:image/svg+xml," + quote(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<text y="26" font-size="28">💰</text></svg>'
    ),
    mimeType="image/svg+xml",
)

mcp = FastMCP(
    "rejeki",
    icons=[_rejeki_icon],
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
        "rejeki_mcp.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
