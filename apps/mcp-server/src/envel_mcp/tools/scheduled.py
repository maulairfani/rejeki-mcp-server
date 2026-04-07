import calendar
from datetime import date, timedelta
from envel_mcp.database import Database
from envel_mcp.tools.transactions import add_transaction


def _next_date(date_str: str, recurrence: str) -> str:
    d = date.fromisoformat(date_str)
    if recurrence == "weekly":
        return (d + timedelta(weeks=1)).isoformat()
    elif recurrence == "monthly":
        month = d.month % 12 + 1
        year = d.year if d.month < 12 else d.year + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day).isoformat()
    elif recurrence == "yearly":
        try:
            return date(d.year + 1, d.month, d.day).isoformat()
        except ValueError:
            return date(d.year + 1, d.month, 28).isoformat()
    return date_str


def add_scheduled_transaction(
    db: Database,
    amount: float,
    type: str,
    account_id: int,
    scheduled_date: str,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    recurrence: str = "once",
) -> dict:
    id = db.execute(
        """INSERT INTO scheduled_transactions
           (amount, type, envelope_id, account_id, to_account_id, payee, memo, scheduled_date, recurrence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (amount, type, envelope_id, account_id, to_account_id, payee, memo, scheduled_date, recurrence),
    )
    return {
        "id": id,
        "amount": amount,
        "type": type,
        "payee": payee,
        "scheduled_date": scheduled_date,
        "recurrence": recurrence,
    }


def get_scheduled_transactions(db: Database, include_inactive: bool = False) -> list[dict]:
    today = date.today()
    where = "" if include_inactive else "WHERE s.is_active = 1"
    rows = db.fetchall(
        f"""SELECT s.id, s.amount, s.type, s.payee, s.memo, s.scheduled_date,
                   s.recurrence, s.is_active,
                   e.name AS envelope, e.icon AS envelope_icon,
                   a.name AS account, a2.name AS to_account
            FROM scheduled_transactions s
            LEFT JOIN envelopes e ON s.envelope_id = e.id
            LEFT JOIN accounts a ON s.account_id = a.id
            LEFT JOIN accounts a2 ON s.to_account_id = a2.id
            {where}
            ORDER BY s.scheduled_date ASC""",
    )
    for r in rows:
        r["days_until"] = (date.fromisoformat(r["scheduled_date"]) - today).days
    return rows


def approve_scheduled_transaction(db: Database, id: int) -> dict:
    sched = db.fetchone("SELECT * FROM scheduled_transactions WHERE id = ? AND is_active = 1", (id,))
    if not sched:
        raise ValueError(f"Scheduled transaction id={id} not found or already inactive")

    txn = add_transaction(
        db,
        amount=sched["amount"],
        type=sched["type"],
        account_id=sched["account_id"],
        envelope_id=sched["envelope_id"],
        to_account_id=sched["to_account_id"],
        payee=sched["payee"],
        memo=sched["memo"],
        transaction_date=sched["scheduled_date"],
    )

    if sched["recurrence"] == "once":
        db.execute("UPDATE scheduled_transactions SET is_active = 0 WHERE id = ?", (id,))
        next_date = None
    else:
        next_date = _next_date(sched["scheduled_date"], sched["recurrence"])
        db.execute("UPDATE scheduled_transactions SET scheduled_date = ? WHERE id = ?", (next_date, id))

    return {"transaction": txn, "next_scheduled": next_date}


def skip_scheduled_transaction(db: Database, id: int) -> dict:
    sched = db.fetchone("SELECT * FROM scheduled_transactions WHERE id = ? AND is_active = 1", (id,))
    if not sched:
        raise ValueError(f"Scheduled transaction id={id} not found or already inactive")

    if sched["recurrence"] == "once":
        db.execute("UPDATE scheduled_transactions SET is_active = 0 WHERE id = ?", (id,))
        return {"id": id, "status": "skipped_and_cancelled"}

    next_date = _next_date(sched["scheduled_date"], sched["recurrence"])
    db.execute("UPDATE scheduled_transactions SET scheduled_date = ? WHERE id = ?", (next_date, id))
    return {"id": id, "status": "skipped", "next_scheduled": next_date}


def delete_scheduled_transaction(db: Database, id: int) -> dict:
    sched = db.fetchone("SELECT * FROM scheduled_transactions WHERE id = ?", (id,))
    if not sched:
        raise ValueError(f"Scheduled transaction id={id} not found")
    db.execute("DELETE FROM scheduled_transactions WHERE id = ?", (id,))
    return {"deleted_id": id, "payee": sched["payee"]}


# ---------------------------------------------------------------------------
# FastMCP provider
# ---------------------------------------------------------------------------

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import CurrentContext
from envel_mcp.deps import get_user_db

mcp = FastMCP("scheduled")


@mcp.tool(name="add_scheduled_transaction")
async def _add_scheduled_mcp(
    amount: float,
    type: str,
    account_id: int,
    scheduled_date: str,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    recurrence: str = "once",
    ctx: Context = CurrentContext(),
) -> dict:
    """
    Schedule a future transaction.
    recurrence: once | weekly | monthly | yearly.
    scheduled_date format YYYY-MM-DD.
    """
    await ctx.info(f"add_scheduled_transaction: {type} {amount} date={scheduled_date} recurrence={recurrence}")
    with get_user_db() as db:
        return add_scheduled_transaction(db, amount, type, account_id, scheduled_date, envelope_id, to_account_id, payee, memo, recurrence)


@mcp.tool(name="get_scheduled_transactions")
async def _get_scheduled_mcp(include_inactive: bool = False, ctx: Context = CurrentContext()) -> list:
    """List scheduled transactions, including days_until field (days remaining)."""
    await ctx.info("get_scheduled_transactions")
    with get_user_db() as db:
        return get_scheduled_transactions(db, include_inactive)


@mcp.tool(name="approve_scheduled_transaction")
async def _approve_scheduled_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """
    Execute a scheduled transaction as a real transaction.
    If recurring, automatically schedules the next occurrence.
    """
    await ctx.info(f"approve_scheduled_transaction: id={id}")
    with get_user_db() as db:
        return approve_scheduled_transaction(db, id)


@mcp.tool(name="skip_scheduled_transaction")
async def _skip_scheduled_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """
    Skip this occurrence without recording a transaction.
    If recurring, advances to the next occurrence.
    """
    await ctx.info(f"skip_scheduled_transaction: id={id}")
    with get_user_db() as db:
        return skip_scheduled_transaction(db, id)


@mcp.tool(name="delete_scheduled_transaction")
async def _delete_scheduled_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """Delete a scheduled transaction entirely."""
    await ctx.info(f"delete_scheduled_transaction: id={id}")
    with get_user_db() as db:
        return delete_scheduled_transaction(db, id)
