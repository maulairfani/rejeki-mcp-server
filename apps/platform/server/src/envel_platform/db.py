import hashlib
import hmac
import os
import sqlite3


_MIGRATED: set[str] = set()


def _derive_db_key(username: str) -> str | None:
    """Derive a per-user SQLCipher key from the master DB_ENCRYPTION_KEY.

    Returns None if DB_ENCRYPTION_KEY is not set (encryption disabled).
    """
    master = os.environ.get("DB_ENCRYPTION_KEY")
    if not master:
        return None
    return hmac.new(master.encode(), username.encode(), hashlib.sha256).hexdigest()


def _open_user_db(path: str, username: str) -> sqlite3.Connection:
    """Open a user's personal SQLite DB, applying SQLCipher encryption if configured."""
    key = _derive_db_key(username)
    if key:
        try:
            import sqlcipher3
            conn = sqlcipher3.connect(path)
            conn.execute(f"PRAGMA key = '{key}'")
            conn.row_factory = sqlite3.Row
            _ensure_migrated(conn, path)
            return conn
        except ImportError:
            pass
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_migrated(conn, path)
    return conn


def _ensure_migrated(conn: sqlite3.Connection, path: str) -> None:
    """Add columns the MCP server might not have migrated yet (idempotent, per-process cache)."""
    if path in _MIGRATED:
        return
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(envelopes)").fetchall()}
    if "sort_order" not in cols:
        conn.execute("ALTER TABLE envelopes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE envelopes SET sort_order = id WHERE sort_order = 0")
        conn.commit()
    _MIGRATED.add(path)


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
    return _open_user_db(row["db_path"], username)


def get_accounts(username: str) -> dict:
    with get_conn(username) as conn:
        rows = conn.execute(
            "SELECT id, name, type, balance FROM accounts ORDER BY type, name"
        ).fetchall()
    accounts = [dict(r) for r in rows]
    total = sum(r["balance"] for r in accounts)
    return {"accounts": accounts, "total": total}


def create_transaction(
    username: str,
    amount: float,
    type_: str,
    account_id: int,
    payee: str | None = None,
    memo: str | None = None,
    envelope_id: int | None = None,
    to_account_id: int | None = None,
    date: str | None = None,
) -> dict:
    sql = """
        INSERT INTO transactions (amount, type, account_id, envelope_id, to_account_id, payee, memo, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
    """
    with get_conn(username) as conn:
        cur = conn.execute(sql, (amount, type_, account_id, envelope_id, to_account_id, payee, memo, date))
        conn.commit()
        row = conn.execute(
            """SELECT t.id, t.date, t.type, t.amount, t.payee, t.memo,
                      a.name AS account_name, e.name AS envelope_name
               FROM transactions t
               LEFT JOIN accounts a ON t.account_id = a.id
               LEFT JOIN envelopes e ON t.envelope_id = e.id
               WHERE t.id = ?""",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


def get_envelope_status(username: str, period: str) -> list[dict]:
    sql = """
        SELECT
            e.id,
            e.name,
            e.icon,
            e.group_id,
            COALESCE(eg.name, 'Uncategorized') AS group_name,
            COALESCE(eg.sort_order, 999) AS group_sort,
            e.sort_order,
            e.target_type,
            e.target_amount,
            e.target_deadline,
            COALESCE(bp.assigned, 0) AS assigned,
            COALESCE(bp.carryover, 0) AS carryover,
            COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS activity
        FROM envelopes e
        LEFT JOIN envelope_groups eg ON e.group_id = eg.id
        LEFT JOIN budget_periods bp ON bp.envelope_id = e.id AND bp.period = ?
        LEFT JOIN transactions t ON t.envelope_id = e.id AND strftime('%Y-%m', t.date) = ?
        WHERE e.type = 'expense'
        GROUP BY e.id
        ORDER BY COALESCE(eg.sort_order, 999), e.sort_order, e.name
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


def reorder_envelopes(
    username: str, items: list[dict]
) -> None:
    """Atomically update sort_order (and optionally group_id) for envelopes.

    Each item: {id: int, group_id: int | None, sort_order: int}
    """
    with get_conn(username) as conn:
        for item in items:
            conn.execute(
                "UPDATE envelopes SET sort_order = ?, group_id = ? WHERE id = ?",
                (item["sort_order"], item.get("group_id"), item["id"]),
            )
        conn.commit()


def reorder_envelope_groups(username: str, items: list[dict]) -> None:
    """Atomically update sort_order for envelope groups.

    Each item: {id: int, sort_order: int}
    """
    with get_conn(username) as conn:
        for item in items:
            conn.execute(
                "UPDATE envelope_groups SET sort_order = ? WHERE id = ?",
                (item["sort_order"], item["id"]),
            )
        conn.commit()


def assign_envelope(username: str, envelope_id: int, period: str, assigned: float) -> None:
    sql = """
        INSERT INTO budget_periods (envelope_id, period, assigned)
        VALUES (?, ?, ?)
        ON CONFLICT(envelope_id, period) DO UPDATE SET assigned = excluded.assigned
    """
    with get_conn(username) as conn:
        conn.execute(sql, (envelope_id, period, assigned))
        conn.commit()


def get_scheduled(username: str) -> list[dict]:
    sql = """
        SELECT
            s.id, s.amount, s.type, s.payee, s.memo,
            s.scheduled_date, s.recurrence, s.is_active,
            a.name AS account_name,
            e.name AS envelope_name
        FROM scheduled_transactions s
        LEFT JOIN accounts a ON s.account_id = a.id
        LEFT JOIN envelopes e ON s.envelope_id = e.id
        WHERE s.is_active = 1
        ORDER BY s.scheduled_date
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


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


def get_transactions(
    username: str,
    period: str | None = None,
    account_id: int | None = None,
    envelope_id: int | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params: list = []

    if period:
        conditions.append("strftime('%Y-%m', t.date) = ?")
        params.append(period)
    if account_id is not None:
        conditions.append("t.account_id = ?")
        params.append(account_id)
    if envelope_id is not None:
        conditions.append("t.envelope_id = ?")
        params.append(envelope_id)
    if search:
        conditions.append("(t.payee LIKE ? OR t.memo LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT
            t.id, t.date, t.type, t.amount, t.payee, t.memo,
            a.name AS account_name,
            e.name AS envelope_name,
            e.icon AS envelope_icon
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN envelopes e ON t.envelope_id = e.id
        {where}
        ORDER BY t.date DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    with get_conn(username) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_wishlist(username: str, status: str | None = None) -> list[dict]:
    conditions = []
    params: list = []
    if status in ("wanted", "bought"):
        conditions.append("status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT id, name, price, priority, url, notes, status,
               created_at AS createdAt
        FROM wishlist
        {where}
        ORDER BY created_at DESC
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_daily_expenses(username: str, days: int = 30) -> list[dict]:
    """Return daily expense rows for the last N days, grouped by date + envelope."""
    sql = """
        SELECT
            date(t.date) AS day,
            COALESCE(e.id, 0) AS envelope_id,
            COALESCE(e.name, 'Uncategorized') AS envelope_name,
            SUM(t.amount) AS amount
        FROM transactions t
        LEFT JOIN envelopes e ON t.envelope_id = e.id
        WHERE t.type = 'expense'
          AND date(t.date) >= date('now', ?)
        GROUP BY day, e.id
        ORDER BY day
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


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
