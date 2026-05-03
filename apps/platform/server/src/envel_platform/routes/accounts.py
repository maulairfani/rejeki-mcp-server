from fastapi import APIRouter, Depends

from envel_platform.auth import require_user
from envel_platform.db import (
    get_accounts,
    add_account,
    edit_account,
    update_account_balance,
    delete_account,
    get_account_transactions,
)
from pydantic import BaseModel

router = APIRouter()


class AccountCreate(BaseModel):
    name: str
    type: str
    balance: float = 0


class AccountEdit(BaseModel):
    name: str
    type: str


class BalanceUpdate(BaseModel):
    balance: float


@router.get("")
async def accounts(username: str = Depends(require_user)):
    return get_accounts(username)


@router.post("", status_code=201)
async def create_account(body: AccountCreate, username: str = Depends(require_user)):
    return add_account(username, body.name, body.type, body.balance)


@router.patch("/{account_id}")
async def update_account(
    account_id: int, body: AccountEdit, username: str = Depends(require_user)
):
    return edit_account(username, account_id, body.name, body.type)


@router.patch("/{account_id}/balance")
async def reconcile_account(
    account_id: int, body: BalanceUpdate, username: str = Depends(require_user)
):
    return update_account_balance(username, account_id, body.balance)


@router.delete("/{account_id}", status_code=204)
async def remove_account(account_id: int, username: str = Depends(require_user)):
    delete_account(username, account_id)


@router.get("/{account_id}/transactions")
async def account_transactions(
    account_id: int, username: str = Depends(require_user)
):
    return get_account_transactions(username, account_id=account_id, limit=5)
