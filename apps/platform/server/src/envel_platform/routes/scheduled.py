from fastapi import APIRouter, Depends

from envel_platform.auth import require_user
from envel_platform.db import get_scheduled

router = APIRouter()


@router.get("")
async def scheduled(username: str = Depends(require_user)):
    return get_scheduled(username)
