import os
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar

from rejeki_mcp.database import Database, init_db

# Set per-request by RejekiTokenVerifier after successful token introspection.
_db_path: ContextVar[str] = ContextVar("db_path")


@contextmanager
def get_user_db():
    """Return an open Database for the currently authenticated user.

    In production the path comes from the token introspection response.
    In test mode (TEST_TOKEN set) it falls back to the TEST_DB env var.
    """
    try:
        path = _db_path.get()
    except LookupError:
        path = os.environ.get("TEST_DB", os.path.expanduser("~/rejeki.db"))

    conn = sqlite3.connect(path)
    db = Database(conn)
    init_db(db)
    try:
        yield db
    finally:
        db.close()
