"""
RepoRAG authentication and security utilities.

Handles:
- HTTP Bearer authentication
- JWT creation
- JWT decoding and validation
- Current authenticated user dependency
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import settings


# ============================================================
# JWT Configuration
# ============================================================

JWT_ALGORITHM = settings.ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = (
    settings.ACCESS_TOKEN_EXPIRE_MINUTES
)


# ============================================================
# HTTP Bearer Authentication
# ============================================================

bearer_scheme = HTTPBearer(
    auto_error=False
)


# ============================================================
# JWT Creation
# ============================================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Parameters
    ----------
    data:
        Payload that will be stored inside the JWT.

    expires_delta:
        Optional custom expiration duration.

    Returns
    -------
    str
        Encoded JWT token.
    """

    to_encode = data.copy()

    # --------------------------------------------------------
    # Calculate expiration time
    # --------------------------------------------------------

    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # --------------------------------------------------------
    # Add standard JWT claims
    # --------------------------------------------------------

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
    )

    # --------------------------------------------------------
    # Encode JWT
    # --------------------------------------------------------

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return encoded_jwt


# ============================================================
# Decode Access Token
# ============================================================

def decode_access_token(
    token: str,
) -> dict[str, Any] | None:
    """
    Decode and validate a JWT access token.

    Returns
    -------
    dict | None
        JWT payload if valid.
        None if invalid or expired.
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        return payload

    except ExpiredSignatureError:
        return None

    except InvalidTokenError:
        return None


# ============================================================
# Get Subject From Token
# ============================================================

def get_subject_from_token(
    token: str,
) -> str:
    """
    Extract the 'sub' claim from a JWT.

    The 'sub' claim represents the authenticated
    RepoRAG user's identifier.
    """

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    subject = payload.get("sub")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return str(subject)


# ============================================================
# Current User Dependency
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict[str, Any]:
    """
    Extract and validate the authenticated JWT payload.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return payload


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> str:
    """
    Extract and validate the authenticated user's ID
    from the Authorization header.

    Expected header:

        Authorization: Bearer <JWT>

    Example:

        @router.get("/me")
        async def me(
            user_id: str = Depends(get_current_user_id)
        ):
            return {"user_id": user_id}
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    token = credentials.credentials
    return get_subject_from_token(token)


# ============================================================
# Security Configuration Validation
# ============================================================

def validate_security_configuration() -> None:
    """
    Validate required security configuration.

    This should be called during application startup.
    """

    # --------------------------------------------------------
    # JWT secret
    # --------------------------------------------------------

    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not configured. "
            "Generate a strong random secret and add it to .env"
        )

    # --------------------------------------------------------
    # Secret length
    # --------------------------------------------------------

    if len(settings.SECRET_KEY) < 32:
        raise RuntimeError(
            "SECRET_KEY must contain at least "
            "32 characters."
        )

    # --------------------------------------------------------
    # Algorithm
    # --------------------------------------------------------

    if not settings.JWT_ALGORITHM:
        raise RuntimeError(
            "JWT_ALGORITHM is not configured."
        )

    # --------------------------------------------------------
    # Expiration
    # --------------------------------------------------------

    if (
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 0
    ):
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be "
            "greater than 0."
        )