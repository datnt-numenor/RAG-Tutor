"""Pydantic schemas for Document domain."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: UUID
    project_id: UUID
    created_by: UUID
    active_version_id: UUID | None
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentVersionOut(BaseModel):
    id: UUID
    document_id: UUID
    version_number: int
    original_filename: str
    mime_type: str
    file_size: int
    page_count: int | None
    status: str
    summary: str | None
    embedding_model: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class DocumentJobOut(BaseModel):
    id: UUID
    document_id: UUID
    document_version_id: UUID | None
    job_type: str
    status: str
    stage: str | None
    progress_current: int
    progress_total: int
    attempt_count: int
    max_attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    job_id: UUID
