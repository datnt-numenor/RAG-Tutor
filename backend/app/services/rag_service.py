"""
RAG Service — Milestone 3.

Pipeline:
  1. Embed user query (sentence-transformers)
  2. Call Supabase RPC `match_chunks` (project-scoped, threshold 0.70)
  3. Rerank / filter results
  4. Build prompt with context + chat history
  5. Stream Gemini response via LangChain
  6. Persist user + assistant messages with citations
"""
from __future__ import annotations


class RAGService:
    """Placeholder — implement in Milestone 3."""

    async def answer(
        self,
        project_id: str,
        session_id: str,
        user_message: str,
    ) -> dict:
        raise NotImplementedError("RAGService.answer not yet implemented")
