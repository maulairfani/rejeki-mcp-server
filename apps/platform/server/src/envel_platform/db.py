import hashlib
import hmac
import os
import sqlite3


_MIGRATED: set[str] = set()

def _configure_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA busy_timeout = 10000")

def _prev_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"

def _compute_carryover(conn: sqlite3.Connection, envelope_id: int, period: str) -> float:
    prev_period = _prev_period(period)
    prev = conn.execute(
        "SELECT assigned, carryover FROM budget_periods WHERE envelope_id = ? AND period = ?",
        (envelope_id, prev_period),
    ).fetchone()
    if not prev:
        return 0.0

    prev_activity = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) AS activity
           FROM transactions
           WHERE envelope_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?""",
        (envelope_id, prev_period),
    ).fetchone()["activity"]
    return prev["carryover"] + prev["assigned"] - prev_activity


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
            conn = sqlcipher3.connect(path, timeout=10)
        except ImportError:
            pass
        else:
            try:
                conn.execute(f"PRAGMA key = '{key}'")
                _configure_sqlite(conn)
                conn.row_factory = sqlite3.Row
                _ensure_migrated(conn, path)
                return conn
            except Exception:
                conn.rollback()
                conn.close()
                raise
    conn = sqlite3.connect(path, timeout=10)
    try:
        _configure_sqlite(conn)
        conn.row_factory = sqlite3.Row
        _ensure_migrated(conn, path)
        return conn
    except Exception:
        conn.rollback()
        conn.close()
        raise


def _ensure_migrated(conn: sqlite3.Connection, path: str) -> None:
    """Add columns the MCP server might not have migrated yet (idempotent, per-process cache)."""
    if path in _MIGRATED:
        return
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(envelopes)").fetchall()}
    if "sort_order" not in cols:
        conn.execute("ALTER TABLE envelopes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE envelopes SET sort_order = id WHERE sort_order = 0")
        conn.commit()
    wishlist_cols = {r["name"] for r in conn.execute("PRAGMA table_info(wishlist)").fetchall()}
    if "icon" not in wishlist_cols:
        conn.execute("ALTER TABLE wishlist ADD COLUMN icon TEXT NOT NULL DEFAULT '🎁'")
        conn.commit()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transaction_tags (
            transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            tag_id         INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (transaction_id, tag_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag ON transaction_tags(tag_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id                          INTEGER PRIMARY KEY CHECK (id = 1),
            morning_briefing_enabled    INTEGER NOT NULL DEFAULT 1,
            morning_briefing_prompt     TEXT,
            morning_briefing_last_shown TEXT
        )
    """)
    conn.execute("INSERT OR IGNORE INTO user_settings (id) VALUES (1)")
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


def add_account(username: str, name: str, type_: str, balance: float) -> dict:
    with get_conn(username) as conn:
        cur = conn.execute(
            "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
            (name, type_, balance),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, name, type, balance FROM accounts WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def edit_account(username: str, account_id: int, name: str, type_: str) -> dict:
    with get_conn(username) as conn:
        conn.execute(
            "UPDATE accounts SET name = ?, type = ? WHERE id = ?",
            (name, type_, account_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, name, type, balance FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
    return dict(row)


def update_account_balance(username: str, account_id: int, balance: float) -> dict:
    with get_conn(username) as conn:
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (balance, account_id)
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, name, type, balance FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
    return dict(row)


def delete_account(username: str, account_id: int) -> None:
    with get_conn(username) as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()


def get_account_transactions(username: str, account_id: int, limit: int = 5) -> list[dict]:
    """Return recent transactions involving an account (either from or to)."""
    sql = """
        SELECT
            t.id, t.date, t.type, t.amount, t.payee, t.memo,
            t.account_id, t.envelope_id, t.to_account_id,
            a.name AS account_name,
            ta.name AS to_account_name,
            e.name AS envelope_name,
            e.icon AS envelope_icon,
            (
                SELECT GROUP_CONCAT(tg.name, '|')
                FROM transaction_tags tt
                JOIN tags tg ON tg.id = tt.tag_id
                WHERE tt.transaction_id = t.id
            ) AS tags
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN accounts ta ON t.to_account_id = ta.id
        LEFT JOIN envelopes e ON t.envelope_id = e.id
        WHERE t.account_id = ? OR t.to_account_id = ?
        ORDER BY t.date DESC
        LIMIT ?
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, (account_id, account_id, limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        raw = d.pop("tags", None)
        d["tags"] = sorted(raw.split("|")) if raw else []
        out.append(d)
    return out


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


def edit_transaction(
    username: str,
    transaction_id: int,
    amount: float | None = None,
    payee: str | None = None,
    memo: str | None = None,
    date: str | None = None,
    envelope_id: int | None = None,
    clear_envelope: bool = False,
) -> dict:
    sets = []
    params: list = []
    if amount is not None:
        sets.append("amount = ?")
        params.append(amount)
    if payee is not None:
        sets.append("payee = ?")
        params.append(payee)
    if memo is not None:
        sets.append("memo = ?")
        params.append(memo)
    if date is not None:
        sets.append("date = ?")
        params.append(date)
    if clear_envelope:
        sets.append("envelope_id = NULL")
    elif envelope_id is not None:
        sets.append("envelope_id = ?")
        params.append(envelope_id)
    if not sets:
        raise ValueError("Nothing to update")
    params.append(transaction_id)
    sql = f"UPDATE transactions SET {', '.join(sets)} WHERE id = ?"
    with get_conn(username) as conn:
        conn.execute(sql, params)
        conn.commit()
        row = conn.execute(
            """SELECT t.id, t.date, t.type, t.amount, t.payee, t.memo,
                      t.account_id, t.envelope_id, t.to_account_id,
                      a.name AS account_name, e.name AS envelope_name, e.icon AS envelope_icon
               FROM transactions t
               LEFT JOIN accounts a ON t.account_id = a.id
               LEFT JOIN envelopes e ON t.envelope_id = e.id
               WHERE t.id = ?""",
            (transaction_id,),
        ).fetchone()
    return dict(row)


def delete_transaction(username: str, transaction_id: int) -> None:
    with get_conn(username) as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()


def get_envelope_status(
    username: str, period: str, include_archived: bool = False
) -> list[dict]:
    archived_clause = "" if include_archived else " AND e.archived = 0"
    prev_period = _prev_period(period)
    sql = f"""
        WITH current_activity AS (
            SELECT envelope_id, COALESCE(SUM(amount), 0) AS activity
            FROM transactions
            WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
            GROUP BY envelope_id
        ),
        previous_activity AS (
            SELECT envelope_id, COALESCE(SUM(amount), 0) AS activity
            FROM transactions
            WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
            GROUP BY envelope_id
        )
        SELECT
            e.id,
            e.name,
            e.icon,
            e.group_id,
            e.archived,
            COALESCE(eg.name, 'Uncategorized') AS group_name,
            COALESCE(eg.sort_order, 999) AS group_sort,
            e.sort_order,
            e.target_type,
            e.target_amount,
            e.target_deadline,
            COALESCE(bp.assigned, 0) AS assigned,
            CASE
                WHEN bp.id IS NOT NULL THEN bp.carryover
                ELSE COALESCE(prev_bp.carryover + prev_bp.assigned - COALESCE(pa.activity, 0), 0)
            END AS carryover,
            COALESCE(ca.activity, 0) AS activity
        FROM envelopes e
        LEFT JOIN envelope_groups eg ON e.group_id = eg.id
        LEFT JOIN budget_periods bp ON bp.envelope_id = e.id AND bp.period = ?
        LEFT JOIN budget_periods prev_bp ON prev_bp.envelope_id = e.id AND prev_bp.period = ?
        LEFT JOIN current_activity ca ON ca.envelope_id = e.id
        LEFT JOIN previous_activity pa ON pa.envelope_id = e.id
        WHERE e.type = 'expense'{archived_clause}
        ORDER BY COALESCE(eg.sort_order, 999), e.sort_order, e.name
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, (period, prev_period, period, prev_period)).fetchall()
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


def set_envelope_target(
    username: str,
    envelope_id: int,
    target_type: str | None,
    target_amount: float | None,
    target_deadline: str | None,
) -> None:
    with get_conn(username) as conn:
        conn.execute(
            "UPDATE envelopes SET target_type = ?, target_amount = ?, target_deadline = ? WHERE id = ?",
            (target_type, target_amount, target_deadline, envelope_id),
        )
        conn.commit()


def assign_envelope(username: str, envelope_id: int, period: str, assigned: float) -> None:
    sql = """
        INSERT INTO budget_periods (envelope_id, period, assigned, carryover)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(envelope_id, period) DO UPDATE SET assigned = excluded.assigned
    """
    with get_conn(username) as conn:
        conn.execute(
            sql,
            (envelope_id, period, assigned, _compute_carryover(conn, envelope_id, period)),
        )
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
            t.account_id, t.envelope_id, t.to_account_id,
            a.name AS account_name,
            ta.name AS to_account_name,
            e.name AS envelope_name,
            e.icon AS envelope_icon,
            (
                SELECT GROUP_CONCAT(tg.name, '|')
                FROM transaction_tags tt
                JOIN tags tg ON tg.id = tt.tag_id
                WHERE tt.transaction_id = t.id
            ) AS tags
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN accounts ta ON t.to_account_id = ta.id
        LEFT JOIN envelopes e ON t.envelope_id = e.id
        {where}
        ORDER BY t.date DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    with get_conn(username) as conn:
        rows = conn.execute(sql, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        raw = d.pop("tags", None)
        d["tags"] = sorted(raw.split("|")) if raw else []
        out.append(d)
    return out


def list_tags(username: str) -> list[dict]:
    """Return all tags with usage counts, ordered by most-used first."""
    sql = """
        SELECT tg.id, tg.name,
               COALESCE(c.usage, 0) AS usage
        FROM tags tg
        LEFT JOIN (
            SELECT tag_id, COUNT(*) AS usage
            FROM transaction_tags
            GROUP BY tag_id
        ) c ON c.tag_id = tg.id
        ORDER BY usage DESC, tg.name COLLATE NOCASE ASC
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def set_transaction_tags(username: str, transaction_id: int, tag_names: list[str]) -> list[str]:
    """Replace the tag set for a transaction. Auto-creates tags that don't exist.

    Tag names are normalized (stripped, deduped case-insensitively).
    Returns the final set of tag names attached to the transaction.
    """
    seen: dict[str, str] = {}
    for raw in tag_names:
        name = (raw or "").strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = name
    cleaned = list(seen.values())

    with get_conn(username) as conn:
        # Confirm transaction exists.
        row = conn.execute(
            "SELECT 1 FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Transaction {transaction_id} not found")

        tag_ids: list[int] = []
        for name in cleaned:
            existing = conn.execute(
                "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if existing:
                tag_ids.append(existing["id"])
            else:
                cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
                tag_ids.append(cur.lastrowid)

        conn.execute(
            "DELETE FROM transaction_tags WHERE transaction_id = ?", (transaction_id,)
        )
        conn.executemany(
            "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
            [(transaction_id, tid) for tid in tag_ids],
        )
        conn.commit()

        rows = conn.execute(
            """
            SELECT tg.name FROM transaction_tags tt
            JOIN tags tg ON tg.id = tt.tag_id
            WHERE tt.transaction_id = ?
            ORDER BY tg.name COLLATE NOCASE
            """,
            (transaction_id,),
        ).fetchall()
    return [r["name"] for r in rows]


def get_morning_briefing(username: str) -> dict:
    """Return the user's morning-briefing settings."""
    with get_conn(username) as conn:
        row = conn.execute(
            """
            SELECT morning_briefing_enabled,
                   morning_briefing_prompt,
                   morning_briefing_last_shown
            FROM user_settings WHERE id = 1
            """
        ).fetchone()
    if not row:
        return {"enabled": True, "prompt": None, "last_shown": None}
    return {
        "enabled": bool(row["morning_briefing_enabled"]),
        "prompt": row["morning_briefing_prompt"],
        "last_shown": row["morning_briefing_last_shown"],
    }


def update_morning_briefing(
    username: str,
    enabled: bool | None = None,
    prompt: str | None = None,
    clear_prompt: bool = False,
) -> dict:
    """Patch one or more morning-briefing fields. Pass clear_prompt=True to wipe."""
    sets: list[str] = []
    params: list = []
    if enabled is not None:
        sets.append("morning_briefing_enabled = ?")
        params.append(1 if enabled else 0)
    if clear_prompt:
        sets.append("morning_briefing_prompt = NULL")
    elif prompt is not None:
        sets.append("morning_briefing_prompt = ?")
        params.append(prompt.strip() or None)
    if not sets:
        return get_morning_briefing(username)
    params.append(1)
    sql = f"UPDATE user_settings SET {', '.join(sets)} WHERE id = ?"
    with get_conn(username) as conn:
        conn.execute(sql, params)
        conn.commit()
    return get_morning_briefing(username)


def get_wishlist(username: str, status: str | None = None) -> list[dict]:
    conditions = []
    params: list = []
    if status in ("wanted", "bought"):
        conditions.append("status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT id, name, icon, price, priority, url, notes, status,
               created_at AS createdAt
        FROM wishlist
        {where}
        ORDER BY created_at DESC
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_daily_expenses(username: str, period: str) -> list[dict]:
    """Return daily expense rows for a YYYY-MM period, grouped by date + envelope."""
    sql = """
        SELECT
            date(t.date) AS day,
            COALESCE(e.id, 0) AS envelope_id,
            COALESCE(e.name, 'Uncategorized') AS envelope_name,
            SUM(t.amount) AS amount
        FROM transactions t
        LEFT JOIN envelopes e ON t.envelope_id = e.id
        WHERE t.type = 'expense'
          AND strftime('%Y-%m', t.date) = ?
        GROUP BY day, e.id
        ORDER BY day
    """
    with get_conn(username) as conn:
        rows = conn.execute(sql, (period,)).fetchall()
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
