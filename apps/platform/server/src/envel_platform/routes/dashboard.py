from datetime import datetime

from fastapi import APIRouter, Depends

from envel_platform.auth import require_user
from envel_platform.db import get_accounts, get_envelope_status, get_monthly_summary, get_spending_trend

router = APIRouter()


@router.get("")
async def dashboard(username: str = Depends(require_user)):
    period = datetime.now().strftime("%Y-%m")
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

    return {
        "period": period,
        "accounts": accounts_data["accounts"],
        "accounts_total": accounts_data["total"],
        "envelopes": envelopes,
        "summary": summary,
        "trend": trend,
    }
