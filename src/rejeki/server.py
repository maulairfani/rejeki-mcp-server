import contextlib
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from rejeki.deps import _db_path
from rejeki.tools.accounts import mcp as _accounts_mcp
from rejeki.tools.analytics import mcp as _analytics_mcp
from rejeki.tools.envelopes import mcp as _envelopes_mcp
from rejeki.tools.scheduled import mcp as _scheduled_mcp
from rejeki.tools.transactions import mcp as _transactions_mcp

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

AS_BASE_URL   = os.environ.get("AS_BASE_URL",    "https://maulairfani.my.id/rejeki/auth")
MCP_BASE_URL  = os.environ.get("MCP_BASE_URL",   "https://maulairfani.my.id/rejeki/mcp")
INTROSPECT_URL = os.environ.get("INTROSPECT_URL", "http://127.0.0.1:9004/introspect")

_ALLOWED_HOSTS = os.environ.get(
    "MCP_ALLOWED_HOSTS",
    "maulairfani.my.id,localhost:*,127.0.0.1:*,[::1]:*",
).split(",")


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
            expires_at=data.get("exp"),
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

mcp = FastMCP(
    "rejeki",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    token_verifier=_token_verifier,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(AS_BASE_URL),
        resource_server_url=AnyHttpUrl(MCP_BASE_URL),
        required_scopes=["rejeki"],
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_ALLOWED_HOSTS,
        allowed_origins=[
            "https://maulairfani.my.id",
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
    ),
    instructions=(
        "Aplikasi personal envelope-budgeting. "
        "Melacak rekening, kategori envelope, transaksi, dan aset. "
        "Format tanggal: YYYY-MM-DD. Nominal dalam IDR. "
        "Resources (finance://) untuk membaca data. "
        "Tools untuk aksi: tambah, edit, hapus, assign, approve. "
        "Prompts tersedia untuk workflow: budget_review, monthly_planning, onboarding_guide."
    ),
)


# ---------------------------------------------------------------------------
# Compose sub-servers
# ---------------------------------------------------------------------------

def _mount(sub: FastMCP, prefix: str) -> None:
    """Mount semua tools dari sub-server ke main MCP dengan prefix."""
    for tool in sub._tool_manager.list_tools():
        mcp.add_tool(tool.fn, name=f"{prefix}_{tool.name}", description=tool.description)


_mount(_accounts_mcp, "finance")
_mount(_envelopes_mcp, "finance")
_mount(_transactions_mcp, "finance")
_mount(_scheduled_mcp, "finance")
_mount(_analytics_mcp, "finance")


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

@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", lambda r: PlainTextResponse("ok")),
        Mount("/mcp", app=mcp.streamable_http_app()),
    ],
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
