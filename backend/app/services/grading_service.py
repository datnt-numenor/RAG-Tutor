"""
Grading Service — Milestone 7 & 8.

MCQ:  rule-based (compare correct_answer)
Essay: LLM-as-judge via Gemini + LangChain structured output
       Uses rubric + key_points + source chunk evidence
Image: OCR confirmation required before grading
"""
from __future__ import annotations


class GradingService:
    """Placeholder — implement in Milestones 7-8."""

    async def grade_mcq(self, attempt_id: str) -> dict:
        raise NotImplementedError

    async def grade_essay(self, attempt_id: str) -> dict:
        raise NotImplementedError

    async def ocr_image(self, attempt_id: str, image_bytes: bytes) -> str:
        raise NotImplementedError
