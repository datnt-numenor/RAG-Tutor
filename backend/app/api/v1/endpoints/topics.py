from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.topic_roadmap_service import get_topic_roadmap_service

router = APIRouter()


def _assert_member(db, project_id: str, user_id: str) -> None:
    member = (
        db.table("project_members")
        .select("id")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Project not found")


def _assert_owner(db, project_id: str, user_id: str) -> None:
    owner = (
        db.table("project_members")
        .select("id")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .eq("role", "owner")
        .maybe_single()
        .execute()
    )
    if not owner.data:
        raise HTTPException(status_code=403, detail="Only the project owner can generate roadmap")


@router.get("/projects/{project_id}/roadmap")
async def get_roadmap(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    service = get_topic_roadmap_service()
    return await run_in_threadpool(service.get_roadmap, str(project_id))


@router.post(
    "/projects/{project_id}/roadmap/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_roadmap(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_owner(db, str(project_id), current_user.user_id)

    service = get_topic_roadmap_service()
    try:
        topics = await run_in_threadpool(service.generate_topics, str(project_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Roadmap generation failed") from exc

    return {
        "project_id": str(project_id),
        "topics": topics,
    }
