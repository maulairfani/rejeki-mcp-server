import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar

from envel_mcp.database import Database, init_db

# Set per-request by EnvelTokenVerifier after successful token introspection.
_db_path: ContextVar[str] = ContextVar("db_path")
_db_username: ContextVar[str] = ContextVar("db_username")


def _derive_db_key(username: str) -> str | None:
    """Derive a per-user SQLCipher key from the master DB_ENCRYPTION_KEY.

    Returns None if DB_ENCRYPTION_KEY is not set (encryption disabled).
    """
    master = os.environ.get("DB_ENCRYPTION_KEY")
    if not master:
        return None
    return hmac.new(master.encode(), username.encode(), hashlib.sha256).hexdigest()


@contextmanager
def get_user_db():
    """Return an open Database for the currently authenticated user.

    In production the path and username come from the token introspection response.
    In test mode (TEST_TOKEN set) it falls back to TEST_DB / TEST_USERNAME env vars.

    If DB_ENCRYPTION_KEY is set, the user DB is opened via SQLCipher. Otherwise
    it falls back to plain sqlite3 (dev / test mode with no encryption key).
    """
    try:
        path = _db_path.get()
    except LookupError:
        path = os.environ.get("TEST_DB", os.path.expanduser("~/envel.db"))

    try:
        username = _db_username.get()
    except LookupError:
        username = os.environ.get("TEST_USERNAME", "test-user")

    key = _derive_db_key(username)

    if key:
        try:
            import sqlcipher3
            conn = sqlcipher3.connect(path)
            conn.execute(f"PRAGMA key = '{key}'")
        except ImportError:
            conn = sqlite3.connect(path)
    else:
        conn = sqlite3.connect(path)

    db = Database(conn)
    init_db(db)
    try:
        yield db
    finally:
        db.close()
