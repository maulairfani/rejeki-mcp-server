from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _row_to_dict(cursor, row) -> dict:
    return {col[0]: val for col, val in zip(cursor.description, row)}


class Database:
    def __init__(self, conn):
        self._conn = conn

    def fetchone(self, query: str, params: tuple = ()) -> dict | None:
        cur = self._conn.execute(query, params)
        row = cur.fetchone()
        return _row_to_dict(cur, row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        cur = self._conn.execute(query, params)
        rows = cur.fetchall()
        return [_row_to_dict(cur, r) for r in rows]

    def execute(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE. Returns lastrowid."""
        try:
            cur = self._conn.execute(query, params)
            self._conn.commit()
            return cur.lastrowid
        except Exception:
            self._conn.rollback()
            raise

    def close(self):
        self._conn.close()


def init_db(db: Database) -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    try:
        db._conn.executescript(schema)
        db._conn.commit()
    except Exception:
        db._conn.rollback()
        raise
    _migrate(db)


def _migrate(db: Database) -> None:
    """Apply schema migrations idempotently for existing user DBs."""
    cols = {row["name"] for row in db.fetchall("PRAGMA table_info(envelopes)")}
    if "archived" not in cols:
        db._conn.execute("ALTER TABLE envelopes ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
        db._conn.commit()
    if "sort_order" not in cols:
        db._conn.execute("ALTER TABLE envelopes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        # Backfill by id so existing order is stable when user first drags
        db._conn.execute("UPDATE envelopes SET sort_order = id WHERE sort_order = 0")
        db._conn.commit()

    wishlist_cols = {row["name"] for row in db.fetchall("PRAGMA table_info(wishlist)")}
    if "icon" not in wishlist_cols:
        db._conn.execute("ALTER TABLE wishlist ADD COLUMN icon TEXT NOT NULL DEFAULT '🎁'")
        db._conn.commit()

    db._conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    db._conn.execute("""
        CREATE TABLE IF NOT EXISTS transaction_tags (
            transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            tag_id         INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (transaction_id, tag_id)
        )
    """)
    db._conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag ON transaction_tags(tag_id)"
    )
    db._conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id                          INTEGER PRIMARY KEY CHECK (id = 1),
            morning_briefing_enabled    INTEGER NOT NULL DEFAULT 1,
            morning_briefing_prompt     TEXT,
            morning_briefing_last_shown TEXT
        )
    """)
    db._conn.execute("INSERT OR IGNORE INTO user_settings (id) VALUES (1)")
    db._conn.commit()
