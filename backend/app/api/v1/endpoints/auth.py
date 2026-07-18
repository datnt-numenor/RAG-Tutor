from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_anon

router = APIRouter()


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(body: SignUpRequest) -> TokenResponse:
    """Register a new user via Supabase Auth."""
    client = get_supabase_anon()
    try:
        res = client.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if res.user is None:
        raise HTTPException(status_code=400, detail="Sign-up failed")

    return TokenResponse(access_token=res.session.access_token)  # type: ignore[union-attr]


@router.post("/signin", response_model=TokenResponse)
async def sign_in(body: SignInRequest) -> TokenResponse:
    """Authenticate and return a Supabase access token."""
    client = get_supabase_anon()
    try:
        res = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    return TokenResponse(access_token=res.session.access_token)  # type: ignore[union-attr]


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
    """Invalidate the current session."""
    client = get_supabase_anon()
    client.auth.sign_out()


@router.get("/me")
async def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    return {"user_id": current_user.user_id, "email": current_user.email}
