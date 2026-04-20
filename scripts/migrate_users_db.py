"""
Migrate users.db to the new schema (name, email, nullable password_hash, google fields).

Two modes:
  --in-place   Keep existing users; add new columns (name/email nullable, populated
               from username for name, left NULL for email). Safe, non-destructive.
  --wipe       Drop the users table and recreate from scratch. Destructive — deletes
               all user metadata in users.db. Per-user SQLite files under ./users/
               are left untouched.

Usage:
    python scripts/migrate_users_db.py --in-place
    python scripts/migrate_users_db.py --wipe
    python scripts/migrate_users_db.py --wipe --users-db /path/to/users.db
"""
import argparse
import sqlite3
import sys
from pathlib import Path

USERS_DB = Path(__file__).parent.parent / "users.db"

NEW_SCHEMA = """
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


def migrate_in_place(conn: sqlite3.Connection) -> None:
    for col, definition in [
        ("name",                 "TEXT"),
        ("email",                "TEXT COLLATE NOCASE"),
        ("google_sub",           "TEXT"),
        ("google_email",         "TEXT"),
        ("google_refresh_token", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass

    # Backfill name from username for rows where name is NULL
    conn.execute("UPDATE users SET name = username WHERE name IS NULL")

    for stmt in [
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email      ON users(email)      WHERE email      IS NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL",
    ]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()


def wipe_and_recreate(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.executescript(NEW_SCHEMA)
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate users.db schema")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--in-place", action="store_true", help="Non-destructive column add")
    mode.add_argument("--wipe", action="store_true", help="Drop and recreate users table")
    parser.add_argument("--users-db", default=str(USERS_DB), help=f"Path to users.db (default: {USERS_DB})")
    args = parser.parse_args()

    users_db = Path(args.users_db)
    if not users_db.exists():
        print(f"users.db not found at {users_db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(users_db))
    conn.row_factory = sqlite3.Row

    before = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    if args.wipe:
        wipe_and_recreate(conn)
        print(f"Wiped users table. Removed {before} user(s). Schema recreated.")
    else:
        migrate_in_place(conn)
        print(f"Migrated users table in place. {before} user(s) preserved.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
