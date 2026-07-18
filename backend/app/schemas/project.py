"""Pydantic schemas for Project domain."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    target_score: Decimal | None = Field(None, ge=0, le=100)
    exam_date: date | None = None
    weekly_study_minutes: int | None = Field(None, gt=0)


class ProjectUpdate(ProjectCreate):
    name: str | None = Field(None, min_length=1, max_length=200)  # type: ignore[assignment]


class ProjectOut(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    target_score: Decimal | None
    exam_date: date | None
    weekly_study_minutes: int | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
