import logging
import os
import sqlite3
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

auth_router = APIRouter()

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

logger = logging.getLogger("rejeki_platform")


class NotAuthenticated(Exception):
    pass


def require_user(request: Request) -> str:
    username = request.session.get("username")
    if not username:
        raise NotAuthenticated()
    return username


def _check_credentials(username: str, password: str) -> bool:
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


@auth_router.get("/login")
async def login_page(request: Request):
    return _TEMPLATES.TemplateResponse(request, "login.html", {"error": False})


@auth_router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    if _check_credentials(username, password):
        request.session["username"] = username
        return RedirectResponse(url="/", status_code=302)
    return _TEMPLATES.TemplateResponse(
        request, "login.html", {"error": True}, status_code=401
    )


@auth_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
