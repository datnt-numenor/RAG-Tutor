from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()


class MessageCreate(BaseModel):
    content: str


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
    """
    RAG pipeline:
    1. Embed user query
    2. RPC match_chunks (project-scoped)
    3. LLM generates answer with citations
    4. Persist both user and assistant messages
    TODO: implement full RAG chain in services/rag_service.py
    """
    db = get_supabase_admin()
    # Persist user message
    db.table("chat_messages").insert({
        "session_id": str(session_id),
        "role": "user",
        "content": body.content,
        "status": "delivered",
    }).execute()

    # TODO: call RAGService.answer(project_id, session_id, body.content)
    assistant_reply = "RAG pipeline not yet implemented. Stay tuned!"

    msg_res = db.table("chat_messages").insert({
        "session_id": str(session_id),
        "role": "assistant",
        "content": assistant_reply,
        "status": "delivered",
    }).execute()

    return msg_res.data[0]
