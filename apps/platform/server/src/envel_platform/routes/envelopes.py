from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from envel_platform.auth import require_user
from envel_platform.db import (
    assign_envelope,
    get_envelope_status,
    reorder_envelope_groups,
    reorder_envelopes,
    set_envelope_target,
)

router = APIRouter()


class AssignRequest(BaseModel):
    assigned: float


class SetTargetRequest(BaseModel):
    target_type: str | None = None
    target_amount: float | None = None
    target_deadline: str | None = None


class EnvelopeReorderItem(BaseModel):
    id: int
    group_id: int | None = None
    sort_order: int


class GroupReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderRequest(BaseModel):
    items: list[EnvelopeReorderItem]


class GroupReorderRequest(BaseModel):
    items: list[GroupReorderItem]


@router.get("")
async def envelopes(
    username: str = Depends(require_user),
    period: str = Query(default=None),
    include_archived: bool = Query(default=False),
):
    if not period:
        period = datetime.now().strftime("%Y-%m")
    return get_envelope_status(username, period, include_archived)


@router.patch("/reorder")
async def reorder(
    body: ReorderRequest,
    username: str = Depends(require_user),
):
    reorder_envelopes(username, [i.model_dump() for i in body.items])
    return {"ok": True}


@router.patch("/groups/reorder")
async def reorder_groups(
    body: GroupReorderRequest,
    username: str = Depends(require_user),
):
    reorder_envelope_groups(username, [i.model_dump() for i in body.items])
    return {"ok": True}


@router.patch("/{envelope_id}/target")
async def update_target(
    envelope_id: int,
    body: SetTargetRequest,
    username: str = Depends(require_user),
):
    set_envelope_target(
        username, envelope_id,
        body.target_type, body.target_amount, body.target_deadline,
    )
    return {"ok": True}


@router.patch("/{envelope_id}/assign")
async def assign(
    envelope_id: int,
    body: AssignRequest,
    period: str = Query(...),
    username: str = Depends(require_user),
):
    assign_envelope(username, envelope_id, period, body.assigned)
    return {"ok": True}
