from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from envel_platform.auth import require_user
from envel_platform.db import (
    add_envelope,
    archive_envelope,
    assign_envelope,
    delete_envelope,
    get_envelope_status,
    reorder_envelope_groups,
    reorder_envelopes,
    set_envelope_target,
    unarchive_envelope,
)

router = APIRouter()


class EnvelopeCreate(BaseModel):
    name: str
    icon: str | None = None
    type: str = "expense"
    group_id: int | None = None


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


@router.post("", status_code=201)
async def create_envelope(
    body: EnvelopeCreate,
    username: str = Depends(require_user),
):
    return add_envelope(username, body.name, body.icon or "📦", body.type, body.group_id)


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


@router.post("/{envelope_id}/archive")
async def archive(envelope_id: int, username: str = Depends(require_user)):
    archive_envelope(username, envelope_id)
    return {"ok": True}


@router.post("/{envelope_id}/unarchive")
async def unarchive(envelope_id: int, username: str = Depends(require_user)):
    unarchive_envelope(username, envelope_id)
    return {"ok": True}


@router.delete("/{envelope_id}", status_code=204)
async def remove_envelope(envelope_id: int, username: str = Depends(require_user)):
    try:
        delete_envelope(username, envelope_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
