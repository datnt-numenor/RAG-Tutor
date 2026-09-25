from __future__ import annotations

from functools import lru_cache

from app.services.ai_provider import TextGenerationProvider, get_aux_text_provider


class DocumentSummaryService:
    def __init__(self, provider: TextGenerationProvider):
        self.provider = provider
        self.model = provider.model_name

    def summarize(
        self,
        *,
        filename: str,
        chunks: list[dict],
        max_chars: int = 18000,
    ) -> str:
        parts: list[str] = []
        used = 0

        for chunk in chunks:
            content = str(chunk.get("content") or "").strip()
            if not content:
                continue

            section = chunk.get("section_title")
            prefix = f"[{section}]\n" if section else ""
            candidate = prefix + content
            remaining = max_chars - used
            if remaining <= 0:
                break
            if len(candidate) > remaining:
                candidate = candidate[:remaining]
            parts.append(candidate)
            used += len(candidate)

        if not parts:
            raise ValueError("No text available for summary")

        context = "\n\n".join(parts)
        prompt = f"""
Tóm tắt tài liệu học tập dưới đây.

File: {filename}

Yêu cầu:
- Chỉ dùng nội dung được cung cấp.
- Viết cùng ngôn ngữ chủ yếu với tài liệu.
- Mở đầu bằng 1 đoạn ngắn nêu tài liệu nói về gì.
- Sau đó liệt kê 3-7 ý chính.
- Không bịa thông tin không có trong tài liệu.
- Tối đa khoảng 350 từ.

Nội dung:
{context}
""".strip()

        summary = self.provider.generate(prompt).strip()
        if not summary:
            raise ValueError("AI provider returned empty document summary")
        return summary


@lru_cache
def get_document_summary_service() -> DocumentSummaryService:
    return DocumentSummaryService(provider=get_aux_text_provider())
