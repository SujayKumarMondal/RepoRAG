from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, get_current_user_id
from app.models.user import User
from app.services.github.client import GitHubClient


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# GitHub Login
# ============================================================

@router.get("/github/login")
async def github_login(request: Request):
    """
    Redirect the user to GitHub OAuth authorization.
    """

    github_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        "&scope=read:user,user:email,repo"
    )

    # When called from the Swagger UI (which sends `accept: application/json`)
    # the browser `fetch` used by the docs will fail to follow cross-origin
    # redirects due to CORS. In that case, return the authorization URL as
    # JSON so the client can open it in a new window.
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return {"authorize_url": github_url}

    return RedirectResponse(
        url=github_url,
        status_code=status.HTTP_302_FOUND,
    )


# ============================================================
# GitHub OAuth Callback
# ============================================================

@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
):
    """
    GitHub OAuth callback.

    GitHub sends an authorization code here.
    """

    if error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "GitHub OAuth error",
                "detail": error,
            },
        )

    if not code:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "GitHub authorization code is missing.",
            },
        )

    try:
        github_client = GitHubClient()

        # Exchange OAuth code for GitHub access token
        access_token = await github_client.exchange_code_for_token(
            code
        )

        # Fetch authenticated GitHub user
        github_user = await github_client.get_authenticated_user(
            access_token
        )

        if not github_user.get("email"):
            github_emails = await github_client.get_user_emails(
                access_token
            )
            usable_emails = [
                email
                for email in github_emails
                if email.get("email") and email.get("verified")
            ]
            primary_email = next(
                (
                    email["email"]
                    for email in usable_emails
                    if email.get("primary")
                ),
                None,
            )
            github_user["email"] = primary_email or (
                usable_emails[0]["email"] if usable_emails else None
            )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    User.github_id == str(github_user.get("id"))
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    github_id=str(github_user.get("id")),
                    github_username=github_user.get("login"),
                    github_email=github_user.get("email"),
                    avatar_url=github_user.get("avatar_url"),
                    github_profile_url=github_user.get("html_url"),
                    github_access_token=access_token,
                )
                db.add(user)
            else:
                user.github_username = github_user.get("login")
                user.github_email = github_user.get("email")
                user.avatar_url = github_user.get("avatar_url")
                user.github_profile_url = github_user.get("html_url")
                user.github_access_token = access_token
                user.is_active = True

            await db.commit()
            await db.refresh(user)

        application_token = create_access_token(
            data={
                "sub": str(user.id),
                "github_id": str(user.github_id),
                "github_login": user.github_username,
            }
        )

        return {
            "message": "GitHub authentication successful",
            "access_token": application_token,
            "token_type": "bearer",
            "github_user": {
                **github_user,
                "repo_rag_user_id": str(user.id),
            },
        }

    except Exception as exc:
        reauth_url = "/api/v1/auth/github"
        error_payload = {
            "error": "GitHub authentication failed",
            "detail": str(exc),
            "reauth_url": reauth_url,
        }

        accept = request.headers.get("accept", "")

        # Keep the browser from looping forever by returning a real error
        # response instead of redirecting back into /github.
        if "text/html" in accept or "*/*" in accept:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_payload,
            )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_payload,
        )


# ============================================================
# Current User
# ============================================================

@router.get("/me")
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
):
    """
    Return authenticated user information.
    """

    return {
        "authenticated": True,
        "user_id": user_id,
    }


# ============================================================
# Logout
# ============================================================

@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    JWTs are stateless, so the frontend should remove the
    stored access token.

    Token blacklist/revocation can be implemented later
    using Redis.
    """

    return {
        "message": "Logged out successfully",
    }