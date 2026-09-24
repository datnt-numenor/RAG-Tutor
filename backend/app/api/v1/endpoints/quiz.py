from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.quiz_service import get_quiz_service
from app.services.ocr_service import get_ocr_service
from app.core.rate_limit import enforce_ai_rate_limit

router = APIRouter()


class GenerateQuizRequest(BaseModel):
    count: int = Field(5, ge=1, le=20)
    question_type: str = Field("mcq", pattern="^(mcq|essay)$")


class AnswerRequest(BaseModel):
    answer: str


class ConfirmScanRequest(BaseModel):
    text: str = Field(..., min_length=1)


class StartQuizRequest(BaseModel):
    count: int = Field(5, ge=1, le=50)
    question_type: str | None = Field(None, pattern="^(mcq|essay)$")


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
        raise HTTPException(
            status_code=403,
            detail="Only the project owner can generate questions",
        )


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
    _assert_owner(db, str(project_id), current_user.user_id)
    await enforce_ai_rate_limit(
        current_user.user_id,
        bucket="quiz-generate",
        limit=8,
        window_seconds=300,
    )

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



@router.post(
    "/projects/{project_id}/quiz/start",
    status_code=status.HTTP_201_CREATED,
)
async def start_quiz_from_bank(
    project_id: UUID,
    body: StartQuizRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    query = (
        db.table("questions")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(body.count)
    )
    if body.question_type:
        query = query.eq("question_type", body.question_type)

    questions = query.execute().data
    if not questions:
        raise HTTPException(
            status_code=400,
            detail="Question bank is empty. Ask the owner to generate questions first.",
        )

    ids = [question["id"] for question in questions]
    max_score = sum(float(question.get("max_score") or 0) for question in questions)

    session = db.table("quiz_sessions").insert({
        "project_id": str(project_id),
        "user_id": current_user.user_id,
        "status": "in_progress",
        "question_ids": ids,
        "max_score": max_score,
    }).execute().data[0]

    return {
        "session": session,
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
        await enforce_ai_rate_limit(
            current_user.user_id,
            bucket="essay-grade",
            limit=20,
            window_seconds=60,
        )
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


ALLOWED_SCAN_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_SCAN_SIZE = 12 * 1024 * 1024


def _validate_image_magic(content: bytes, mime_type: str) -> bool:
    if mime_type == "image/jpeg":
        return len(content) >= 3 and content[:3] == b"\xff\xd8\xff"
    if mime_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return (
            len(content) >= 12
            and content[:4] == b"RIFF"
            and content[8:12] == b"WEBP"
        )
    return False


def _get_owned_quiz_session(
    db,
    project_id: str,
    session_id: str,
    user_id: str,
) -> dict:
    session = (
        db.table("quiz_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if session.data["status"] != "in_progress":
        raise HTTPException(status_code=409, detail="Quiz session is not active")
    return session.data


@router.post(
    "/projects/{project_id}/quiz/sessions/{session_id}/questions/{question_id}/scan",
    status_code=status.HTTP_201_CREATED,
)
async def upload_essay_scan(
    project_id: UUID,
    session_id: UUID,
    question_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> dict:
    db = get_supabase_admin()
    project_id_str = str(project_id)
    session_id_str = str(session_id)
    question_id_str = str(question_id)

    _assert_member(db, project_id_str, current_user.user_id)
    session = _get_owned_quiz_session(
        db,
        project_id_str,
        session_id_str,
        current_user.user_id,
    )
    if question_id_str not in session["question_ids"]:
        raise HTTPException(status_code=404, detail="Question not in this quiz")

    question = (
        db.table("questions")
        .select("*")
        .eq("id", question_id_str)
        .eq("project_id", project_id_str)
        .maybe_single()
        .execute()
    )
    if not question.data:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.data["question_type"] != "essay":
        raise HTTPException(status_code=400, detail="Image scan is only supported for essay questions")

    content = await file.read()
    mime_type = file.content_type or ""
    if not content:
        raise HTTPException(status_code=400, detail="Image is empty")
    if len(content) > MAX_SCAN_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 12 MB)")
    if mime_type not in ALLOWED_SCAN_MIME:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP are supported")
    if not _validate_image_magic(content, mime_type):
        raise HTTPException(status_code=415, detail="File content does not match its image MIME type")

    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[mime_type]
    storage_path = (
        f"projects/{project_id_str}/users/{current_user.user_id}/"
        f"quiz/{session_id_str}/{question_id_str}/{uuid4().hex}.{extension}"
    )

    db.storage.from_("quiz-submissions").upload(
        storage_path,
        content,
        {"content-type": mime_type},
    )

    await enforce_ai_rate_limit(
        current_user.user_id,
        bucket="ocr",
        limit=10,
        window_seconds=300,
    )

    try:
        ocr = await run_in_threadpool(
            get_ocr_service().extract,
            content,
            mime_type,
        )
    except Exception as exc:
        db.storage.from_("quiz-submissions").remove([storage_path])
        raise HTTPException(status_code=502, detail="OCR failed") from exc

    existing = (
        db.table("quiz_attempts")
        .select("id, image_storage_path")
        .eq("quiz_session_id", session_id_str)
        .eq("question_id", question_id_str)
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "quiz_session_id": session_id_str,
        "question_id": question_id_str,
        "user_id": current_user.user_id,
        "project_id": project_id_str,
        "submission_type": "image_scan",
        "question_text_snapshot": question.data["question_text"],
        "options_snapshot": question.data.get("options"),
        "rubric_snapshot": question.data.get("rubric"),
        "max_score_snapshot": question.data["max_score"],
        "user_answer": None,
        "ocr_raw_text": ocr["text"],
        "ocr_confirmed_text": None,
        "ocr_uncertain_regions": ocr["uncertain_regions"],
        "image_storage_path": storage_path,
        "image_deleted_at": None,
        "score": None,
        "is_correct": None,
        "feedback": None,
        "grading_method": None,
        "model_name": question.data.get("model_name"),
        "prompt_version": question.data.get("prompt_version"),
        "status": "ocr_pending_confirmation",
        "submitted_at": None,
        "graded_at": None,
    }

    old_path = None
    if existing.data:
        old_path = existing.data.get("image_storage_path")
        attempt = (
            db.table("quiz_attempts")
            .update(payload)
            .eq("id", existing.data["id"])
            .execute()
        ).data[0]
    else:
        attempt = db.table("quiz_attempts").insert(payload).execute().data[0]

    if old_path and old_path != storage_path:
        try:
            db.storage.from_("quiz-submissions").remove([old_path])
        except Exception:
            pass

    return attempt


@router.post("/quiz-attempts/{attempt_id}/confirm-scan")
async def confirm_essay_scan(
    attempt_id: UUID,
    body: ConfirmScanRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    attempt = (
        db.table("quiz_attempts")
        .select("*")
        .eq("id", str(attempt_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not attempt.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    if attempt.data["submission_type"] != "image_scan":
        raise HTTPException(status_code=400, detail="Attempt is not an image scan")
    if attempt.data["status"] != "ocr_pending_confirmation":
        raise HTTPException(status_code=409, detail="OCR text is not awaiting confirmation")
    if not attempt.data.get("question_id"):
        raise HTTPException(status_code=400, detail="Original question is unavailable")

    question = (
        db.table("questions")
        .select("*")
        .eq("id", attempt.data["question_id"])
        .maybe_single()
        .execute()
    )
    if not question.data:
        raise HTTPException(status_code=404, detail="Question not found")

    confirmed_text = body.text.strip()
    await enforce_ai_rate_limit(
        current_user.user_id,
        bucket="essay-grade",
        limit=20,
        window_seconds=60,
    )
    graded = await run_in_threadpool(
        get_quiz_service().grade_essay,
        question.data,
        confirmed_text,
    )

    now = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("quiz_attempts")
        .update({
            "user_answer": confirmed_text,
            "ocr_confirmed_text": confirmed_text,
            "score": graded["score"],
            "is_correct": graded["is_correct"],
            "feedback": graded["feedback"],
            "grading_method": graded["grading_method"],
            "status": "graded",
            "submitted_at": now,
            "graded_at": now,
        })
        .eq("id", str(attempt_id))
        .eq("user_id", current_user.user_id)
        .execute()
    )
    updated = result.data[0]

    score_ratio = graded["score"] / float(question.data["max_score"] or 1)
    await run_in_threadpool(
        get_quiz_service().update_review_state,
        current_user.user_id,
        attempt.data["project_id"],
        attempt.data["question_id"],
        score_ratio,
    )

    return updated


@router.get("/quiz-attempts/{attempt_id}/scan-url")
async def get_scan_signed_url(
    attempt_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    attempt = (
        db.table("quiz_attempts")
        .select("id, image_storage_path")
        .eq("id", str(attempt_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not attempt.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    if not attempt.data.get("image_storage_path"):
        raise HTTPException(status_code=404, detail="Scan image is unavailable")

    signed = db.storage.from_("quiz-submissions").create_signed_url(
        attempt.data["image_storage_path"],
        300,
    )
    return {"signed_url": signed["signedURL"]}


@router.delete(
    "/quiz-attempts/{attempt_id}/scan",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_scan_image(
    attempt_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    db = get_supabase_admin()
    attempt = (
        db.table("quiz_attempts")
        .select("id, image_storage_path")
        .eq("id", str(attempt_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not attempt.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    path = attempt.data.get("image_storage_path")
    if path:
        db.storage.from_("quiz-submissions").remove([path])

    db.table("quiz_attempts").update({
        "image_storage_path": None,
        "image_deleted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", str(attempt_id)).eq(
        "user_id", current_user.user_id
    ).execute()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
