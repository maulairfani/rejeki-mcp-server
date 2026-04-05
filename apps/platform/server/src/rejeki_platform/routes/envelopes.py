from datetime import datetime

from fastapi import APIRouter, Depends, Query

from rejeki_platform.auth import require_user
from rejeki_platform.db import get_envelope_status

router = APIRouter()


@router.get("")
async def envelopes(
    username: str = Depends(require_user),
    period: str = Query(default=None),
):
    if not period:
        period = datetime.now().strftime("%Y-%m")
    return get_envelope_status(username, period)
