from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.topic_roadmap_service import get_topic_roadmap_service
from app.core.rate_limit import enforce_ai_rate_limit
from app.workers.celery_app import celery_app

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
    await run_in_threadpool(
        _assert_member,
        db,
        str(project_id),
        current_user.user_id,
    )

    service = get_topic_roadmap_service()
    return await run_in_threadpool(service.get_roadmap, str(project_id))


@router.post(
    "/projects/{project_id}/roadmap/generate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_roadmap(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    await run_in_threadpool(
        _assert_owner,
        db,
        str(project_id),
        current_user.user_id,
    )
    await enforce_ai_rate_limit(
        current_user.user_id,
        bucket="roadmap-generate",
        limit=5,
        window_seconds=300,
    )

    try:
        from app.workers.roadmap_worker import generate_topic_roadmap

        task = await run_in_threadpool(
            generate_topic_roadmap.delay, str(project_id)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Roadmap generation could not be queued",
        ) from exc

    return {
        "project_id": str(project_id),
        "job_id": task.id,
        "status": "queued",
    }


@router.get("/projects/{project_id}/roadmap/jobs/{job_id}")
async def get_roadmap_job(
    project_id: UUID,
    job_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    await run_in_threadpool(
        _assert_member, db, str(project_id), current_user.user_id
    )

    task = celery_app.AsyncResult(job_id)
    state = await run_in_threadpool(lambda: task.state)
    response = {
        "job_id": job_id,
        "project_id": str(project_id),
        "status": state.lower(),
    }
    if state == "SUCCESS":
        result = await run_in_threadpool(lambda: task.result)
        if not isinstance(result, dict) or result.get("project_id") != str(project_id):
            raise HTTPException(status_code=404, detail="Roadmap job not found")
        response["topic_count"] = int(result.get("topic_count") or 0)
    elif state == "FAILURE":
        response["error"] = "Roadmap generation failed"
    return response
