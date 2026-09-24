from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.quiz_service import get_quiz_service

router = APIRouter()


class GenerateQuizRequest(BaseModel):
    count: int = Field(5, ge=1, le=20)
    question_type: str = Field("mcq", pattern="^(mcq|essay)$")


class AnswerRequest(BaseModel):
    answer: str


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


@router.post(
    "/projects/{project_id}/quiz/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_quiz(
    project_id: UUID,
    body: GenerateQuizRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    service = get_quiz_service()
    try:
        questions = await run_in_threadpool(
            service.generate_questions,
            str(project_id),
            body.count,
            body.question_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Quiz generation failed") from exc

    ids = [q["id"] for q in questions]
    max_score = sum(float(q.get("max_score") or 0) for q in questions)

    session_res = db.table("quiz_sessions").insert({
        "project_id": str(project_id),
        "user_id": current_user.user_id,
        "status": "in_progress",
        "question_ids": ids,
        "max_score": max_score,
    }).execute()

    return {
        "session": session_res.data[0],
        "questions": questions,
    }


@router.get("/projects/{project_id}/quiz/sessions")
async def list_quiz_sessions(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    res = (
        db.table("quiz_sessions")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .order("started_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/projects/{project_id}/quiz/sessions/{session_id}")
async def get_quiz_session(
    project_id: UUID,
    session_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    session = (
        db.table("quiz_sessions")
        .select("*")
        .eq("id", str(session_id))
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    ids = session.data["question_ids"]
    questions = (
        db.table("questions")
        .select("*")
        .in_("id", ids)
        .execute()
    )
    attempts = (
        db.table("quiz_attempts")
        .select("*")
        .eq("quiz_session_id", str(session_id))
        .execute()
    )

    order = {question_id: index for index, question_id in enumerate(ids)}
    sorted_questions = sorted(
        questions.data,
        key=lambda question: order.get(question["id"], 9999),
    )

    return {
        "session": session.data,
        "questions": sorted_questions,
        "attempts": attempts.data,
    }


@router.post(
    "/projects/{project_id}/quiz/sessions/{session_id}/questions/{question_id}/answer"
)
async def answer_question(
    project_id: UUID,
    session_id: UUID,
    question_id: UUID,
    body: AnswerRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    session = (
        db.table("quiz_sessions")
        .select("*")
        .eq("id", str(session_id))
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if session.data["status"] != "in_progress":
        raise HTTPException(status_code=409, detail="Quiz session is not active")
    if str(question_id) not in session.data["question_ids"]:
        raise HTTPException(status_code=404, detail="Question not in this quiz")

    qres = (
        db.table("questions")
        .select("*")
        .eq("id", str(question_id))
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )
    question = qres.data

    now = datetime.now(timezone.utc).isoformat()
    if question["question_type"] == "mcq":
        expected = (question.get("correct_answer") or "").strip()
        is_correct = body.answer.strip() == expected
        score = float(question["max_score"]) if is_correct else 0.0
        feedback = question.get("model_answer") or (
            "Correct." if is_correct else f"Correct answer: {expected}"
        )
        grading_method = "exact-match"
    else:
        service = get_quiz_service()
        graded = await run_in_threadpool(
            service.grade_essay,
            question,
            body.answer,
        )
        score = graded["score"]
        is_correct = graded["is_correct"]
        feedback = graded["feedback"]
        grading_method = graded["grading_method"]

    existing = (
        db.table("quiz_attempts")
        .select("id")
        .eq("quiz_session_id", str(session_id))
        .eq("question_id", str(question_id))
        .maybe_single()
        .execute()
    )

    payload = {
        "quiz_session_id": str(session_id),
        "question_id": str(question_id),
        "user_id": current_user.user_id,
        "project_id": str(project_id),
        "question_text_snapshot": question["question_text"],
        "options_snapshot": question.get("options"),
        "max_score_snapshot": question["max_score"],
        "user_answer": body.answer,
        "score": score,
        "is_correct": is_correct,
        "feedback": feedback,
        "grading_method": grading_method,
        "model_name": question.get("model_name"),
        "prompt_version": question.get("prompt_version"),
        "status": "graded",
        "submitted_at": now,
        "graded_at": now,
    }

    if existing.data:
        attempt = (
            db.table("quiz_attempts")
            .update(payload)
            .eq("id", existing.data["id"])
            .execute()
        ).data[0]
    else:
        attempt = db.table("quiz_attempts").insert(payload).execute().data[0]

    service = get_quiz_service()
    score_ratio = score / float(question["max_score"] or 1)
    await run_in_threadpool(
        service.update_review_state,
        current_user.user_id,
        str(project_id),
        str(question_id),
        score_ratio,
    )

    return attempt


@router.post("/projects/{project_id}/quiz/sessions/{session_id}/submit")
async def submit_quiz(
    project_id: UUID,
    session_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    session = (
        db.table("quiz_sessions")
        .select("*")
        .eq("id", str(session_id))
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    attempts = (
        db.table("quiz_attempts")
        .select("score")
        .eq("quiz_session_id", str(session_id))
        .eq("status", "graded")
        .execute()
    )
    total_score = sum(float(a.get("score") or 0) for a in attempts.data)
    now = datetime.now(timezone.utc).isoformat()

    result = (
        db.table("quiz_sessions")
        .update({
            "status": "graded",
            "total_score": total_score,
            "submitted_at": now,
            "graded_at": now,
        })
        .eq("id", str(session_id))
        .execute()
    )
    return result.data[0]
