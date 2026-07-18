"""Document repository — Prisma queries for documents, versions, jobs."""
from __future__ import annotations

from app.core.database import prisma


class DocumentRepository:
    async def list_active(self, project_id: str):
        return await prisma.document.find_many(
            where={"project_id": project_id, "status": "active"},
            include={"active_version": True},
            order={"created_at": "desc"},
        )

    async def get_by_id(self, document_id: str):
        return await prisma.document.find_unique(where={"id": document_id})

    async def mark_deleting(self, document_id: str):
        return await prisma.document.update(
            where={"id": document_id},
            data={"status": "deleting", "active_version_id": None},
        )

    async def create_job(self, data: dict):
        return await prisma.documentjob.create(data=data)

    async def get_job(self, job_id: str):
        return await prisma.documentjob.find_unique(where={"id": job_id})

    async def get_active_delete_job(self, document_id: str):
        return await prisma.documentjob.find_first(
            where={
                "document_id": document_id,
                "job_type": "delete",
                "status": {"not_in": ["succeeded", "failed", "cancelled"]},
            }
        )
