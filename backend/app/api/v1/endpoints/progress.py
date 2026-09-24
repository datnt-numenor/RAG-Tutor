from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

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
        .lte("due_at", "now()")
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
