import os
from datetime import datetime
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import TokenVerifier, AccessToken
from mcp.types import Icon
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from rejeki.deps import _db_path
from rejeki.tools.accounts import mcp as _accounts_mcp
from rejeki.tools.analytics import mcp as _analytics_mcp
from rejeki.tools.apps import mcp as _apps_mcp
from rejeki.tools.envelopes import mcp as _envelopes_mcp
from rejeki.tools.scheduled import mcp as _scheduled_mcp
from rejeki.tools.transactions import mcp as _transactions_mcp
from rejeki.tools.wishlist import mcp as _wishlist_mcp

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
        "Aplikasi personal envelope-budgeting. "
        "Melacak rekening, kategori envelope, transaksi, dan aset. "
        "Format tanggal: YYYY-MM-DD. Nominal dalam IDR. "
        "Tools untuk aksi: tambah, edit, hapus, assign, approve. "
        "Prompts tersedia untuk workflow: budget_review, monthly_planning, onboarding_guide."
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


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@mcp.prompt()
def budget_review(period: str | None = None) -> str:
    """Review budget bulanan: analisis overspend dan saran rebalancing."""
    p = period or datetime.now().strftime("%Y-%m")
    return (
        f"Lakukan review budget bulan {p}:\n\n"
        f"1. Panggil finance_get_summary(period='{p}') untuk ringkasan income, expense, dan net.\n"
        f"2. Panggil finance_get_envelopes(period='{p}') untuk detail setiap envelope "
        f"(carryover, assigned, activity, available).\n"
        f"3. Identifikasi envelope yang overspend (available negatif).\n"
        f"4. Berikan ringkasan: envelope mana yang konsisten, mana yang perlu perhatian.\n"
        f"5. Cek finance_get_ready_to_assign(period='{p}') — jika ada RTA tersisa, sarankan alokasi ke envelope yang kekurangan."
    )


@mcp.prompt()
def monthly_planning(period: str | None = None) -> str:
    """Panduan distribusi budget awal bulan: cek RTA, lihat targets, assign hingga RTA = 0."""
    p = period or datetime.now().strftime("%Y-%m")
    return (
        f"Bantu planning budget bulan {p}:\n\n"
        f"1. Panggil finance_get_ready_to_assign(period='{p}') — lihat berapa uang yang belum dialokasikan.\n"
        f"2. Panggil finance_get_envelopes(period='{p}') — lihat target setiap envelope dan available saat ini.\n"
        f"3. Prioritaskan envelope dengan target 'monthly' yang belum terpenuhi.\n"
        f"4. Untuk envelope 'goal', cek apakah on track menuju deadline.\n"
        f"5. Distribusikan RTA ke envelope yang paling butuh hingga RTA = 0.\n"
        f"Gunakan finance_assign_to_envelope untuk setiap alokasi. Tanya user jika ada prioritas khusus."
    )


@mcp.prompt()
def onboarding_guide() -> str:
    """Wizard setup Rejeki dari awal: rekening → envelope → budget."""
    return (
        "Bantu setup Rejeki dari awal:\n\n"
        "1. Baca finance://onboarding-status untuk melihat progress saat ini.\n"
        "2. Jika belum ada rekening: tambah dengan finance_add_account (type: bank | ewallet | cash).\n"
        "3. Buat kelompok envelope dengan finance_add_group (contoh: Kebutuhan, Keinginan, Tabungan).\n"
        "4. Buat envelope untuk setiap kategori dengan finance_add_envelope (type: income | expense).\n"
        "5. Set target dengan finance_set_target untuk envelope yang punya target bulanan atau goal.\n"
        "6. Assign budget ke setiap envelope dengan finance_assign_to_envelope hingga RTA = 0.\n\n"
        "Tanyakan user mau mulai dari step mana, atau ikuti step berikutnya yang belum selesai."
    )


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
        "rejeki.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
