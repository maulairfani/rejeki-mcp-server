from fastapi import APIRouter, Depends, Query

from rejeki_platform.auth import require_user
from rejeki_platform.db import get_transactions

router = APIRouter()


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
