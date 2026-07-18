from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    target_score: float | None = Field(None, ge=0, le=100)
    exam_date: str | None = None          # ISO date string
    weekly_study_minutes: int | None = Field(None, gt=0)


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    owner_id: str
    target_score: float | None
    exam_date: str | None
    weekly_study_minutes: int | None
    status: str
    created_at: str
    updated_at: str


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[ProjectResponse]:
    """List all projects the current user is a member of."""
    db = get_supabase_admin()
    res = (
        db.table("project_members")
        .select("project_id, projects(*)")
        .eq("user_id", current_user.user_id)
        .execute()
    )
    return [row["projects"] for row in res.data]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProjectResponse:
    """Create a new project and automatically add the creator as owner."""
    db = get_supabase_admin()
    # Use DB function that creates project + owner membership atomically
    res = db.rpc(
        "create_project_with_owner",
        {
            "p_owner_id": current_user.user_id,
            "p_name": body.name,
            "p_description": body.description,
            "p_target_score": body.target_score,
            "p_exam_date": body.exam_date,
            "p_weekly_study_minutes": body.weekly_study_minutes,
        },
    ).execute()

    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create project")

    return res.data


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProjectResponse:
    db = get_supabase_admin()
    # Verify membership
    member = (
        db.table("project_members")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Project not found")

    res = db.table("projects").select("*").eq("id", str(project_id)).single().execute()
    return res.data


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProjectResponse:
    """Update project — only the owner may do this."""
    db = get_supabase_admin()
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
        raise HTTPException(status_code=403, detail="Only the project owner can update it")

    update_data = body.model_dump(exclude_none=True)
    res = (
        db.table("projects")
        .update(update_data)
        .eq("id", str(project_id))
        .execute()
    )
    return res.data[0]


@router.get("/{project_id}/members")
async def list_members(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    member_check = (
        db.table("project_members")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not member_check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    res = (
        db.table("project_members")
        .select("*, users(id, full_name, email, avatar_url)")
        .eq("project_id", str(project_id))
        .execute()
    )
    return res.data


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
    """Remove a member from the project. Owner cannot be removed."""
    db = get_supabase_admin()
    owner_check = (
        db.table("project_members")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .eq("role", "owner")
        .maybe_single()
        .execute()
    )
    if not owner_check.data:
        raise HTTPException(status_code=403, detail="Only the owner can remove members")

    # Prevent removing owner
    target = (
        db.table("project_members")
        .select("role")
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .single()
        .execute()
    )
    if target.data and target.data["role"] == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the project owner")

    db.table("project_members").delete().eq("project_id", str(project_id)).eq(
        "user_id", str(user_id)
    ).execute()
