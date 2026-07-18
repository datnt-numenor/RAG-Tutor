"""Pydantic schemas for Note/Annotation domain."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class Rectangle(BaseModel):
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)


class NoteCreate(BaseModel):
    page_number: int = Field(..., ge=1)
    annotation_type: str  # text_highlight | rectangle
    selected_text: str | None = None
    rectangles: list[Rectangle] | None = None
    content: str | None = None
    color: str = "#FFFF00"


class NoteUpdate(BaseModel):
    content: str | None = None
    color: str | None = None
    rectangles: list[Rectangle] | None = None


class NoteOut(BaseModel):
    id: UUID
    user_id: UUID
    document_version_id: UUID
    page_number: int
    annotation_type: str
    selected_text: str | None
    rectangles: list | None
    content: str | None
    color: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
