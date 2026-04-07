from envel_mcp.database import Database


def add_account(db: Database, name: str, type: str, initial_balance: float = 0) -> dict:
    id = db.execute(
        "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
        (name, type, initial_balance),
    )
    return {"id": id, "name": name, "type": type, "balance": initial_balance}


def get_accounts(db: Database) -> dict:
    rows = db.fetchall("SELECT id, name, type, balance FROM accounts ORDER BY name")
    total = sum(r["balance"] for r in rows)
    return {"accounts": rows, "total_balance": total}


def edit_account(db: Database, id: int, name: str | None = None, type: str | None = None) -> dict:
    account = db.fetchone("SELECT * FROM accounts WHERE id = ?", (id,))
    if not account:
        raise ValueError(f"Account id={id} not found")

    new_name = name or account["name"]
    new_type = type or account["type"]
    db.execute("UPDATE accounts SET name = ?, type = ? WHERE id = ?", (new_name, new_type, id))
    return {"id": id, "name": new_name, "type": new_type, "balance": account["balance"]}


def update_balance(db: Database, id: int, balance: float) -> dict:
    account = db.fetchone("SELECT * FROM accounts WHERE id = ?", (id,))
    if not account:
        raise ValueError(f"Account id={id} not found")

    db.execute("UPDATE accounts SET balance = ? WHERE id = ?", (balance, id))
    return {"id": id, "name": account["name"], "type": account["type"], "balance": balance}


def delete_account(db: Database, id: int) -> dict:
    account = db.fetchone("SELECT * FROM accounts WHERE id = ?", (id,))
    if not account:
        raise ValueError(f"Account id={id} not found")

    db.execute("DELETE FROM accounts WHERE id = ?", (id,))
    return {"deleted_id": id, "name": account["name"]}


# ---------------------------------------------------------------------------
# FastMCP provider
# ---------------------------------------------------------------------------

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import CurrentContext
from envel_mcp.deps import get_user_db

mcp = FastMCP("accounts")


@mcp.tool(name="add_account")
async def _add_account_mcp(name: str, type: str, initial_balance: float = 0, ctx: Context = CurrentContext()) -> dict:
    """Add a new account. type: bank | ewallet | cash"""
    await ctx.info(f"add_account: name={name}, type={type}, balance={initial_balance}")
    with get_user_db() as db:
        return add_account(db, name, type, initial_balance)


@mcp.tool(name="get_accounts")
async def _get_accounts_mcp(ctx: Context = CurrentContext()) -> dict:
    """List all accounts with balances and total."""
    await ctx.info("get_accounts")
    with get_user_db() as db:
        return get_accounts(db)


@mcp.tool(name="edit_account")
async def _edit_account_mcp(id: int, name: str | None = None, type: str | None = None, ctx: Context = CurrentContext()) -> dict:
    """Edit account name or type."""
    await ctx.info(f"edit_account: id={id}")
    with get_user_db() as db:
        return edit_account(db, id, name, type)


@mcp.tool(name="update_balance")
async def _update_balance_mcp(id: int, balance: float, ctx: Context = CurrentContext()) -> dict:
    """Set account balance directly (manual reconciliation)."""
    await ctx.info(f"update_balance: id={id}, balance={balance}")
    with get_user_db() as db:
        return update_balance(db, id, balance)


@mcp.tool(name="delete_account")
async def _delete_account_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """Delete an account."""
    await ctx.info(f"delete_account: id={id}")
    with get_user_db() as db:
        return delete_account(db, id)
