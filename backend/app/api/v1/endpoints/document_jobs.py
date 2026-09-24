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
    res = db.table("document_jobs").select("*, document_versions(project_id)").eq("id", str(job_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")

    version = res.data.get("document_versions")
    if not version:
        raise HTTPException(status_code=404, detail="Job not found")

    member = (
        db.table("project_members").select("id")
        .eq("project_id", version["project_id"])
        .eq("user_id", current_user.user_id)
        .maybe_single().execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return res.data


@router.post("/{job_id}/retry", status_code=202)
async def retry_job(
    job_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    job = db.table("document_jobs").select("*, document_versions(project_id)").eq("id", str(job_id)).maybe_single().execute()
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    version = job.data.get("document_versions")
    if not version:
        raise HTTPException(status_code=400, detail="Only ingest jobs can currently be retried")

    owner = (
        db.table("project_members").select("id")
        .eq("project_id", version["project_id"])
        .eq("user_id", current_user.user_id)
        .eq("role", "owner")
        .maybe_single().execute()
    )
    if not owner.data:
        raise HTTPException(status_code=403, detail="Only the project owner can retry ingestion")

    if job.data["status"] not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Job is not in a retryable state")

    if job.data["job_type"] != "ingest" or not job.data.get("document_version_id"):
        raise HTTPException(status_code=400, detail="Only ingest jobs can currently be retried")

    db.table("document_jobs").update({
        "status": "queued",
        "attempt_count": 0,
        "last_error": None,
    }).eq("id", str(job_id)).execute()

    from app.workers.ingest_worker import ingest_document

    try:
        ingest_document.delay(
            job.data["document_id"],
            job.data["document_version_id"],
            str(job_id),
        )
    except Exception as exc:
        db.table("document_jobs").update({
            "status": "failed",
            "last_error": f"Failed to dispatch ingest worker: {exc}",
        }).eq("id", str(job_id)).execute()
        raise HTTPException(status_code=503, detail="Could not queue retry") from exc

    return {"job_id": str(job_id), "message": "Retry queued"}
