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
        cur = self._conn.execute(query, params)
        self._conn.commit()
        return cur.lastrowid

    def close(self):
        self._conn.close()


def init_db(db: Database) -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [s.strip() for s in schema.split(";") if s.strip()]
    for stmt in statements:
        db._conn.execute(stmt)
    db._conn.commit()
