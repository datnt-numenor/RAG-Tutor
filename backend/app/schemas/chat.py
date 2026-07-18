"""Pydantic schemas for Chat domain."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ChatSessionOut(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    status: str
    citations: list | None
    model_name: str | None
    prompt_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
