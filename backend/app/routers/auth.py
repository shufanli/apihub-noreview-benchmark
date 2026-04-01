"""Auth routes: GitHub OAuth login/callback/logout/me."""
import os
import uuid
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from ..database import get_db
from ..auth import create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "demo_client_id")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "demo_client_secret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.get("/login")
async def login(request: Request):
    redirect_to = request.query_params.get("redirect", "/dashboard")
    state = redirect_to
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&scope=user:email&state={state}"
    )
    return RedirectResponse(url=github_url)


@router.get("/callback")
async def callback(code: str, state: str = "/dashboard"):
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token returned")

        # Get user info
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        gh_user = user_resp.json()

    github_id = gh_user["id"]
    username = gh_user["login"]
    email = gh_user.get("email", "")
    avatar_url = gh_user.get("avatar_url", "")

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE github_id = ?", (github_id,)).fetchone()
        if existing:
            user_id = existing["id"]
            conn.execute(
                "UPDATE users SET username=?, email=?, avatar_url=? WHERE id=?",
                (username, email, avatar_url, user_id),
            )
        else:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO users (id, github_id, username, email, avatar_url) VALUES (?, ?, ?, ?, ?)",
                (user_id, github_id, username, email, avatar_url),
            )

    jwt_token = create_token(user_id, username)
    redirect_url = f"{FRONTEND_URL}{state}"
    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"ok": True})
    response.delete_cookie("session_token", path="/")
    return response


@router.get("/me")
async def me(request: Request):
    user = get_current_user(request)
    user_id = user["sub"]
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, github_id, username, email, avatar_url, plan, stripe_customer_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(row)


# Dev-only: login as test user without GitHub OAuth
@router.get("/dev-login")
async def dev_login(user_id: str = "user_pro_001"):
    with get_db() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
    jwt_token = create_token(row["id"], row["username"])
    response = JSONResponse(content={"ok": True, "user_id": row["id"]})
    response.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return response
