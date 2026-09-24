from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.config import get_settings

router = APIRouter()

INVITATION_TTL_DAYS = 7


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _parse_expiry(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class InviteRequest(BaseModel):
    email: EmailStr


@router.post("/projects/{project_id}/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    project_id: UUID,
    body: InviteRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    # Must be owner
    owner = (
        db.table("project_members")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .eq("role", "owner")
        .maybe_single()
        .execute()
    )
    if not owner.data:
        raise HTTPException(status_code=403, detail="Only the owner can send invitations")

    existing_user = (
        db.table("users")
        .select("id")
        .eq("email", body.email.lower())
        .maybe_single()
        .execute()
    )
    if existing_user.data:
        existing_member = (
            db.table("project_members")
            .select("id")
            .eq("project_id", str(project_id))
            .eq("user_id", existing_user.data["id"])
            .maybe_single()
            .execute()
        )
        if existing_member.data:
            raise HTTPException(
                status_code=409,
                detail="This user is already a project member",
            )

    pending = (
        db.table("project_invitations")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("invited_email", body.email.lower())
        .eq("status", "pending")
        .maybe_single()
        .execute()
    )
    if pending.data:
        raise HTTPException(
            status_code=409,
            detail="A pending invitation already exists for this email",
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    res = db.table("project_invitations").insert({
        "project_id": str(project_id),
        "invited_by": current_user.user_id,
        "invited_email": body.email.lower(),
        "token_hash": token_hash,
        "status": "pending",
    }).execute()

    invitation = res.data[0]
    # Return raw token only at creation time — never stored
    return {
        "invitation_id": invitation["id"],
        "invite_link": f"/invite/{raw_token}",
        "expires_at": invitation["expires_at"],
    }


@router.get("/projects/{project_id}/invitations")
async def list_invitations(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    owner = (
        db.table("project_members").select("id")
        .eq("project_id", str(project_id)).eq("user_id", current_user.user_id)
        .eq("role", "owner").maybe_single().execute()
    )
    if not owner.data:
        raise HTTPException(status_code=403, detail="Forbidden")

    res = (
        db.table("project_invitations")
        .select("id, invited_email, status, expires_at, created_at")
        .eq("project_id", str(project_id))
        .execute()
    )
    return res.data


@router.delete("/projects/{project_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def revoke_invitation(
    project_id: UUID,
    invitation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    db = get_supabase_admin()
    owner = (
        db.table("project_members").select("id")
        .eq("project_id", str(project_id)).eq("user_id", current_user.user_id)
        .eq("role", "owner").maybe_single().execute()
    )
    if not owner.data:
        raise HTTPException(status_code=403, detail="Forbidden")

    db.table("project_invitations").update({"status": "revoked"}).eq(
        "id", str(invitation_id)
    ).eq("project_id", str(project_id)).execute()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/invitations/{raw_token}")
async def preview_invitation(raw_token: str) -> dict:
    """Return safe preview info (project name, inviter) without revealing token hash."""
    db = get_supabase_admin()
    token_hash = _hash_token(raw_token)
    res = (
        db.table("project_invitations")
        .select("id, status, expires_at, invited_email, projects(name), users!invited_by(full_name)")
        .eq("token_hash", token_hash)
        .maybe_single()
        .execute()
    )
    if not res.data or res.data["status"] != "pending":
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    if _parse_expiry(res.data["expires_at"]) <= datetime.now(timezone.utc):
        db.table("project_invitations").update({
            "status": "expired",
        }).eq("id", res.data["id"]).eq("status", "pending").execute()
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    return {
        "invitation_id": res.data["id"],
        "project_name": res.data["projects"]["name"],
        "invited_by": res.data["users"]["full_name"],
        "expires_at": res.data["expires_at"],
    }


@router.post("/invitations/{raw_token}/accept", status_code=201)
async def accept_invitation(
    raw_token: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    settings = get_settings()

    if settings.is_production:
        try:
            auth_user = db.auth.admin.get_user_by_id(current_user.user_id)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Could not verify account email status",
            ) from exc

        user_record = getattr(auth_user, "user", None)
        if not user_record or not getattr(user_record, "email_confirmed_at", None):
            raise HTTPException(
                status_code=403,
                detail="Verified email is required to accept an invitation",
            )

    res = db.rpc("accept_project_invitation", {
        "p_raw_token": raw_token,
        "p_user_id": current_user.user_id,
        "p_email": current_user.email,
    }).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Could not accept invitation")
    return {"message": "Joined project successfully"}


@router.post("/invitations/{raw_token}/reject", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def reject_invitation(
    raw_token: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    db = get_supabase_admin()
    token_hash = _hash_token(raw_token)
    invitation = (
        db.table("project_invitations")
        .select("id, invited_email, status, expires_at")
        .eq("token_hash", token_hash)
        .maybe_single()
        .execute()
    )
    if not invitation.data or invitation.data["status"] != "pending":
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    if _parse_expiry(invitation.data["expires_at"]) <= datetime.now(timezone.utc):
        db.table("project_invitations").update({
            "status": "expired",
        }).eq("id", invitation.data["id"]).eq("status", "pending").execute()
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    if invitation.data["invited_email"].casefold() != current_user.email.casefold():
        raise HTTPException(
            status_code=403,
            detail="This invitation belongs to a different email",
        )

    db.table("project_invitations").update({"status": "rejected"}).eq(
        "id", invitation.data["id"]
    ).eq("status", "pending").execute()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
