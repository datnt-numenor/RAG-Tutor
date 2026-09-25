from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.rag_service import get_rag_service
from app.core.rate_limit import enforce_ai_rate_limit
from app.services.progress_service import get_progress_service

router = APIRouter()
logger = structlog.get_logger()


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



class MessageCreate(BaseModel):
    content: str


def _sse(event: str, payload: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    )


@router.get("/projects/{project_id}/chat/sessions")
async def list_sessions(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    res = (
        db.table("chat_sessions")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/projects/{project_id}/chat/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    project_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    res = db.table("chat_sessions").insert({
        "project_id": str(project_id),
        "user_id": current_user.user_id,
        "title": "New conversation",
    }).execute()
    return res.data[0]


@router.get("/projects/{project_id}/chat/sessions/{session_id}/messages")
async def list_messages(
    project_id: UUID,
    session_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[dict]:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    session = (
        db.table("chat_sessions")
        .select("id")
        .eq("id", str(session_id))
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    res = (
        db.table("chat_messages")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at")
        .execute()
    )
    return res.data


@router.post("/projects/{project_id}/chat/sessions/{session_id}/messages", status_code=201)
async def send_message(
    project_id: UUID,
    session_id: UUID,
    body: MessageCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    await enforce_ai_rate_limit(
        current_user.user_id,
        bucket="chat",
        limit=30,
        window_seconds=60,
    )

    session = (
        db.table("chat_sessions")
        .select("id, title")
        .eq("id", str(session_id))
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = db.table("chat_messages").insert({
        "session_id": str(session_id),
        "role": "user",
        "content": body.content,
        "status": "delivered",
    }).execute().data[0]

    await run_in_threadpool(
        get_progress_service().record_event,
        user_id=current_user.user_id,
        project_id=str(project_id),
        event_type="chat_question",
        source_id=user_msg["id"],
        idempotency_key=f"chat_message:{user_msg['id']}",
    )

    rag_service = get_rag_service()

    try:
        result = await run_in_threadpool(
            rag_service.answer,
            str(project_id),
            body.content,
        )
    except Exception as exc:
        db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "assistant",
            "content": "Không thể xử lý câu hỏi lúc này.",
            "status": "error",
        }).execute()
        raise HTTPException(status_code=502, detail="RAG generation failed") from exc

    msg_res = db.table("chat_messages").insert({
        "session_id": str(session_id),
        "role": "assistant",
        "content": result["answer"],
        "status": "delivered",
        "citations": result["sources"],
        "retrieval_params": {
            **result["retrieval_params"],
            "rag_status": result["status"],
        },
        "model_name": result["model_name"],
        "prompt_version": result["prompt_version"],
    }).execute()

    session_update = {}
    if session.data.get("title") == "New conversation":
        session_update["title"] = body.content[:80]

    session_update["updated_at"] = datetime.now(timezone.utc).isoformat()

    db.table("chat_sessions").update(session_update).eq(
        "id", str(session_id)
    ).execute()

    return msg_res.data[0]



@router.post(
    "/projects/{project_id}/chat/sessions/{session_id}/messages/stream"
)
async def send_message_stream(
    project_id: UUID,
    session_id: UUID,
    body: MessageCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    await enforce_ai_rate_limit(
        current_user.user_id,
        bucket="chat",
        limit=30,
        window_seconds=60,
    )

    session = (
        db.table("chat_sessions")
        .select("id, title")
        .eq("id", str(session_id))
        .eq("project_id", str(project_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = db.table("chat_messages").insert({
        "session_id": str(session_id),
        "role": "user",
        "content": body.content,
        "status": "delivered",
    }).execute().data[0]

    await run_in_threadpool(
        get_progress_service().record_event,
        user_id=current_user.user_id,
        project_id=str(project_id),
        event_type="chat_question",
        source_id=user_msg["id"],
        idempotency_key=f"chat_message:{user_msg['id']}",
    )

    rag_service = get_rag_service()
    try:
        results = await run_in_threadpool(
            rag_service.retrieve,
            str(project_id),
            body.content,
            5,
            0.30,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="RAG retrieval failed",
        ) from exc

    retrieval_params = {
        "top_k": 5,
        "threshold": 0.30,
        "retrieved_count": len(results),
    }

    if not results:
        answer = "Không đủ thông tin trong tài liệu để trả lời câu hỏi này."
        assistant = db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "assistant",
            "content": answer,
            "status": "delivered",
            "citations": [],
            "retrieval_params": {
                **retrieval_params,
                "rag_status": "insufficient_evidence",
            },
            "model_name": rag_service.gemini_model,
            "prompt_version": "basic-rag-v1-stream",
        }).execute().data[0]

        def no_evidence_stream():
            yield _sse("meta", {
                "status": "insufficient_evidence",
                "sources": [],
                "retrieval_params": retrieval_params,
            })
            yield _sse("token", {"text": answer})
            yield _sse("done", {"message_id": assistant["id"]})

        return StreamingResponse(
            no_evidence_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    context = rag_service.build_context(results)
    sources = rag_service.build_sources(results)

    def event_stream():
        answer_parts: list[str] = []

        yield _sse("meta", {
            "status": "ok",
            "sources": sources,
            "retrieval_params": retrieval_params,
        })

        try:
            for text_delta in rag_service.stream_generate_answer(
                question=body.content,
                context=context,
            ):
                answer_parts.append(text_delta)
                yield _sse("token", {"text": text_delta})

            answer = "".join(answer_parts).strip()
            if not answer:
                raise RuntimeError("Gemini stream returned no text")

            assistant = db.table("chat_messages").insert({
                "session_id": str(session_id),
                "role": "assistant",
                "content": answer,
                "status": "delivered",
                "citations": sources,
                "retrieval_params": {
                    **retrieval_params,
                    "rag_status": "ok",
                },
                "model_name": rag_service.gemini_model,
                "prompt_version": "basic-rag-v1-stream",
            }).execute().data[0]

            session_update = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if session.data.get("title") == "New conversation":
                session_update["title"] = body.content[:80]

            db.table("chat_sessions").update(session_update).eq(
                "id", str(session_id)
            ).execute()

            yield _sse("done", {"message_id": assistant["id"]})
        except Exception as exc:
            logger.exception(
                "chat_stream_failed",
                project_id=str(project_id),
                session_id=str(session_id),
                error_type=exc.__class__.__name__,
                emitted_parts=len(answer_parts),
            )
            error_text = "Không thể xử lý câu hỏi lúc này."
            db.table("chat_messages").insert({
                "session_id": str(session_id),
                "role": "assistant",
                "content": error_text,
                "status": "error",
                "citations": sources,
                "retrieval_params": {
                    **retrieval_params,
                    "rag_status": "error",
                },
                "model_name": rag_service.gemini_model,
                "prompt_version": "basic-rag-v1-stream",
            }).execute()
            yield _sse("error", {
                "message": error_text,
                "error_type": exc.__class__.__name__,
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
