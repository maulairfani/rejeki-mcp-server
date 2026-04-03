import sqlite3
from contextlib import asynccontextmanager

from fastmcp import Context
from fastmcp.server.dependencies import get_access_token
from rejeki.database import Database, init_db
from rejeki.platform_db import get_user_by_workos_id


@asynccontextmanager
async def get_user_db(ctx: Context):
    token = get_access_token()
    if not token:
        raise RuntimeError("Token tidak ditemukan — pastikan AuthKitProvider terkonfigurasi")

    workos_id = token.claims.get("sub") or token.claims.get("client_id")
    if not workos_id:
        raise RuntimeError("Token tidak mengandung claim 'sub' atau 'client_id'")

    user = get_user_by_workos_id(workos_id)
    if not user:
        raise RuntimeError(f"User dengan WorkOS ID '{workos_id}' tidak terdaftar")

    conn = sqlite3.connect(user["db_path"])
    db = Database(conn)
    init_db(db)

    try:
        yield db
    finally:
        db.close()
