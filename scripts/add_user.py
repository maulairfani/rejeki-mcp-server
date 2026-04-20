"""
Add or update a user in users.db.

Usage:
    python scripts/add_user.py <username> <password> [--db-path PATH]
"""
import argparse
import hashlib
import hmac
import os
import sqlite3
import sys
from pathlib import Path

import bcrypt

USERS_DB = Path(__file__).parent.parent / "users.db"


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    name          TEXT,
    email         TEXT COLLATE NOCASE,
    password_hash TEXT,
    db_path       TEXT NOT NULL,
    google_sub    TEXT,
    google_email  TEXT,
    google_refresh_token TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email      ON users(email)      WHERE email      IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL;
"""


def _derive_db_key(username: str, master: str) -> str:
    return hmac.new(master.encode(), username.encode(), hashlib.sha256).hexdigest()


def _init_user_db(db_path: str, username: str, encryption_key: str | None) -> None:
    """Initialize the user's personal SQLite DB (encrypted if key provided)."""
    if encryption_key:
        try:
            import sqlcipher3
            conn = sqlcipher3.connect(db_path)
            key = _derive_db_key(username, encryption_key)
            conn.execute(f"PRAGMA key = '{key}'")
        except ImportError:
            print("Warning: sqlcipher3 not installed, creating unencrypted DB.", file=sys.stderr)
            conn = sqlite3.connect(db_path)
    else:
        conn = sqlite3.connect(db_path)
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Add or update a user in users.db")
    parser.add_argument("username", help="Username")
    parser.add_argument("password", help="Password (will be hashed with bcrypt)")
    parser.add_argument("--name", default=None, help="Display name (defaults to username)")
    parser.add_argument("--email", default=None, help="Email address (optional)")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to user's SQLite DB (default: ./users/<username>.db)",
    )
    parser.add_argument(
        "--users-db",
        default=str(USERS_DB),
        help=f"Path to users.db (default: {USERS_DB})",
    )
    parser.add_argument(
        "--encryption-key",
        default=None,
        help="Master encryption key for SQLCipher (overrides DB_ENCRYPTION_KEY env var)",
    )
    args = parser.parse_args()

    db_path = args.db_path or str(Path(__file__).parent.parent / "users" / f"{args.username}.db")
    users_db = Path(args.users_db)
    encryption_key = args.encryption_key or os.environ.get("DB_ENCRYPTION_KEY")
    name = args.name or args.username

    password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()

    conn = sqlite3.connect(str(users_db))
    conn.executescript(CREATE_TABLE)

    existing = conn.execute(
        "SELECT username FROM users WHERE username = ?", (args.username,)
    ).fetchone()

    if existing:
        print(f"User '{args.username}' already exists. Updating...")
        conn.execute(
            "UPDATE users SET name = ?, email = ?, password_hash = ?, db_path = ? WHERE username = ?",
            (name, args.email, password_hash, db_path, args.username),
        )
    else:
        conn.execute(
            "INSERT INTO users (username, name, email, password_hash, db_path) VALUES (?, ?, ?, ?, ?)",
            (args.username, name, args.email, password_hash, db_path),
        )

    conn.commit()
    conn.close()

    # Ensure user db directory exists and initialize DB (with encryption if configured)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _init_user_db(db_path, args.username, encryption_key)

    print(f"User '{args.username}' saved to {users_db}")
    print(f"DB path: {db_path}")
    if encryption_key:
        print("DB encryption: enabled (SQLCipher)")
    else:
        print("DB encryption: disabled (set DB_ENCRYPTION_KEY to enable)")


if __name__ == "__main__":
    main()
