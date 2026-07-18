"""
Chunking Service — Milestone 2.

Custom Vietnamese-aware chunker (Plan.md §3):
  1. Split by paragraph (\\n\\n) and headings
  2. Sentence tokenization (regex, handles TP.HCM, GS., numbers)
  3. Greedy merge to target_tokens=220, max_tokens=256
  4. Add 1-2 sentence overlap between chunks
  5. Attach metadata: page, section_title, chunk_index, source_spans
"""
from __future__ import annotations


class ChunkingService:
    """Placeholder — implement in Milestone 2."""

    def chunk(self, text: str, page_number: int = 1) -> list[dict]:
        raise NotImplementedError("ChunkingService.chunk not yet implemented")
