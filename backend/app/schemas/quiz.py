"""Pydantic schemas for Quiz domain."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class QuizSessionOut(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    status: str
    question_ids: list[UUID]
    total_score: Decimal | None
    max_score: Decimal | None
    started_at: datetime
    submitted_at: datetime | None
    graded_at: datetime | None

    model_config = {"from_attributes": True}


class AnswerSubmit(BaseModel):
    question_id: UUID
    user_answer: str
    submission_type: str = "text"  # text | image_scan


class QuizAttemptOut(BaseModel):
    id: UUID
    quiz_session_id: UUID
    question_id: UUID | None
    status: str
    score: Decimal | None
    is_correct: bool | None
    feedback: str | None
    submitted_at: datetime | None
    graded_at: datetime | None

    model_config = {"from_attributes": True}
