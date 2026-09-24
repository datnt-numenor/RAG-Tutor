from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from time import perf_counter

import pdfplumber
import structlog
from docx import Document as DocxDocument

from app.core.database import get_supabase_admin
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger()


class IngestService:
    def __init__(self, supabase=None):
        self.supabase = supabase or get_supabase_admin()
        self.embedding_service = EmbeddingService()
        self.chunking_service = ChunkingService(
            token_counter=self.embedding_service.count_tokens,
            model_max_tokens=self.embedding_service.max_seq_length,
            overlap_sentences=1,
        )

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
            text = "\n".join(
                paragraph.text
                for paragraph in doc.paragraphs
                if paragraph.text.strip()
            )
            return [{"page": 1, "text": text}]

        raise ValueError(f"Unsupported mime type: {mime_type}")

    def _chunk_pages(self, pages: list[dict]) -> list[dict]:
        all_chunks: list[dict] = []

        for page in pages:
            page_chunks = self.chunking_service.chunk(
                text=page["text"],
                page_number=page["page"],
            )
            all_chunks.extend(page_chunks)

        for chunk_index, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = chunk_index

        return all_chunks

    def _build_rows(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        project_id: str,
        document_id: str,
        version_id: str,
    ) -> list[dict]:
        rows: list[dict] = []

        for chunk, embedding in zip(chunks, embeddings):
            rows.append(
                {
                    "project_id": project_id,
                    "document_id": document_id,
                    "document_version_id": version_id,
                    "content": chunk["content"],
                    "embedding": embedding,
                    "page_number": chunk["page_number"],
                    "section_title": chunk.get("section_title"),
                    "chunk_index": chunk["chunk_index"],
                    "source_spans": chunk.get("source_spans"),
                    "token_count": chunk.get("token_count"),
                }
            )

        return rows

    def process_pages(
        self,
        pages: list[dict],
        project_id: str,
        document_id: str,
        version_id: str,
    ) -> list[dict]:
        chunks = self._chunk_pages(pages)
        embeddings = self.embedding_service.embed_many(
            [chunk["content"] for chunk in chunks]
        )
        return self._build_rows(
            chunks=chunks,
            embeddings=embeddings,
            project_id=project_id,
            document_id=document_id,
            version_id=version_id,
        )

    def _insert_in_batches(self, rows: list[dict], batch_size: int = 100) -> None:
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            self.supabase.table("chunks").insert(batch).execute()

    def run(self, document_id: str, version_id: str, job_id: str) -> None:
        started = perf_counter()
        now = datetime.now(timezone.utc).isoformat()

        try:
            job_res = (
                self.supabase.table("document_jobs")
                .select("attempt_count, max_attempts")
                .eq("id", job_id)
                .single()
                .execute()
            )
            current_attempt = int(job_res.data.get("attempt_count") or 0)
            max_attempts = int(job_res.data.get("max_attempts") or 3)
            next_attempt = current_attempt + 1

            if next_attempt > max_attempts:
                raise RuntimeError(
                    f"Ingest job exceeded max attempts ({max_attempts})"
                )

            self.supabase.table("document_jobs").update(
                {
                    "status": "running",
                    "stage": "extract",
                    "attempt_count": next_attempt,
                    "last_error": None,
                    "progress_current": 0,
                    "progress_total": 4,
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
                    "summary": None,
                    "summary_status": None,
                    "error_code": None,
                    "error_message": None,
                }
            ).eq("id", version_id).execute()

            extract_started = perf_counter()
            file_bytes = self.supabase.storage.from_("documents").download(
                version["storage_path"]
            )
            pages = self._extract_pages(
                content=file_bytes,
                mime_type=version["mime_type"],
            )
            logger.info(
                "ingest_stage_complete",
                job_id=job_id,
                stage="extract",
                duration_ms=round((perf_counter() - extract_started) * 1000, 2),
                page_count=len(pages),
            )

            self.supabase.table("document_jobs").update(
                {
                    "stage": "chunk",
                    "progress_current": 1,
                    "progress_total": 4,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", job_id).execute()

            chunk_started = perf_counter()
            chunks = self._chunk_pages(pages)
            if not chunks:
                raise ValueError("No extractable text found in document")

            logger.info(
                "ingest_stage_complete",
                job_id=job_id,
                stage="chunk",
                duration_ms=round((perf_counter() - chunk_started) * 1000, 2),
                chunk_count=len(chunks),
            )

            self.supabase.table("document_jobs").update(
                {
                    "stage": "embed",
                    "progress_current": 2,
                    "progress_total": 4,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", job_id).execute()

            embed_started = perf_counter()
            embeddings = self.embedding_service.embed_many(
                [chunk["content"] for chunk in chunks]
            )
            rows = self._build_rows(
                chunks=chunks,
                embeddings=embeddings,
                project_id=version["project_id"],
                document_id=document_id,
                version_id=version_id,
            )
            logger.info(
                "ingest_stage_complete",
                job_id=job_id,
                stage="embed",
                duration_ms=round((perf_counter() - embed_started) * 1000, 2),
                chunk_count=len(rows),
                batch_size=self.embedding_service.batch_size,
            )

            persist_started = perf_counter()

            # Idempotent retry: replace all chunks for this version.
            self.supabase.table("chunks").delete().eq(
                "document_version_id", version_id
            ).execute()
            self._insert_in_batches(rows)

            self.supabase.table("document_jobs").update(
                {
                    "stage": "activate",
                    "progress_current": 3,
                    "progress_total": 4,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", job_id).execute()

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

            # The document becomes searchable here. Summary generation is
            # intentionally decoupled and must not block RAG readiness.
            self.supabase.table("document_versions").update(
                {
                    "status": "ready",
                    "page_count": len(pages),
                    "embedding_model": self.embedding_service.model_name,
                    "chunker_version": self.chunking_service.VERSION,
                    "processed_at": processed_at,
                    "summary": None,
                    "summary_status": "queued",
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

            logger.info(
                "ingest_stage_complete",
                job_id=job_id,
                stage="persist_activate",
                duration_ms=round((perf_counter() - persist_started) * 1000, 2),
            )
            logger.info(
                "ingest_complete",
                job_id=job_id,
                version_id=version_id,
                duration_ms=round((perf_counter() - started) * 1000, 2),
                chunk_count=len(rows),
            )

            # Summary is best-effort background work. A Gemini outage must not
            # make an otherwise searchable document look like a failed ingest.
            try:
                from app.workers.summary_worker import summarize_document

                summarize_document.apply_async(
                    args=[version_id],
                    priority=0,
                )
            except Exception as summary_dispatch_exc:
                self.supabase.table("document_versions").update(
                    {
                        "summary_status": "error",
                        "summary": None,
                    }
                ).eq("id", version_id).execute()
                logger.warning(
                    "document_summary_dispatch_failed",
                    version_id=version_id,
                    error=summary_dispatch_exc.__class__.__name__,
                )

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

            logger.exception(
                "ingest_failed",
                job_id=job_id,
                version_id=version_id,
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            raise
