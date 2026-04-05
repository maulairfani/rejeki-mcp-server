from fastapi import APIRouter, Depends

from rejeki_platform.auth import require_user
from rejeki_platform.db import get_accounts

router = APIRouter()


@router.get("")
async def accounts(username: str = Depends(require_user)):
    return get_accounts(username)
