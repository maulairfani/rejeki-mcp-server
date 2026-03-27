from datetime import date
from rejeki.database import execute, fetchall, fetchone


def add_transaction(
    amount: float,
    type: str,
    account_id: int,
    category_id: int | None = None,
    to_account_id: int | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict:
    txn_date = transaction_date or date.today().isoformat()

    txn_id = execute(
        """INSERT INTO transactions
           (amount, type, category_id, account_id, to_account_id, description, date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (amount, type, category_id, account_id, to_account_id, description, txn_date),
    )

    if type == "expense":
        execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
    elif type == "income":
        execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    elif type == "transfer":
        execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
        execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

    account = fetchone("SELECT name, balance FROM accounts WHERE id = ?", (account_id,))
    return {
        "id": txn_id,
        "amount": amount,
        "type": type,
        "date": txn_date,
        "description": description,
        "account": account["name"],
        "account_balance_after": account["balance"],
    }


def get_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    conditions = []
    params = []

    if account_id:
        conditions.append("t.account_id = ?")
        params.append(account_id)
    if category_id:
        conditions.append("t.category_id = ?")
        params.append(category_id)
    if type:
        conditions.append("t.type = ?")
        params.append(type)
    if date_from:
        conditions.append("t.date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("t.date <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    return fetchall(
        f"""SELECT t.id, t.amount, t.type, t.description, t.date,
                   a.name AS account, c.name AS category, c.icon AS category_icon
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN categories c ON t.category_id = c.id
            {where}
            ORDER BY t.date DESC, t.id DESC
            LIMIT ?""",
        tuple(params),
    )
