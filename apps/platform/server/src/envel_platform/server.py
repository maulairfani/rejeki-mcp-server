import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from envel_platform.routes.auth import router as auth_router
from envel_platform.routes.accounts import router as accounts_router
from envel_platform.routes.chat import router as chat_router
from envel_platform.routes.dashboard import router as dashboard_router
from envel_platform.routes.envelopes import router as envelopes_router
from envel_platform.routes.scheduled import router as scheduled_router
from envel_platform.routes.transactions import router as transactions_router

load_dotenv()

_SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not _SESSION_SECRET and not os.environ.get("TEST_TOKEN"):
    raise RuntimeError(
        "SESSION_SECRET env var must be set. "
        "Set it to a long random string (e.g. openssl rand -hex 32)."
    )

app = FastAPI(title="Envel Platform API")

_secure_cookies = os.environ.get("SECURE_COOKIES", "").lower() == "true"
app.add_middleware(
    SessionMiddleware,
    secret_key=_SESSION_SECRET or "dev-secret-test-only",
    https_only=_secure_cookies,
    same_site="lax",
)

_allowed_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.environ.get("FORCE_HTTPS", "").lower() == "true":
    class _HTTPSRedirectMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            proto = request.headers.get("x-forwarded-proto", "http")
            if proto == "http":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)
            return await call_next(request)

    app.add_middleware(_HTTPSRedirectMiddleware)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(accounts_router, prefix="/api/accounts", tags=["accounts"])
app.include_router(envelopes_router, prefix="/api/envelopes", tags=["envelopes"])
app.include_router(scheduled_router, prefix="/api/scheduled", tags=["scheduled"])
app.include_router(transactions_router, prefix="/api/transactions", tags=["transactions"])

# Serve React frontend build (production)
_ui_dist = Path(__file__).parent.parent.parent.parent / "web" / "dist"
if _ui_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_ui_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        index = _ui_dist / "index.html"
        return FileResponse(str(index))


def main():
    import uvicorn

    load_dotenv()
    port = int(os.environ.get("PLATFORM_PORT", 8002))
    from pythonjsonlogger.json import JsonFormatter
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
    logging.getLogger("envel_platform").info("server_start", extra={"port": port})
    uvicorn.run("envel_platform.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
