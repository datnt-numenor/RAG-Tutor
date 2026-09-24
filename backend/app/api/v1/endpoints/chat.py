from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

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
