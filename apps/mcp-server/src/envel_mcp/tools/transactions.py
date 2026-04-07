from datetime import date
from envel_mcp.database import Database


def add_transaction(
    db: Database,
    amount: float,
    type: str,
    account_id: int,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    transaction_date: str | None = None,
) -> dict:
    txn_date = transaction_date or date.today().isoformat()

    txn_id = db.execute(
        """INSERT INTO transactions
           (amount, type, envelope_id, account_id, to_account_id, payee, memo, date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (amount, type, envelope_id, account_id, to_account_id, payee, memo, txn_date),
    )

    if type == "expense":
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
    elif type == "income":
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    elif type == "transfer":
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

    account = db.fetchone("SELECT name, balance FROM accounts WHERE id = ?", (account_id,))
    return {
        "id": txn_id,
        "amount": amount,
        "type": type,
        "payee": payee,
        "memo": memo,
        "date": txn_date,
        "account": account["name"],
        "account_balance_after": account["balance"],
    }


def _reverse_balance(db: Database, txn: dict) -> None:
    t = txn["type"]
    if t == "expense":
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (txn["amount"], txn["account_id"]))
    elif t == "income":
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (txn["amount"], txn["account_id"]))
    elif t == "transfer":
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (txn["amount"], txn["account_id"]))
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (txn["amount"], txn["to_account_id"]))


def _apply_balance(db: Database, amount: float, type: str, account_id: int, to_account_id: int | None) -> None:
    if type == "expense":
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
    elif type == "income":
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    elif type == "transfer":
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))


def edit_transaction(
    db: Database,
    id: int,
    amount: float | None = None,
    type: str | None = None,
    account_id: int | None = None,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    transaction_date: str | None = None,
) -> dict:
    old = db.fetchone("SELECT * FROM transactions WHERE id = ?", (id,))
    if not old:
        raise ValueError(f"Transaction id={id} not found")

    _reverse_balance(db, old)

    new_amount = amount if amount is not None else old["amount"]
    new_type = type or old["type"]
    new_account_id = account_id if account_id is not None else old["account_id"]
    new_to_account_id = to_account_id if to_account_id is not None else old["to_account_id"]
    new_envelope_id = envelope_id if envelope_id is not None else old["envelope_id"]
    new_payee = payee if payee is not None else old["payee"]
    new_memo = memo if memo is not None else old["memo"]
    new_date = transaction_date or old["date"]

    db.execute(
        """UPDATE transactions SET amount=?, type=?, account_id=?, to_account_id=?,
           envelope_id=?, payee=?, memo=?, date=? WHERE id=?""",
        (new_amount, new_type, new_account_id, new_to_account_id, new_envelope_id,
         new_payee, new_memo, new_date, id),
    )
    _apply_balance(db, new_amount, new_type, new_account_id, new_to_account_id)

    account = db.fetchone("SELECT name, balance FROM accounts WHERE id = ?", (new_account_id,))
    return {
        "id": id,
        "amount": new_amount,
        "type": new_type,
        "payee": new_payee,
        "memo": new_memo,
        "date": new_date,
        "account": account["name"],
        "account_balance_after": account["balance"],
    }


def delete_transaction(db: Database, id: int) -> dict:
    txn = db.fetchone("SELECT * FROM transactions WHERE id = ?", (id,))
    if not txn:
        raise ValueError(f"Transaction id={id} not found")

    _reverse_balance(db, txn)
    db.execute("DELETE FROM transactions WHERE id = ?", (id,))

    account = db.fetchone("SELECT name, balance FROM accounts WHERE id = ?", (txn["account_id"],))
    return {
        "deleted_id": id,
        "account": account["name"],
        "account_balance_after": account["balance"],
    }


def get_transactions(
    db: Database,
    account_id: int | None = None,
    envelope_id: int | None = None,
    type: str | None = None,
    payee: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    conditions = []
    params = []

    if account_id:
        conditions.append("t.account_id = ?")
        params.append(account_id)
    if envelope_id:
        conditions.append("t.envelope_id = ?")
        params.append(envelope_id)
    if type:
        conditions.append("t.type = ?")
        params.append(type)
    if payee:
        conditions.append("t.payee LIKE ?")
        params.append(f"%{payee}%")
    if date_from:
        conditions.append("t.date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("t.date <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    return db.fetchall(
        f"""SELECT t.id, t.amount, t.type, t.payee, t.memo, t.date,
                   a.name AS account, e.name AS envelope, e.icon AS envelope_icon
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN envelopes e ON t.envelope_id = e.id
            {where}
            ORDER BY t.date DESC, t.id DESC
            LIMIT ?""",
        tuple(params),
    )


# ---------------------------------------------------------------------------
# FastMCP provider
# ---------------------------------------------------------------------------

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import CurrentContext
from envel_mcp.deps import get_user_db

mcp = FastMCP("transactions")


@mcp.tool(name="add_transaction")
async def _add_transaction_mcp(
    amount: float,
    type: str,
    account_id: int,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    transaction_date: str | None = None,
    ctx: Context = CurrentContext(),
) -> dict:
    """
    Record a new transaction.
    type: income | expense | transfer.
    transaction_date format YYYY-MM-DD (defaults to today).
    """
    await ctx.info(f"add_transaction: {type} {amount} payee={payee}")
    with get_user_db() as db:
        return add_transaction(db, amount, type, account_id, envelope_id, to_account_id, payee, memo, transaction_date)


@mcp.tool(name="get_transactions")
async def _get_transactions_mcp(
    account_id: int | None = None,
    envelope_id: int | None = None,
    type: str | None = None,
    payee: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    ctx: Context = CurrentContext(),
) -> list:
    """
    Query transactions. All filters are optional and combinable.
    payee: partial match (e.g. 'Grab' matches 'GrabFood').
    """
    await ctx.info(f"get_transactions: filters account={account_id} envelope={envelope_id} type={type} payee={payee}")
    with get_user_db() as db:
        return get_transactions(db, account_id, envelope_id, type, payee, date_from, date_to, limit)


@mcp.tool(name="edit_transaction")
async def _edit_transaction_mcp(
    id: int,
    amount: float | None = None,
    type: str | None = None,
    account_id: int | None = None,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    payee: str | None = None,
    memo: str | None = None,
    transaction_date: str | None = None,
    ctx: Context = CurrentContext(),
) -> dict:
    """Edit an existing transaction. Only provide fields you want to change."""
    await ctx.info(f"edit_transaction: id={id}")
    with get_user_db() as db:
        return edit_transaction(db, id, amount, type, account_id, envelope_id, to_account_id, payee, memo, transaction_date)


@mcp.tool(name="delete_transaction")
async def _delete_transaction_mcp(id: int, ctx: Context = CurrentContext()) -> dict:
    """Delete a transaction and reverse its effect on account balance."""
    await ctx.info(f"delete_transaction: id={id}")
    with get_user_db() as db:
        return delete_transaction(db, id)
