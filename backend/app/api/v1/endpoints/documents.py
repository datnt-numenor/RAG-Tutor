from __future__ import annotations

import hashlib
from typing import Annotated
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()

ALLOWED_MIME = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _assert_owner(db, project_id: str, user_id: str) -> None:
    owner = (
        db.table("project_members").select("id")
        .eq("project_id", project_id).eq("user_id", user_id)
        .eq("role", "owner").maybe_single().execute()
    )
    if not owner.data:
        raise HTTPException(status_code=403, detail="Only the project owner can manage documents")


def _assert_member(db, project_id: str, user_id: str) -> None:
    member = (
        db.table("project_members").select("id")
        .eq("project_id", project_id).eq("user_id", user_id)
        .maybe_single().execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Upload PDF/DOCX, create document record + ingest job. Returns 202 immediately."""
    db = get_supabase_admin()
    _assert_owner(db, str(project_id), current_user.user_id)

    # Validate MIME
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX are supported")

    sha256 = hashlib.sha256(content).hexdigest()

    # Create document record
    doc_res = db.table("documents").insert({
        "project_id": str(project_id),
        "created_by": current_user.user_id,
        "display_name": file.filename,
        "status": "active",
    }).execute()
    document_id = doc_res.data[0]["id"]

    # Determine version number
    prev_versions = (
        db.table("document_versions")
        .select("version_number")
        .eq("document_id", document_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    version_number = (prev_versions.data[0]["version_number"] + 1) if prev_versions.data else 1

    storage_path = f"projects/{project_id}/documents/{document_id}/versions/v{version_number}/{file.filename}"

    # Upload to Supabase Storage
    db.storage.from_("documents").upload(storage_path, content, {"content-type": file.content_type})

    # Create version record
    ver_res = db.table("document_versions").insert({
        "document_id": document_id,
        "project_id": str(project_id),
        "version_number": version_number,
        "storage_path": storage_path,
        "original_filename": file.filename,
        "mime_type": file.content_type,
        "file_size": len(content),
        "sha256": sha256,
        "status": "pending",
    }).execute()
    version_id = ver_res.data[0]["id"]

    # Create ingest job
    job_res = db.table("document_jobs").insert({
        "document_id": document_id,
        "document_version_id": version_id,
        "job_type": "ingest",
        "status": "queued",
        "stage": "store",
        "max_attempts": 3,
    }).execute()
    job_id = job_res.data[0]["id"]

    # TODO: dispatch Celery task: ingest_document.delay(document_id, version_id, job_id)

    return {"document_id": document_id, "version_id": version_id, "job_id": job_id}


@router.get("/projects/{project_id}/documents")
async def list_documents(
    project_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict]:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)

    res = (
        db.table("documents")
        .select("*, document_versions!active_version_id(status, version_number)")
        .eq("project_id", str(project_id))
        .neq("status", "deleting")
        .execute()
    )
    return res.data


@router.delete("/projects/{project_id}/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_document(
    project_id: UUID,
    document_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Permanent deletion — returns 202 immediately, cleanup runs in background."""
    db = get_supabase_admin()
    _assert_owner(db, str(project_id), current_user.user_id)

    # Check for existing delete job
    existing = (
        db.table("document_jobs")
        .select("id")
        .eq("document_id", str(document_id))
        .eq("job_type", "delete")
        .not_.in_("status", ["succeeded", "failed", "cancelled"])
        .maybe_single()
        .execute()
    )
    if existing.data:
        return {"job_id": existing.data["id"], "message": "Deletion already in progress"}

    # Mark as deleting and clear active version
    db.table("documents").update({
        "status": "deleting",
        "active_version_id": None,
    }).eq("id", str(document_id)).execute()

    # Create delete job
    job_res = db.table("document_jobs").insert({
        "document_id": str(document_id),
        "job_type": "delete",
        "status": "queued",
        "stage": "exclude",
        "max_attempts": 5,
    }).execute()
    job_id = job_res.data[0]["id"]

    # TODO: dispatch Celery task: delete_document.delay(str(document_id), job_id)

    return {"job_id": job_id, "message": "Deletion queued"}


@router.get("/document-versions/{version_id}/signed-url")
async def get_signed_url(
    version_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    db = get_supabase_admin()
    ver = db.table("document_versions").select("storage_path, project_id").eq("id", str(version_id)).single().execute()
    if not ver.data:
        raise HTTPException(status_code=404, detail="Version not found")

    _assert_member(db, ver.data["project_id"], current_user.user_id)

    signed = db.storage.from_("documents").create_signed_url(ver.data["storage_path"], 300)
    return {"signed_url": signed["signedURL"]}
