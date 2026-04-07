from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from envel_platform.auth import require_user
from envel_platform.db import assign_envelope, get_envelope_status

router = APIRouter()


class AssignRequest(BaseModel):
    assigned: float


@router.get("")
async def envelopes(
    username: str = Depends(require_user),
    period: str = Query(default=None),
):
    if not period:
        period = datetime.now().strftime("%Y-%m")
    return get_envelope_status(username, period)


@router.patch("/{envelope_id}/assign")
async def assign(
    envelope_id: int,
    body: AssignRequest,
    period: str = Query(...),
    username: str = Depends(require_user),
):
    assign_envelope(username, envelope_id, period, body.assigned)
    return {"ok": True}
