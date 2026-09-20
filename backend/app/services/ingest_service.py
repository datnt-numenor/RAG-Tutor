from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

import pdfplumber
from docx import Document as DocxDocument

from app.core.database import get_supabase_admin
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService


class IngestService:
    def __init__(self, supabase=None):
        self.supabase = supabase or get_supabase_admin()
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()

    def _extract_pages(self, content: bytes, mime_type: str) -> list[dict]:
        if mime_type == "application/pdf":
            pages: list[dict] = []
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    pages.append(
                        {
                            "page": page_number,
                            "text": page.extract_text() or "",
                        }
                    )
            return pages

        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = DocxDocument(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
            return [{"page": 1, "text": text}]

        raise ValueError(f"Unsupported mime type: {mime_type}")

    def process_pages(
        self,
        pages: list[dict],
        project_id: str,
        document_id: str,
        version_id: str,
    ) -> list[dict]:
        all_chunks: list[dict] = []

        for page in pages:
            page_chunks = self.chunking_service.chunk(
                text=page["text"],
                page_number=page["page"],
            )
            all_chunks.extend(page_chunks)

        for chunk_index, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = chunk_index

        embeddings = self.embedding_service.embed_many(
            [chunk["content"] for chunk in all_chunks]
        )

        rows: list[dict] = []
        for chunk, embedding in zip(all_chunks, embeddings):
            rows.append(
                {
                    "project_id": project_id,
                    "document_id": document_id,
                    "document_version_id": version_id,
                    "content": chunk["content"],
                    "embedding": embedding,
                    "page_number": chunk["page_number"],
                    "chunk_index": chunk["chunk_index"],
                    "source_spans": [
                        {
                            "page_number": chunk["page_number"],
                        }
                    ],
                }
            )

        return rows

    def _insert_in_batches(self, rows: list[dict], batch_size: int = 100) -> None:
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            self.supabase.table("chunks").insert(batch).execute()

    def run(self, document_id: str, version_id: str, job_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()

        try:
            self.supabase.table("document_jobs").update(
                {
                    "status": "running",
                    "stage": "extract",
                    "attempt_count": 1,
                    "last_error": None,
                    "updated_at": now,
                }
            ).eq("id", job_id).execute()

            version_res = (
                self.supabase.table("document_versions")
                .select("*")
                .eq("id", version_id)
                .eq("document_id", document_id)
                .single()
                .execute()
            )
            version = version_res.data

            self.supabase.table("document_versions").update(
                {
                    "status": "processing",
                    "error_code": None,
                    "error_message": None,
                }
            ).eq("id", version_id).execute()

            file_bytes = self.supabase.storage.from_("documents").download(
                version["storage_path"]
            )

            pages = self._extract_pages(
                content=file_bytes,
                mime_type=version["mime_type"],
            )

            self.supabase.table("document_jobs").update(
                {
                    "stage": "chunk",
                    "progress_current": 1,
                    "progress_total": 4,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", job_id).execute()

            rows = self.process_pages(
                pages=pages,
                project_id=version["project_id"],
                document_id=document_id,
                version_id=version_id,
            )

            self.supabase.table("document_jobs").update(
                {
                    "stage": "embed",
                    "progress_current": 2,
                    "progress_total": 4,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", job_id).execute()

            # Idempotent retry: replace all chunks for this version.
            self.supabase.table("chunks").delete().eq(
                "document_version_id", version_id
            ).execute()
            self._insert_in_batches(rows)

            document_res = (
                self.supabase.table("documents")
                .select("active_version_id")
                .eq("id", document_id)
                .single()
                .execute()
            )
            previous_version_id = document_res.data.get("active_version_id")

            if previous_version_id and previous_version_id != version_id:
                self.supabase.table("document_versions").update(
                    {"status": "superseded"}
                ).eq("id", previous_version_id).execute()

            processed_at = datetime.now(timezone.utc).isoformat()

            self.supabase.table("document_versions").update(
                {
                    "status": "ready",
                    "page_count": len(pages),
                    "embedding_model": self.embedding_service.model_name,
                    "chunker_version": "sentence-overlap-v1",
                    "processed_at": processed_at,
                }
            ).eq("id", version_id).execute()

            self.supabase.table("documents").update(
                {
                    "active_version_id": version_id,
                    "status": "active",
                    "updated_at": processed_at,
                }
            ).eq("id", document_id).execute()

            self.supabase.table("document_jobs").update(
                {
                    "status": "succeeded",
                    "stage": "done",
                    "progress_current": 4,
                    "progress_total": 4,
                    "updated_at": processed_at,
                }
            ).eq("id", job_id).execute()

        except Exception as exc:
            failed_at = datetime.now(timezone.utc).isoformat()

            self.supabase.table("document_versions").update(
                {
                    "status": "error",
                    "error_code": exc.__class__.__name__,
                    "error_message": str(exc)[:2000],
                }
            ).eq("id", version_id).execute()

            self.supabase.table("document_jobs").update(
                {
                    "status": "failed",
                    "last_error": str(exc)[:2000],
                    "updated_at": failed_at,
                }
            ).eq("id", job_id).execute()

            raise
