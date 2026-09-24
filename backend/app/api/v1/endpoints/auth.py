from __future__ import annotations

from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin, get_supabase_anon

router = APIRouter()


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    requires_email_confirmation: bool = False


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=80)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("full_name cannot be blank")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown IANA timezone") from exc
        return value


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(body: SignUpRequest) -> TokenResponse:
    """Register a new user via Supabase Auth."""
    client = get_supabase_anon()
    try:
        sign_up_payload = {
            "email": body.email,
            "password": body.password,
            "options": {
                "data": {
                    "full_name": body.full_name,
                }
            },
        }
        res = client.auth.sign_up(sign_up_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if res.user is None:
        raise HTTPException(status_code=400, detail="Sign-up failed")

    if res.session is None:
        return TokenResponse(
            access_token=None,
            requires_email_confirmation=True,
        )

    return TokenResponse(access_token=res.session.access_token)


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


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def sign_out(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    """End the local API session response without a response body."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
async def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    profile = (
        db.table("users")
        .select("id, email, full_name, avatar_url, timezone, created_at, updated_at")
        .eq("id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not profile.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    return {
        "user_id": profile.data["id"],
        "email": profile.data.get("email") or current_user.email,
        "full_name": profile.data.get("full_name"),
        "avatar_url": profile.data.get("avatar_url"),
        "timezone": profile.data.get("timezone") or "UTC",
        "created_at": profile.data.get("created_at"),
        "updated_at": profile.data.get("updated_at"),
    }


@router.patch("/me")
async def update_me(
    body: ProfileUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        return await get_me(current_user)

    db = get_supabase_admin()
    result = (
        db.table("users")
        .update(payload)
        .eq("id", current_user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User profile not found")

    return await get_me(current_user)
