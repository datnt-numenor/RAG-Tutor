from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()


@router.get("/{job_id}")
async def get_job(
    job_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    res = db.table("document_jobs").select("*").eq("id", str(job_id)).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return res.data


@router.post("/{job_id}/retry", status_code=202)
async def retry_job(
    job_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    job = db.table("document_jobs").select("*").eq("id", str(job_id)).single().execute()
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.data["status"] not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Job is not in a retryable state")

    db.table("document_jobs").update({"status": "queued", "attempt_count": 0}).eq("id", str(job_id)).execute()
    # TODO: re-dispatch Celery task based on job_type
    return {"job_id": str(job_id), "message": "Retry queued"}
