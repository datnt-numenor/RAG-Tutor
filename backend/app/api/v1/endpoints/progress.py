from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.progress_service import get_progress_service
from starlette.concurrency import run_in_threadpool

router = APIRouter()


@router.get("/progress/overview")
async def progress_overview(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()

    memberships = (
        db.table("project_members")
        .select("project_id, projects(id, name, status)")
        .eq("user_id", current_user.user_id)
        .execute()
    )
    project_ids = [row["project_id"] for row in memberships.data]

    if not project_ids:
        return {
            "projects": 0,
            "documents": 0,
            "ready_documents": 0,
            "chat_sessions": 0,
            "chat_messages": 0,
            "quiz_sessions": 0,
            "quiz_attempts": 0,
            "quiz_correct": 0,
            "avg_quiz_score": 0,
            "reviews_due": 0,
            "project_breakdown": [],
        }

    documents = (
        db.table("documents")
        .select("id, project_id, active_version_id")
        .in_("project_id", project_ids)
        .neq("status", "deleting")
        .execute()
    )

    sessions = (
        db.table("chat_sessions")
        .select("id, project_id")
        .in_("project_id", project_ids)
        .eq("user_id", current_user.user_id)
        .execute()
    )
    session_ids = [row["id"] for row in sessions.data]

    messages = []
    if session_ids:
        messages = (
            db.table("chat_messages")
            .select("id, session_id, role")
            .in_("session_id", session_ids)
            .execute()
        ).data

    quiz_sessions = (
        db.table("quiz_sessions")
        .select("id, project_id, status, total_score, max_score")
        .in_("project_id", project_ids)
        .eq("user_id", current_user.user_id)
        .execute()
    )

    attempts = (
        db.table("quiz_attempts")
        .select("id, project_id, score, max_score_snapshot, is_correct")
        .in_("project_id", project_ids)
        .eq("user_id", current_user.user_id)
        .eq("status", "graded")
        .execute()
    )

    reviews = (
        db.table("review_states")
        .select("id, project_id, due_at")
        .in_("project_id", project_ids)
        .eq("user_id", current_user.user_id)
        .lte("due_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )

    ratios: list[float] = []
    for attempt in attempts.data:
        max_score = float(attempt.get("max_score_snapshot") or 0)
        if max_score > 0:
            ratios.append(float(attempt.get("score") or 0) / max_score)

    project_breakdown: list[dict] = []
    for membership in memberships.data:
        project = membership.get("projects") or {}
        project_id = membership["project_id"]
        project_documents = [
            item for item in documents.data if item["project_id"] == project_id
        ]
        project_quizzes = [
            item for item in quiz_sessions.data if item["project_id"] == project_id
        ]
        project_attempts = [
            item for item in attempts.data if item["project_id"] == project_id
        ]
        project_chat_sessions = [
            item for item in sessions.data if item["project_id"] == project_id
        ]
        project_breakdown.append({
            "project_id": project_id,
            "name": project.get("name", "Project"),
            "documents": len(project_documents),
            "ready_documents": sum(
                1 for item in project_documents if item.get("active_version_id")
            ),
            "chat_sessions": len(project_chat_sessions),
            "quiz_sessions": len(project_quizzes),
            "quiz_attempts": len(project_attempts),
            "quiz_correct": sum(
                1 for item in project_attempts if item.get("is_correct") is True
            ),
        })

    return {
        "projects": len(project_ids),
        "documents": len(documents.data),
        "ready_documents": sum(
            1 for item in documents.data if item.get("active_version_id")
        ),
        "chat_sessions": len(sessions.data),
        "chat_messages": len(messages),
        "quiz_sessions": len(quiz_sessions.data),
        "quiz_attempts": len(attempts.data),
        "quiz_correct": sum(
            1 for item in attempts.data if item.get("is_correct") is True
        ),
        "avg_quiz_score": round(
            (sum(ratios) / len(ratios) * 100) if ratios else 0,
            1,
        ),
        "reviews_due": len(reviews.data),
        "project_breakdown": project_breakdown,
    }



@router.get("/progress/history")
async def progress_history(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365),
    project_id: str | None = None,
) -> list[dict]:
    db = get_supabase_admin()
    start_date = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()

    query = (
        db.table("progress_snapshots")
        .select("*, projects(name)")
        .eq("user_id", current_user.user_id)
        .gte("snapshot_date", start_date.isoformat())
        .order("snapshot_date")
    )

    if project_id:
        member = (
            db.table("project_members")
            .select("id")
            .eq("project_id", project_id)
            .eq("user_id", current_user.user_id)
            .maybe_single()
            .execute()
        )
        if not member.data:
            raise HTTPException(status_code=404, detail="Project not found")
        query = query.eq("project_id", project_id)

    return query.execute().data


@router.post("/projects/{project_id}/progress/rebuild")
async def rebuild_progress(
    project_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365),
) -> dict:
    db = get_supabase_admin()
    member = (
        db.table("project_members")
        .select("id")
        .eq("project_id", project_id)
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Project not found")

    service = get_progress_service()
    tz = service._user_timezone(current_user.user_id)
    end_date = datetime.now(tz).date()
    start_date = end_date - timedelta(days=days - 1)

    rows = await run_in_threadpool(
        service.rebuild_range,
        user_id=current_user.user_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "project_id": project_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "snapshots_rebuilt": len(rows),
    }
