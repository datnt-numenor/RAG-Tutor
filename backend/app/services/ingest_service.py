"""
Ingest Service — Milestone 2.

Steps: store → extract → chunk → embed → summarize → activate
Each step is idempotent; retry resumes from last incomplete stage.
"""
from __future__ import annotations


class IngestService:
    """Placeholder — implement in Milestone 2."""

    async def run(self, document_id: str, version_id: str, job_id: str) -> None:
        raise NotImplementedError("IngestService.run not yet implemented")
