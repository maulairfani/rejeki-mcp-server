import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from rejeki_platform.auth import NotAuthenticated, auth_router, require_user
from rejeki_platform.db import get_accounts, get_envelope_status, get_monthly_summary, get_spending_trend

load_dotenv()

_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

app = FastAPI(title="Rejeki Platform")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"),
)

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _format_rp(value: float) -> str:
    prefix = "Rp\u00a0" if value >= 0 else "-Rp\u00a0"
    return prefix + f"{abs(int(value)):,}".replace(",", ".")


_TEMPLATES.env.filters["rp"] = _format_rp

app.include_router(auth_router)


@app.exception_handler(NotAuthenticated)
async def redirect_to_login(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/login", status_code=302)


@app.get("/")
async def dashboard(request: Request, username: str = Depends(require_user)):
    now = datetime.now()
    period = now.strftime("%Y-%m")
    period_display = f"{_MONTHS[now.month]} {now.year}"

    try:
        accounts_data = get_accounts(username)
        envelopes = get_envelope_status(username, period)
        summary = get_monthly_summary(username, period)
        trend = get_spending_trend(username)
    except Exception:
        accounts_data = {"accounts": [], "total": 0}
        envelopes = []
        summary = {"income": 0, "expense": 0, "surplus": 0}
        trend = {"labels": [], "incomes": [], "expenses": []}

    return _TEMPLATES.TemplateResponse(
        request,
        "dashboard.html",
        {
            "username": username,
            "period": period,
            "period_display": period_display,
            "accounts": accounts_data["accounts"],
            "accounts_total": accounts_data["total"],
            "envelopes": envelopes,
            "summary": summary,
            "trend_json": json.dumps(trend),
        },
    )


def main():
    import uvicorn

    load_dotenv()
    port = int(os.environ.get("PLATFORM_PORT", 8002))
    from pythonjsonlogger.json import JsonFormatter
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
    logging.getLogger("rejeki_platform").info("server_start", extra={"port": port})
    uvicorn.run("rejeki_platform.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
