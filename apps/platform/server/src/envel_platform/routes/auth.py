import logging
import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from envel_platform.auth import (
    SignupError,
    check_credentials,
    create_user,
    username_available,
)

router = APIRouter()
logger = logging.getLogger("envel_platform")


def _auth_server_url() -> str:
    return os.environ.get("AUTH_SERVER_URL", "http://localhost:9004")


def _auth_public_url() -> str:
    """Browser-visible URL of the auth server (for redirects)."""
    return os.environ.get("AS_BASE_URL", _auth_server_url())


def _service_secret() -> str:
    return os.environ.get("PLATFORM_SERVICE_SECRET", "")


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    name: str
    email: str
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    if not check_credentials(body.username, body.password):
        return JSONResponse({"detail": "Invalid username or password"}, status_code=401)
    request.session["username"] = body.username
    return {"username": body.username}


@router.post("/signup")
async def signup(body: SignupRequest, request: Request):
    try:
        username = create_user(
            name=body.name,
            email=body.email,
            username=body.username,
            password=body.password,
        )
    except SignupError as e:
        return JSONResponse(
            {"detail": e.message, "field": e.field, "code": e.code},
            status_code=409 if e.code == "taken" else 400,
        )
    request.session["username"] = username
    return {"username": username}


@router.get("/username-available")
async def username_available_endpoint(u: str):
    return {"available": username_available(u)}


# ─── Google OAuth (via auth-server) ─────────────────────────────────────────

@router.get("/google-start")
async def google_start(intent: str = "signup"):
    """Redirect the browser to the auth-server's Google authorize endpoint."""
    if intent not in ("signup", "login"):
        intent = "signup"
    return RedirectResponse(
        url=f"{_auth_public_url()}/platform/google/authorize?intent={intent}",
        status_code=302,
    )


async def _resolve_handoff(token: str) -> dict | None:
    """Ask auth-server what a handoff token means. Returns dict or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_auth_server_url()}/platform/handoff/resolve",
                json={"service_secret": _service_secret(), "token": token},
            )
        if resp.status_code == 200:
            return resp.json()
        logger.warning("handoff_resolve_failed", extra={"status": resp.status_code})
    except httpx.HTTPError as e:
        logger.warning("handoff_resolve_error", extra={"err": str(e)})
    return None


@router.get("/google-handoff")
async def google_handoff(token: str, request: Request):
    """Auth-server redirects here with a handoff token after Google OAuth completes.

    For login: resolves token, sets session, redirects to /connect (or dashboard).
    For signup: redirects to /signup/confirm with the token (the confirm page fetches Google info).
    """
    data = await _resolve_handoff(token)
    if not data:
        return RedirectResponse(url="/signup?error=handoff_invalid", status_code=302)

    if data.get("type") == "login":
        request.session["username"] = data["username"]
        return RedirectResponse(url="/connect", status_code=302)

    if data.get("type") == "signup":
        # Pass token through to confirm page. Token remains valid on auth-server until TTL.
        return RedirectResponse(url=f"/signup/confirm?token={token}", status_code=302)

    return RedirectResponse(url="/signup?error=handoff_unknown", status_code=302)


@router.get("/google-pending")
async def google_pending(token: str):
    """Signup-confirm page calls this to get Google info + suggested username."""
    data = await _resolve_handoff(token)
    if not data or data.get("type") != "signup":
        return JSONResponse({"detail": "Invalid or expired token"}, status_code=410)
    return {
        "google_email": data.get("google_email"),
        "google_name": data.get("google_name"),
        "suggested_username": data.get("suggested_username"),
    }


class GoogleSignupCompleteRequest(BaseModel):
    token: str
    username: str


@router.post("/google-signup-complete")
async def google_signup_complete(body: GoogleSignupCompleteRequest, request: Request):
    """User confirmed (possibly edited) username on signup/confirm — create the user."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_auth_server_url()}/platform/signup/complete",
                json={
                    "service_secret": _service_secret(),
                    "token": body.token,
                    "username": body.username,
                },
            )
    except httpx.HTTPError as e:
        logger.warning("google_signup_complete_error", extra={"err": str(e)})
        return JSONResponse({"detail": "Auth server unavailable"}, status_code=502)

    if resp.status_code == 200:
        data = resp.json()
        request.session["username"] = data["username"]
        return {"username": data["username"]}

    # Map auth-server errors to user-facing messages
    err = (resp.json() or {}).get("error", "unknown")
    if err == "username_taken":
        return JSONResponse(
            {"detail": "This username is already taken.", "field": "username", "code": "taken"},
            status_code=409,
        )
    if err == "invalid_username":
        return JSONResponse(
            {
                "detail": "Username must be 3-32 chars: letters, numbers, underscore, dash.",
                "field": "username",
                "code": "invalid_format",
            },
            status_code=400,
        )
    if err in ("expired", "not_found"):
        return JSONResponse(
            {"detail": "Signup session expired — please try again.", "code": "expired"},
            status_code=410,
        )
    return JSONResponse({"detail": "Signup failed.", "code": err}, status_code=resp.status_code)


@router.get("/me/connection-status")
async def connection_status(request: Request):
    """Poll this to find out if the user has ever used the MCP server."""
    username = request.session.get("username")
    if not username:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{_auth_server_url()}/platform/user/connection-status",
                json={"service_secret": _service_secret(), "username": username},
            )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "connected": data.get("first_connected_at") is not None,
                "first_connected_at": data.get("first_connected_at"),
                "last_active_at": data.get("last_active_at"),
            }
        if resp.status_code == 404:
            return {"connected": False, "first_connected_at": None, "last_active_at": None}
    except httpx.HTTPError:
        pass
    return JSONResponse({"detail": "Auth server unavailable"}, status_code=502)


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
