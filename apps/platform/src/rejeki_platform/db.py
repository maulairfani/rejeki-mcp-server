import os
import sqlite3


def get_conn(username: str) -> sqlite3.Connection:
    users_db = os.environ.get("USERS_DB")
    if not users_db:
        raise RuntimeError("USERS_DB env var not set")
    conn = sqlite3.connect(users_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT db_path FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Unknown user: {username}")
    user_conn = sqlite3.connect(row["db_path"])
    user_conn.row_factory = sqlite3.Row
    return user_conn


def get_accounts(username: str) -> dict:
    with get_conn(username) as conn:
        rows = conn.execute(
            "SELECT name, type, balance FROM accounts ORDER BY type, name"
        ).fetchall()
    accounts = [dict(r) for r in rows]
    total = sum(r["balance"] for r in accounts)
    return {"accounts": accounts, "total": total}


def get_envelope_status(username: str, period: str) -> list[dict]:
    sql = """
        SELECT
            e.id,
            e.name,
            e.icon,
            COALESCE(eg.name, 'Uncategorized') AS group_name,
            COALESCE(bp.assigned, 0) AS assigned,
            COALESCE(bp.carryover, 0) AS carryover,
            COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS activity
        FROM envelopes e
        LEFT JOIN envelope_groups eg ON e.group_id = eg.id
        LEFT JOIN budget_periods bp ON bp.envelope_id = e.id AND bp.period = ?
        LEFT JOIN transactions t ON t.envelope_id = e.id AND strftime('%Y-%m', t.date) = ?
        WHERE e.type = 'expense'
        GROUP BY e.id
        ORDER BY COALESCE(eg.sort_order, 999), e.name
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, (period, period)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["available"] = d["assigned"] + d["carryover"] - d["activity"]
        if d["assigned"] > 0:
            d["pct"] = min(100, d["activity"] / d["assigned"] * 100)
        elif d["activity"] > 0:
            d["pct"] = 100
        else:
            d["pct"] = 0
        d["overspent"] = d["available"] < 0
        result.append(d)
    return result


def get_monthly_summary(username: str, period: str) -> dict:
    sql = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE strftime('%Y-%m', date) = ?
    """
    with get_conn(username) as conn:
        row = conn.execute(sql, (period,)).fetchone()
    income = row["income"]
    expense = row["expense"]
    return {"income": income, "expense": expense, "surplus": income - expense}


def get_spending_trend(username: str, months: int = 6) -> dict:
    sql = """
        SELECT
            strftime('%Y-%m', date) AS month,
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE date >= date('now', ?)
        GROUP BY month
        ORDER BY month
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, (f"-{months} months",)).fetchall()
    return {
        "labels": [r["month"] for r in rows],
        "incomes": [r["income"] for r in rows],
        "expenses": [r["expense"] for r in rows],
    }
