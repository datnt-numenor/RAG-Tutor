from __future__ import annotations

import hashlib
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()

INVITATION_TTL_DAYS = 7


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


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


@router.delete("/projects/{project_id}/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(
    project_id: UUID,
    invitation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
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


@router.get("/{raw_token}")
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
    return {
        "invitation_id": res.data["id"],
        "project_name": res.data["projects"]["name"],
        "invited_by": res.data["users"]["full_name"],
        "expires_at": res.data["expires_at"],
    }


@router.post("/{raw_token}/accept", status_code=201)
async def accept_invitation(
    raw_token: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    res = db.rpc("accept_project_invitation", {
        "p_raw_token": raw_token,
        "p_user_id": current_user.user_id,
        "p_email": current_user.email,
    }).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Could not accept invitation")
    return {"message": "Joined project successfully"}


@router.post("/{raw_token}/reject", status_code=204)
async def reject_invitation(raw_token: str) -> None:
    db = get_supabase_admin()
    token_hash = _hash_token(raw_token)
    db.table("project_invitations").update({"status": "rejected"}).eq(
        "token_hash", token_hash
    ).eq("status", "pending").execute()
