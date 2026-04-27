from fastapi import APIRouter, Depends

from envel_platform.auth import require_user
from envel_platform.db import list_tags

router = APIRouter()


@router.get("")
async def get_tags(username: str = Depends(require_user)):
    return list_tags(username)
