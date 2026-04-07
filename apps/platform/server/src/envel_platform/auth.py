import logging
import os
import sqlite3

import bcrypt
from fastapi import Request

logger = logging.getLogger("envel_platform")


class NotAuthenticated(Exception):
    pass


def require_user(request: Request) -> str:
    username = request.session.get("username")
    if not username:
        raise NotAuthenticated()
    return username


def check_credentials(username: str, password: str) -> bool:
    users_db = os.environ.get("USERS_DB")
    if not users_db:
        return False
    try:
        conn = sqlite3.connect(users_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
    except Exception:
        return False
    if not row:
        logger.warning("login_failed", extra={"username": username, "reason": "unknown_user"})
        return False
    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        logger.warning("login_failed", extra={"username": username, "reason": "bad_password"})
        return False
    logger.info("login_success", extra={"username": username})
    return True
