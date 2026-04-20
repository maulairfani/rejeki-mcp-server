import logging
import os
import re
import sqlite3
from pathlib import Path

import bcrypt
from fastapi import Request

logger = logging.getLogger("envel_platform")


class NotAuthenticated(Exception):
    pass


class SignupError(Exception):
    """Raised when signup fails. `field` points to the offending input (or None for general)."""

    def __init__(self, message: str, field: str | None = None, code: str = "invalid"):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LEN = 8


def require_user(request: Request) -> str:
    username = request.session.get("username")
    if not username:
        raise NotAuthenticated()
    return username


def _users_db_path() -> str:
    users_db = os.environ.get("USERS_DB")
    if not users_db:
        raise RuntimeError("USERS_DB env var not set")
    return users_db


def _connect_users_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_users_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def check_credentials(username: str, password: str) -> bool:
    try:
        conn = _connect_users_db()
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
    except Exception:
        return False
    if not row:
        logger.warning("login_failed", extra={"username": username, "reason": "unknown_user"})
        return False
    if not row["password_hash"]:
        logger.warning("login_failed", extra={"username": username, "reason": "no_password_set"})
        return False
    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        logger.warning("login_failed", extra={"username": username, "reason": "bad_password"})
        return False
    logger.info("login_success", extra={"username": username})
    return True


def username_available(username: str) -> bool:
    if not USERNAME_RE.match(username):
        return False
    conn = _connect_users_db()
    row = conn.execute(
        "SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,)
    ).fetchone()
    conn.close()
    return row is None


def _default_db_path(username: str) -> str:
    # Mirrors scripts/add_user.py: ./users/<username>.db relative to project root.
    # project root = apps/platform/server/src/envel_platform/auth.py -> up 5 levels
    root = Path(__file__).resolve().parents[4]
    return str(root / "users" / f"{username}.db")


def _init_user_db(db_path: str, username: str) -> None:
    """Create the user's per-user SQLite DB file. Encryption applied if DB_ENCRYPTION_KEY set."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    master = os.environ.get("DB_ENCRYPTION_KEY")
    if master:
        try:
            import hashlib
            import hmac
            import sqlcipher3
            key = hmac.new(master.encode(), username.encode(), hashlib.sha256).hexdigest()
            conn = sqlcipher3.connect(db_path)
            conn.execute(f"PRAGMA key = '{key}'")
            conn.close()
            return
        except ImportError:
            logger.warning("sqlcipher_missing_creating_unencrypted_db", extra={"username": username})
    conn = sqlite3.connect(db_path)
    conn.close()


def create_user(name: str, email: str, username: str, password: str) -> str:
    """Create a new user with username + password.

    Raises SignupError on validation failure or duplicate username/email.
    Returns the username on success.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()
    username = (username or "").strip()

    if not name:
        raise SignupError("Name is required.", field="name", code="required")
    if not USERNAME_RE.match(username):
        raise SignupError(
            "Username must be 3-32 chars: letters, numbers, underscore, dash.",
            field="username",
            code="invalid_format",
        )
    if not EMAIL_RE.match(email):
        raise SignupError("Please enter a valid email address.", field="email", code="invalid_format")
    if len(password) < PASSWORD_MIN_LEN:
        raise SignupError(f"Password must be at least {PASSWORD_MIN_LEN} characters.", field="password", code="too_short")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise SignupError("Password must contain at least one letter and one number.", field="password", code="too_weak")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db_path = _default_db_path(username)

    conn = _connect_users_db()
    try:
        existing = conn.execute(
            "SELECT username FROM users WHERE username = ? OR email = ? LIMIT 1",
            (username, email),
        ).fetchone()
        if existing:
            # Disambiguate which field collided
            u = conn.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,)).fetchone()
            if u:
                raise SignupError("This username is already taken.", field="username", code="taken")
            raise SignupError("An account with this email already exists.", field="email", code="taken")

        conn.execute(
            "INSERT INTO users (username, name, email, password_hash, db_path) VALUES (?, ?, ?, ?, ?)",
            (username, name, email, password_hash, db_path),
        )
        conn.commit()
    finally:
        conn.close()

    _init_user_db(db_path, username)
    logger.info("signup_success", extra={"username": username, "email": email})
    return username
