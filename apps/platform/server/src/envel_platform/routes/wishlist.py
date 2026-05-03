from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from envel_platform.auth import require_user
from envel_platform.db import add_wishlist_item, get_wishlist

router = APIRouter()


class WishlistCreate(BaseModel):
    name: str
    icon: str | None = None
    price: float | None = None
    priority: str = "medium"
    url: str | None = None
    notes: str | None = None


@router.get("")
async def wishlist(
    username: str = Depends(require_user),
    status: str = Query(default=None),
):
    items = get_wishlist(username, status=status)
    total_wanted = sum(
        i["price"] or 0 for i in items if i["status"] == "wanted"
    )
    wanted_count = sum(1 for i in items if i["status"] == "wanted")
    bought_count = sum(1 for i in items if i["status"] == "bought")
    return {
        "items": items,
        "totalWanted": total_wanted,
        "wantedCount": wanted_count,
        "boughtCount": bought_count,
    }


@router.post("", status_code=201)
async def create_wishlist_item(
    body: WishlistCreate,
    username: str = Depends(require_user),
):
    return add_wishlist_item(
        username,
        body.name,
        body.icon,
        body.price,
        body.priority,
        body.url,
        body.notes,
    )
