from __future__ import annotations

from functools import lru_cache

from app.core.database import get_supabase_admin
from app.services.ai_provider import TextGenerationProvider, get_text_provider
from app.services.embedding_service import EmbeddingService


class RAGService:
    def __init__(
        self,
        supabase,
        provider: TextGenerationProvider,
    ):
        self.supabase = supabase
        self.embedding_service = EmbeddingService()
        self.provider = provider
        # Kept for the existing API/database response contract.
        self.gemini_model = provider.model_name

    def retrieve(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.30,
    ) -> list[dict]:
        query_embedding = self.embedding_service.embed(query)

        response = self.supabase.rpc(
            "match_chunks",
            {
                "filter_project_id": project_id,
                "query_embedding": query_embedding,
                "match_count": top_k,
                "match_threshold": threshold,
            },
        ).execute()

        return response.data or []

    def build_context(self, results: list[dict]) -> str:
        parts: list[str] = []

        for index, result in enumerate(results, start=1):
            source_file = result.get("source_file") or "unknown"
            page_number = result.get("page_number")
            page_label = f"page {page_number}" if page_number is not None else "page unknown"

            parts.append(
                f"[Source {index} | {source_file} | {page_label}]\n"
                f"{result['content']}"
            )

        return "\n\n".join(parts)

    def build_prompt(self, question: str, context: str) -> str:
        return f"""
Bạn là trợ lý học tập trả lời câu hỏi dựa trên tài liệu được cung cấp.

Context:
{context}

Question:
{question}

Yêu cầu:
- Chỉ trả lời dựa trên context.
- Không tự thêm thông tin bên ngoài context.
- Nếu context không đủ thông tin, trả lời đúng câu:
  "Không đủ thông tin trong tài liệu để trả lời câu hỏi này."
- Trả lời ngắn gọn, rõ ràng và bằng cùng ngôn ngữ với câu hỏi.
""".strip()

    def generate_answer(self, question: str, context: str) -> str:
        prompt = self.build_prompt(question=question, context=context)

        return self.provider.generate(prompt)

    def stream_generate_answer(self, question: str, context: str):
        """Yield text deltas from Gemini Interactions streaming."""
        prompt = self.build_prompt(question=question, context=context)
        yield from self.provider.stream(prompt)

    def build_sources(self, results: list[dict]) -> list[dict]:
        sources: list[dict] = []
        seen: set[tuple] = set()

        for result in results:
            key = (
                result.get("document_version_id"),
                result.get("page_number"),
            )
            if key in seen:
                continue

            seen.add(key)
            sources.append(
                {
                    "chunk_id": result.get("id"),
                    "document_id": result.get("document_id"),
                    "document_version_id": result.get("document_version_id"),
                    "source_file": result.get("source_file"),
                    "page": result.get("page_number"),
                    "similarity": result.get("similarity"),
                }
            )

        return sources

    def answer(
        self,
        project_id: str,
        question: str,
        top_k: int = 5,
        threshold: float = 0.30,
    ) -> dict:
        results = self.retrieve(
            project_id=project_id,
            query=question,
            top_k=top_k,
            threshold=threshold,
        )

        retrieval_params = {
            "top_k": top_k,
            "threshold": threshold,
            "retrieved_count": len(results),
        }

        if not results:
            return {
                "status": "insufficient_evidence",
                "answer": "Không đủ thông tin trong tài liệu để trả lời câu hỏi này.",
                "sources": [],
                "retrieval_params": retrieval_params,
                "model_name": self.gemini_model,
                "prompt_version": "basic-rag-v1",
            }

        context = self.build_context(results)
        answer = self.generate_answer(question=question, context=context)

        return {
            "status": "ok",
            "answer": answer,
            "sources": self.build_sources(results),
            "retrieval_params": retrieval_params,
            "model_name": self.gemini_model,
            "prompt_version": "basic-rag-v1",
        }


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService(
        supabase=get_supabase_admin(),
        provider=get_text_provider(),
    )
