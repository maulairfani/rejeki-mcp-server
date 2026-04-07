from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from envel_platform.auth import NotAuthenticated, check_credentials, require_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    if not check_credentials(body.username, body.password):
        return JSONResponse({"detail": "Invalid username or password"}, status_code=401)
    request.session["username"] = body.username
    return {"username": body.username}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/session")
async def session(request: Request):
    username = request.session.get("username")
    if not username:
        return JSONResponse({"authenticated": False}, status_code=401)
    return {"authenticated": True, "username": username}
