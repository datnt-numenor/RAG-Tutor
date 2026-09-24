from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.topic_roadmap_service import get_topic_roadmap_service
from app.services.progress_service import get_progress_service

router = APIRouter()


def _membership(db, project_id: str, user_id: str) -> dict:
    member = (
        db.table("project_members")
        .select("id, role")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return member.data


@router.get("/projects/{project_id}/schedules")
async def list_schedules(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    _membership(db, str(project_id), current_user.user_id)

    schedules = (
        db.table("schedules")
        .select("*, topics(id, name)")
        .eq("project_id", str(project_id))
        .order("start_time")
        .execute()
    ).data

    schedule_ids = [item["id"] for item in schedules]
    completion_ids: set[str] = set()
    if schedule_ids:
        completions = (
            db.table("schedule_completions")
            .select("schedule_id")
            .eq("user_id", current_user.user_id)
            .in_("schedule_id", schedule_ids)
            .execute()
        ).data
        completion_ids = {item["schedule_id"] for item in completions}

    for item in schedules:
        item["completed_by_me"] = item["id"] in completion_ids

    return schedules


@router.post(
    "/projects/{project_id}/schedules/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_schedules(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    member = _membership(db, str(project_id), current_user.user_id)
    if member["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can generate schedule")

    service = get_topic_roadmap_service()
    try:
        return await run_in_threadpool(
            service.generate_schedule,
            str(project_id),
            current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/schedules/{schedule_id}/accept")
async def accept_schedule(
    schedule_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    schedule = (
        db.table("schedules")
        .select("id, project_id, suggestion_status")
        .eq("id", str(schedule_id))
        .maybe_single()
        .execute()
    )
    if not schedule.data:
        raise HTTPException(status_code=404, detail="Schedule not found")

    member = _membership(db, schedule.data["project_id"], current_user.user_id)
    if member["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can accept shared schedule")

    result = (
        db.table("schedules")
        .update({"suggestion_status": "accepted"})
        .eq("id", str(schedule_id))
        .execute()
    )
    return result.data[0]


@router.post("/schedules/{schedule_id}/reject")
async def reject_schedule(
    schedule_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    schedule = (
        db.table("schedules")
        .select("id, project_id")
        .eq("id", str(schedule_id))
        .maybe_single()
        .execute()
    )
    if not schedule.data:
        raise HTTPException(status_code=404, detail="Schedule not found")

    member = _membership(db, schedule.data["project_id"], current_user.user_id)
    if member["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can reject shared schedule")

    result = (
        db.table("schedules")
        .update({"suggestion_status": "rejected"})
        .eq("id", str(schedule_id))
        .execute()
    )
    return result.data[0]


@router.post("/schedules/{schedule_id}/complete", status_code=status.HTTP_201_CREATED)
async def complete_schedule(
    schedule_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    schedule = (
        db.table("schedules")
        .select("id, project_id, topic_id, start_time, end_time")
        .eq("id", str(schedule_id))
        .maybe_single()
        .execute()
    )
    if not schedule.data:
        raise HTTPException(status_code=404, detail="Schedule not found")

    _membership(db, schedule.data["project_id"], current_user.user_id)

    completed_at = datetime.now(timezone.utc)
    result = (
        db.table("schedule_completions")
        .upsert({
            "schedule_id": str(schedule_id),
            "user_id": current_user.user_id,
            "completed_at": completed_at.isoformat(),
        }, on_conflict="schedule_id,user_id")
        .execute()
    )

    duration_seconds = None
    if schedule.data.get("end_time"):
        start_value = datetime.fromisoformat(
            schedule.data["start_time"].replace("Z", "+00:00")
        )
        end_value = datetime.fromisoformat(
            schedule.data["end_time"].replace("Z", "+00:00")
        )
        duration_seconds = max(
            0,
            int((end_value - start_value).total_seconds()),
        )

    await run_in_threadpool(
        get_progress_service().record_event,
        user_id=current_user.user_id,
        project_id=schedule.data["project_id"],
        topic_id=schedule.data.get("topic_id"),
        event_type="schedule_completed",
        source_id=str(schedule_id),
        duration_seconds=duration_seconds,
        idempotency_key=(
            f"schedule_completion:{schedule_id}:{current_user.user_id}"
        ),
    )

    return result.data[0]


@router.delete(
    "/schedules/{schedule_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def uncomplete_schedule(
    schedule_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    db = get_supabase_admin()
    schedule = (
        db.table("schedules")
        .select("id, project_id")
        .eq("id", str(schedule_id))
        .maybe_single()
        .execute()
    )
    if not schedule.data:
        raise HTTPException(status_code=404, detail="Schedule not found")

    _membership(db, schedule.data["project_id"], current_user.user_id)

    db.table("schedule_completions").delete().eq(
        "schedule_id", str(schedule_id)
    ).eq(
        "user_id", current_user.user_id
    ).execute()

    await run_in_threadpool(
        get_progress_service().remove_event,
        user_id=current_user.user_id,
        idempotency_key=(
            f"schedule_completion:{schedule_id}:{current_user.user_id}"
        ),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
