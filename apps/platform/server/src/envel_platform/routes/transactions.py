from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from envel_platform.auth import require_user
from envel_platform.db import create_transaction, get_transactions

router = APIRouter()


class TransactionCreate(BaseModel):
    amount: float
    type: str
    account_id: int
    payee: str | None = None
    memo: str | None = None
    envelope_id: int | None = None
    to_account_id: int | None = None
    date: str | None = None


@router.get("")
async def transactions(
    username: str = Depends(require_user),
    period: str = Query(default=None),
    account_id: int = Query(default=None),
    envelope_id: int = Query(default=None),
    search: str = Query(default=None),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0),
):
    return get_transactions(
        username,
        period=period,
        account_id=account_id,
        envelope_id=envelope_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=201)
async def add_transaction(
    body: TransactionCreate,
    username: str = Depends(require_user),
):
    return create_transaction(
        username,
        amount=body.amount,
        type_=body.type,
        account_id=body.account_id,
        payee=body.payee,
        memo=body.memo,
        envelope_id=body.envelope_id,
        to_account_id=body.to_account_id,
        date=body.date,
    )
