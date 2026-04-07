from envel_mcp.database import Database


def add_wishlist_item(db: Database, name: str, price: float | None = None, priority: str = "medium", url: str | None = None, notes: str | None = None) -> dict:
    id = db.execute(
        "INSERT INTO wishlist (name, price, priority, url, notes) VALUES (?, ?, ?, ?, ?)",
        (name, price, priority, url, notes),
    )
    return {"id": id, "name": name, "price": price, "priority": priority, "url": url, "notes": notes, "status": "wanted"}


def get_wishlist(db: Database, status: str | None = None) -> dict:
    if status:
        rows = db.fetchall("SELECT * FROM wishlist WHERE status = ? ORDER BY priority DESC, created_at DESC", (status,))
    else:
        rows = db.fetchall("SELECT * FROM wishlist ORDER BY priority DESC, created_at DESC")
    return {"items": rows, "total": len(rows)}


def edit_wishlist_item(db: Database, id: int, name: str | None = None, price: float | None = None, priority: str | None = None, url: str | None = None, notes: str | None = None) -> dict:
    item = db.fetchone("SELECT * FROM wishlist WHERE id = ?", (id,))
    if not item:
        raise ValueError(f"Wishlist item id={id} not found")

    new_name     = name     if name     is not None else item["name"]
    new_price    = price    if price    is not None else item["price"]
    new_priority = priority if priority is not None else item["priority"]
    new_url      = url      if url      is not None else item["url"]
    new_notes    = notes    if notes    is not None else item["notes"]

    db.execute(
        "UPDATE wishlist SET name = ?, price = ?, priority = ?, url = ?, notes = ? WHERE id = ?",
        (new_name, new_price, new_priority, new_url, new_notes, id),
    )
    return {"id": id, "name": new_name, "price": new_price, "priority": new_priority, "url": new_url, "notes": new_notes, "status": item["status"]}


def mark_bought(db: Database, id: int) -> dict:
    item = db.fetchone("SELECT * FROM wishlist WHERE id = ?", (id,))
    if not item:
        raise ValueError(f"Wishlist item id={id} not found")

    db.execute("UPDATE wishlist SET status = 'bought' WHERE id = ?", (id,))
    return {"id": id, "name": item["name"], "status": "bought"}


def delete_wishlist_item(db: Database, id: int) -> dict:
    item = db.fetchone("SELECT * FROM wishlist WHERE id = ?", (id,))
    if not item:
        raise ValueError(f"Wishlist item id={id} not found")

    db.execute("DELETE FROM wishlist WHERE id = ?", (id,))
    return {"deleted_id": id, "name": item["name"]}


# ---------------------------------------------------------------------------
# FastMCP provider
# ---------------------------------------------------------------------------

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import CurrentContext
from envel_mcp.deps import get_user_db

mcp = FastMCP("wishlist")


@mcp.tool(name="add_wishlist_item")
async def _add_wishlist_item_mcp(name: str, price: float | None = None, priority: str = "medium", url: str | None = None, notes: str | None = None, ctx: Context = CurrentContext()) -> dict:
    """Add item to wishlist. priority: high | medium | low"""
    await ctx.info(f"add_wishlist_item: name={name}, price={price}")
    with get_user_db() as db:
        return add_wishlist_item(db, name, price, priority, url, notes)


@mcp.tool(name="get_wishlist")
async def _get_wishlist_mcp(status: str | None = None, ctx: Context = CurrentContext()) -> dict:
    """List wishlist items. Optional status filter: wanted | bought"""
    await ctx.info(f"get_wishlist: status={status}")
    with get_user_db() as db:
        return get_wishlist(db, status)


@mcp.tool(name="edit_wishlist_item")
async def _edit_wishlist_item_mcp(id: int, name: str | None = None, price: float | None = None, priority: str | None = None, url: str | None = None, notes: str | None = None, ctx: Context = CurrentContext()) -> dict:
    """Edit a wishlist item."""
    await ctx.info(f"edit_wishlist_item: id={id}")
    with get_user_db() as db:
        return edit_wishlist_item(db, id, name, price, priority, url, notes)


@mcp.tool(name="mark_bought")
async def _mark_bought_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """Mark a wishlist item as bought."""
    await ctx.info(f"mark_bought: id={id}")
    with get_user_db() as db:
        return mark_bought(db, id)


@mcp.tool(name="delete_wishlist_item")
async def _delete_wishlist_item_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """Delete a wishlist item."""
    await ctx.info(f"delete_wishlist_item: id={id}")
    with get_user_db() as db:
        return delete_wishlist_item(db, id)
