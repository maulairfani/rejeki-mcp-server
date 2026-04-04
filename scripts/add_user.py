"""
Add or update a user in users.db.

Usage:
    python scripts/add_user.py <username> <password> [--db-path PATH]
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import bcrypt

USERS_DB = Path(__file__).parent.parent / "users.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    db_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def main():
    parser = argparse.ArgumentParser(description="Add or update a user in users.db")
    parser.add_argument("username", help="Username")
    parser.add_argument("password", help="Password (will be hashed with bcrypt)")
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
    args = parser.parse_args()

    db_path = args.db_path or str(Path(__file__).parent.parent / "users" / f"{args.username}.db")
    users_db = Path(args.users_db)

    password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()

    conn = sqlite3.connect(str(users_db))
    conn.execute(CREATE_TABLE)

    existing = conn.execute(
        "SELECT username FROM users WHERE username = ?", (args.username,)
    ).fetchone()

    if existing:
        print(f"User '{args.username}' already exists. Updating...")
        conn.execute(
            "UPDATE users SET password_hash = ?, db_path = ? WHERE username = ?",
            (password_hash, db_path, args.username),
        )
    else:
        conn.execute(
            "INSERT INTO users (username, password_hash, db_path) VALUES (?, ?, ?)",
            (args.username, password_hash, db_path),
        )

    conn.commit()
    conn.close()

    # Ensure user db directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"User '{args.username}' saved to {users_db}")
    print(f"DB path: {db_path}")


if __name__ == "__main__":
    main()
