from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from functools import lru_cache

from google import genai

from app.core.config import get_settings
from app.core.database import get_supabase_admin


class QuizService:
    def __init__(self, supabase, gemini_api_key: str, gemini_model: str):
        self.supabase = supabase
        self.gemini_model = gemini_model
        self.client = genai.Client(api_key=gemini_api_key)

    def _active_chunks(self, project_id: str, limit: int = 12) -> list[dict]:
        response = (
            self.supabase.table("chunks")
            .select(
                "id, content, page_number, document_id, document_version_id, "
                "document_versions!inner(original_filename, status), "
                "documents!inner(active_version_id, status)"
            )
            .eq("project_id", project_id)
            .eq("documents.status", "active")
            .eq("document_versions.status", "ready")
            .limit(limit)
            .execute()
        )

        rows: list[dict] = []
        for row in response.data or []:
            doc = row.get("documents") or {}
            if doc.get("active_version_id") != row.get("document_version_id"):
                continue
            rows.append(row)
        return rows

    def _parse_json(self, text: str):
        clean = text.strip()
        clean = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", clean, flags=re.I)
        clean = re.sub(r"\s*\x60\x60\x60\s*$", "", clean)
        return json.loads(clean)

    def generate_questions(
        self,
        project_id: str,
        count: int = 5,
        question_type: str = "mcq",
    ) -> list[dict]:
        chunks = self._active_chunks(project_id, limit=max(8, count * 3))
        if not chunks:
            raise ValueError("No ready active chunks found for this project")

        context_parts: list[str] = []
        chunk_ids: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            filename = (chunk.get("document_versions") or {}).get(
                "original_filename", "unknown"
            )
            context_parts.append(
                f"[Chunk {i} | {filename} | page {chunk.get('page_number')}]\n"
                f"{chunk['content']}"
            )
            chunk_ids.append(chunk["id"])

        context = "\n\n".join(context_parts)

        if question_type == "essay":
            shape = """
Return ONLY a JSON array. Each item:
{
  "question_text": "...",
  "model_answer": "...",
  "key_points": ["...", "..."],
  "max_score": 10
}
"""
        else:
            shape = """
Return ONLY a JSON array. Each item:
{
  "question_text": "...",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "exact option text",
  "explanation": "...",
  "max_score": 1
}
"""

        prompt = f"""
Bạn là hệ thống sinh quiz cho sinh viên.
Chỉ được dùng thông tin trong CONTEXT bên dưới.

Hãy tạo đúng {count} câu hỏi loại {question_type}.
- Không hỏi điều không có trong context.
- Câu hỏi phải kiểm tra hiểu biết, không chỉ chép nguyên câu.
- Tránh câu mơ hồ.
- Ngôn ngữ câu hỏi theo ngôn ngữ chủ yếu của context.
{shape}

CONTEXT:
{context}
""".strip()

        interaction = self.client.interactions.create(
            model=self.gemini_model,
            input=prompt,
        )
        parsed = self._parse_json(interaction.output_text)
        if not isinstance(parsed, list):
            raise ValueError("Gemini did not return a question array")

        inserted: list[dict] = []
        for item in parsed[:count]:
            row = {
                "project_id": project_id,
                "question_type": question_type,
                "question_text": str(item["question_text"]).strip(),
                "options": item.get("options"),
                "correct_answer": item.get("correct_answer"),
                "model_answer": item.get("model_answer") or item.get("explanation"),
                "key_points": item.get("key_points"),
                "rubric": None,
                "max_score": item.get("max_score", 1 if question_type == "mcq" else 10),
                "status": "active",
                "model_name": self.gemini_model,
                "prompt_version": "quiz-generate-v1",
            }
            result = self.supabase.table("questions").insert(row).execute()
            question = result.data[0]
            inserted.append(question)

            self.supabase.table("question_sources").insert(
                [
                    {"question_id": question["id"], "chunk_id": chunk_id}
                    for chunk_id in chunk_ids[: min(5, len(chunk_ids))]
                ]
            ).execute()

        return inserted

    def grade_essay(self, question: dict, user_answer: str) -> dict:
        prompt = f"""
Chấm câu trả lời của sinh viên chỉ dựa trên đáp án mẫu và key points.

Question:
{question['question_text']}

Model answer:
{question.get('model_answer') or ''}

Key points:
{json.dumps(question.get('key_points') or [], ensure_ascii=False)}

Student answer:
{user_answer}

Maximum score: {question['max_score']}

Return ONLY JSON:
{{
  "score": number,
  "feedback": "ngắn gọn, cụ thể",
  "is_correct": boolean
}}
""".strip()

        interaction = self.client.interactions.create(
            model=self.gemini_model,
            input=prompt,
        )
        result = self._parse_json(interaction.output_text)
        score = float(result.get("score", 0))
        score = max(0.0, min(float(question["max_score"]), score))
        return {
            "score": score,
            "feedback": str(result.get("feedback", "")),
            "is_correct": bool(result.get("is_correct", False)),
            "grading_method": "gemini-rubric",
        }

    def update_review_state(
        self,
        user_id: str,
        project_id: str,
        question_id: str,
        score_ratio: float,
    ) -> None:
        now = datetime.now(timezone.utc)
        existing = (
            self.supabase.table("review_states")
            .select("*")
            .eq("user_id", user_id)
            .eq("question_id", question_id)
            .maybe_single()
            .execute()
        )

        current = existing.data or {}
        repetitions = int(current.get("repetitions") or 0)
        interval = int(current.get("interval_days") or 1)
        ease = float(current.get("ease_factor") or 2.5)

        if score_ratio >= 0.8:
            repetitions += 1
            if repetitions == 1:
                interval = 1
            elif repetitions == 2:
                interval = 3
            else:
                interval = max(1, round(interval * ease))
            ease = min(3.0, ease + 0.05)
        else:
            repetitions = 0
            interval = 1
            ease = max(1.3, ease - 0.2)

        due_at = now.timestamp() + interval * 86400
        due_iso = datetime.fromtimestamp(due_at, tz=timezone.utc).isoformat()

        payload = {
            "user_id": user_id,
            "question_id": question_id,
            "project_id": project_id,
            "due_at": due_iso,
            "interval_days": interval,
            "repetitions": repetitions,
            "ease_factor": ease,
            "last_score": round(score_ratio, 2),
            "last_reviewed_at": now.isoformat(),
        }

        self.supabase.table("review_states").upsert(
            payload,
            on_conflict="user_id,question_id",
        ).execute()


@lru_cache
def get_quiz_service() -> QuizService:
    settings = get_settings()
    return QuizService(
        supabase=get_supabase_admin(),
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
    )
