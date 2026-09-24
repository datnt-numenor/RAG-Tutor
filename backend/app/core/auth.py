from __future__ import annotations

from typing import Annotated

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.jwk import construct

from app.core.config import get_settings

logger = structlog.get_logger()
bearer = HTTPBearer(auto_error=False)

_JWKS_CACHE: dict | None = None


class AuthenticatedUser:
    def __init__(self, user_id: str, email: str, raw_token: str) -> None:
        self.user_id = user_id
        self.email = email
        self.raw_token = raw_token


async def _fetch_jwks(force_refresh: bool = False) -> dict:
    global _JWKS_CACHE

    if _JWKS_CACHE is not None and not force_refresh:
        return _JWKS_CACHE

    settings = get_settings()
    jwks_url = (
        f"{settings.supabase_url.rstrip('/')}"
        "/auth/v1/.well-known/jwks.json"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _JWKS_CACHE = response.json()

    return _JWKS_CACHE


async def _get_signing_key(token: str):
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    kid = header.get("kid")
    alg = header.get("alg")

    if alg not in {"ES256", "RS256"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported token signing algorithm",
        )

    for force_refresh in (False, True):
        jwks = await _fetch_jwks(force_refresh=force_refresh)

        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                return construct(key_data, algorithm=alg), alg

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Signing key not found",
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer),
    ],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = credentials.credentials
    settings = get_settings()

    try:
        signing_key, algorithm = await _get_signing_key(token)

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
            audience="authenticated",
        )
    except HTTPException:
        raise
    except (JWTError, httpx.HTTPError, ValueError) as exc:
        logger.warning("JWT verification failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id: str | None = payload.get("sub")
    email: str | None = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    return AuthenticatedUser(
        user_id=user_id,
        email=email or "",
        raw_token=token,
    )
