import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date

from envel_mcp.database import Database, init_db

# Set per-request by EnvelTokenVerifier after successful token introspection.
_db_path: ContextVar[str] = ContextVar("db_path")
_db_username: ContextVar[str] = ContextVar("db_username")

def _configure_sqlite(conn) -> None:
    conn.execute("PRAGMA busy_timeout = 10000")


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
            conn = sqlcipher3.connect(path, timeout=10)
            conn.execute(f"PRAGMA key = '{key}'")
        except ImportError:
            conn = sqlite3.connect(path, timeout=10)
    else:
        conn = sqlite3.connect(path, timeout=10)

    try:
        _configure_sqlite(conn)
        db = Database(conn)
        init_db(db)
        yield db
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Morning briefing piggyback ─────────────────────────────────────────────
#
# Fires once per day. The hint is attached to a tool's response by calling
# `attach_briefing_hint(db, result)` at the end of a tool wrapper. The first
# tool call of the day stamps `morning_briefing_last_shown=today` so later
# calls in the same day stay quiet.

_BRIEFING_SETUP_HINT = (
    "Daily briefing is enabled but the user hasn't configured what to include yet. "
    "Before answering their request, briefly tell them this feature exists, ask 1-2 "
    "questions about what they want each morning (e.g. which budgets to monitor, "
    "whether to recap yesterday, scheduled transactions to flag), summarize their "
    "answer into a clear instruction, and save it via the `set_morning_briefing` "
    "tool. Keep the conversation short — a couple of exchanges at most."
)


def _briefing_run_hint(prompt: str) -> str:
    return (
        "Daily briefing time. Before answering the user's actual request, "
        "execute the following user-defined briefing instruction by calling "
        "whatever envel tools you need, then narrate the result concisely:\n\n"
        f"---\n{prompt}\n---\n\n"
        "After the briefing, continue with the user's original message."
    )


def _check_briefing_due(db: Database) -> str | None:
    row = db.fetchone(
        """
        SELECT morning_briefing_enabled    AS enabled,
               morning_briefing_prompt     AS prompt,
               morning_briefing_last_shown AS last_shown
        FROM user_settings WHERE id = 1
        """
    )
    if not row or not row["enabled"]:
        return None
    today = date.today().isoformat()
    if row["last_shown"] == today:
        return None
    # Stamp first so concurrent calls don't double-fire.
    db.execute(
        "UPDATE user_settings SET morning_briefing_last_shown = ? WHERE id = 1",
        (today,),
    )
    if not row["prompt"]:
        return _BRIEFING_SETUP_HINT
    return _briefing_run_hint(row["prompt"])


def attach_briefing_hint(db: Database, result):
    """If today's briefing hasn't fired yet, attach a hint to a dict result.

    No-op for non-dict results (lists, scalars). Use this at the end of a tool
    wrapper that returns a dict — the AI client reads `_assistant_hint` and
    acts on it before continuing with the user's request.
    """
    if not isinstance(result, dict):
        return result
    hint = _check_briefing_due(db)
    if hint:
        result["_assistant_hint"] = hint
    return result
