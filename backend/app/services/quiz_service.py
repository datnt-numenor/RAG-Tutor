from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from datetime import datetime, timezone
from functools import lru_cache

from app.core.database import get_supabase_admin
from app.services.ai_provider import TextGenerationProvider, get_aux_text_provider
from app.services.chunk_sampling_service import balanced_active_chunks


class QuizService:
    DEDUP_THRESHOLD = 0.90

    def __init__(self, supabase, provider: TextGenerationProvider):
        self.supabase = supabase
        self.provider = provider
        self.gemini_model = provider.model_name

    def _active_chunks(self, project_id: str, limit: int = 12) -> list[dict]:
        return balanced_active_chunks(
            self.supabase,
            project_id,
            limit,
        )

    def _parse_json(self, text: str):
        clean = text.strip()
        clean = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", clean, flags=re.I)
        clean = re.sub(r"\s*\x60\x60\x60\s*$", "", clean)
        return json.loads(clean)

    @staticmethod
    def _normalize_question(text: str) -> str:
        return " ".join(
            re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        )

    @classmethod
    def _is_duplicate_text(cls, a: str, b: str) -> bool:
        a_norm = cls._normalize_question(a)
        b_norm = cls._normalize_question(b)
        if not a_norm or not b_norm:
            return False

        sequence_ratio = SequenceMatcher(None, a_norm, b_norm).ratio()
        a_tokens = set(a_norm.split())
        b_tokens = set(b_norm.split())
        union = a_tokens | b_tokens
        jaccard = len(a_tokens & b_tokens) / len(union) if union else 0.0

        return sequence_ratio >= 0.88 or jaccard >= 0.82

    def _existing_question_texts(self, project_id: str) -> list[str]:
        existing = (
            self.supabase.table("questions")
            .select("question_text")
            .eq("project_id", project_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        ).data

        return [
            str(row.get("question_text") or "").strip()
            for row in existing
            if str(row.get("question_text") or "").strip()
        ]

    def _topic_lookup(self, project_id: str) -> tuple[dict[str, str], list[str]]:
        topics = (
            self.supabase.table("topics")
            .select("id, name")
            .eq("project_id", project_id)
            .execute()
        ).data

        by_name = {
            str(topic["name"]).strip().casefold(): topic["id"]
            for topic in topics
            if topic.get("name")
        }
        names = [str(topic["name"]) for topic in topics if topic.get("name")]
        return by_name, names

    def generate_questions(
        self,
        project_id: str,
        count: int = 5,
        question_type: str = "mcq",
    ) -> list[dict]:
        chunks = self._active_chunks(project_id, limit=min(12, max(8, count * 2)))
        if not chunks:
            raise ValueError("No ready active chunks found for this project")

        context_parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            filename = (chunk.get("document_versions") or {}).get(
                "original_filename", "unknown"
            )
            content = str(chunk.get("content") or "").strip()
            if len(content) > 1200:
                content = content[:1200]
            context_parts.append(
                f"[Chunk {i} | {filename} | page {chunk.get('page_number')}]\n"
                f"{content}"
            )

        context = "\n\n".join(context_parts)
        if len(context) > 14_000:
            context = context[:14_000]
        topic_lookup, topic_names = self._topic_lookup(project_id)
        candidate_count = min(12, max(count + 2, count * 2))

        common_fields = """
Every item MUST include:
  "source_chunk_numbers": [1, 2],
  "topic_name": "exact topic name from TOPICS or null"

source_chunk_numbers must only contain chunks that directly support the question and answer.
"""

        if question_type == "essay":
            shape = f"""
Return ONLY a JSON array with up to {candidate_count} candidate items.
Each item:
{{
  "question_text": "...",
  "model_answer": "...",
  "key_points": ["...", "..."],
  "max_score": 10,
  "source_chunk_numbers": [1, 2],
  "topic_name": null
}}
{common_fields}
"""
        else:
            shape = f"""
Return ONLY a JSON array with up to {candidate_count} candidate items.
Each item:
{{
  "question_text": "...",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "exact option text",
  "explanation": "...",
  "max_score": 1,
  "source_chunk_numbers": [1, 2],
  "topic_name": null
}}
{common_fields}
"""

        topics_text = (
            "\n".join(f"- {name}" for name in topic_names)
            if topic_names
            else "(No roadmap topics generated yet)"
        )

        prompt = f"""
Bạn là hệ thống sinh quiz cho sinh viên.
Chỉ được dùng thông tin trong CONTEXT bên dưới.

Mục tiêu cuối cùng: giữ tối đa {count} câu hỏi loại {question_type}
sau khi hệ thống loại câu trùng nghĩa.
- Không hỏi điều không có trong context.
- Câu hỏi phải kiểm tra hiểu biết, không chỉ chép nguyên câu.
- Tránh câu mơ hồ.
- Các candidate phải khác nhau rõ rệt về ý nghĩa.
- Ngôn ngữ câu hỏi theo ngôn ngữ chủ yếu của context.
{shape}

TOPICS:
{topics_text}

CONTEXT:
{context}
""".strip()

        parsed = self._parse_json(self.provider.generate(prompt))
        if not isinstance(parsed, list):
            raise ValueError("AI provider did not return a question array")

        candidates: list[dict] = []
        for item in parsed[:candidate_count]:
            question_text = str(item.get("question_text") or "").strip()
            if not question_text:
                continue

            valid_sources: list[int] = []
            for value in item.get("source_chunk_numbers") or []:
                try:
                    number = int(value)
                except (TypeError, ValueError):
                    continue
                if 1 <= number <= len(chunks) and number not in valid_sources:
                    valid_sources.append(number)

            if not valid_sources:
                continue

            candidates.append(
                {
                    "raw": item,
                    "question_text": question_text,
                    "source_numbers": valid_sources[:5],
                }
            )

        if not candidates:
            raise ValueError("No generated question had valid source chunks")

        existing_questions = self._existing_question_texts(project_id)
        accepted_questions = list(existing_questions)

        inserted: list[dict] = []
        for candidate in candidates:
            question_text = candidate["question_text"]
            is_duplicate = any(
                self._is_duplicate_text(question_text, previous)
                for previous in accepted_questions
            )
            if is_duplicate:
                continue

            item = candidate["raw"]
            topic_name = str(item.get("topic_name") or "").strip()
            topic_id = topic_lookup.get(topic_name.casefold()) if topic_name else None

            row = {
                "project_id": project_id,
                "topic_id": topic_id,
                "question_type": question_type,
                "question_text": candidate["question_text"],
                "options": item.get("options"),
                "correct_answer": item.get("correct_answer"),
                "model_answer": item.get("model_answer") or item.get("explanation"),
                "key_points": item.get("key_points"),
                "rubric": item.get("rubric"),
                "max_score": item.get(
                    "max_score",
                    1 if question_type == "mcq" else 10,
                ),
                "question_embedding": None,
                "status": "active",
                "model_name": self.gemini_model,
                "prompt_version": "quiz-generate-v2",
            }
            result = self.supabase.table("questions").insert(row).execute()
            question = result.data[0]

            source_rows = [
                {
                    "question_id": question["id"],
                    "chunk_id": chunks[number - 1]["id"],
                }
                for number in candidate["source_numbers"]
            ]
            self.supabase.table("question_sources").insert(source_rows).execute()

            inserted.append(question)
            accepted_questions.append(question_text)

            if len(inserted) >= count:
                break

        if not inserted:
            raise ValueError(
                "All generated questions were removed as semantic duplicates"
            )

        return inserted

    def grade_essay(self, question: dict, user_answer: str) -> dict:
        source_rows = (
            self.supabase.table("question_sources")
            .select("chunks(content, page_number, document_versions(original_filename))")
            .eq("question_id", question["id"])
            .execute()
        ).data

        evidence_parts: list[str] = []
        for row in source_rows:
            chunk = row.get("chunks") or {}
            filename = (chunk.get("document_versions") or {}).get(
                "original_filename",
                "unknown",
            )
            evidence_parts.append(
                f"[{filename} | page {chunk.get('page_number')}]\n"
                f"{chunk.get('content') or ''}"
            )
        evidence = "\n\n".join(evidence_parts)

        prompt = f"""
Chấm câu trả lời của sinh viên chỉ dựa trên rubric/key points và evidence nguồn.

Question:
{question['question_text']}

Model answer:
{question.get('model_answer') or ''}

Key points:
{json.dumps(question.get('key_points') or [], ensure_ascii=False)}

Rubric:
{json.dumps(question.get('rubric') or {}, ensure_ascii=False)}

Evidence:
{evidence}

Student answer:
{user_answer}

Maximum score: {question['max_score']}

Return ONLY JSON:
{{
  "score": number,
  "feedback": "ngắn gọn, cụ thể; nói rõ ý đúng và ý còn thiếu",
  "is_correct": boolean
}}
""".strip()

        result = self._parse_json(self.provider.generate(prompt, json_mode=True))
        score = float(result.get("score", 0))
        score = max(0.0, min(float(question["max_score"]), score))
        return {
            "score": score,
            "feedback": str(result.get("feedback", "")),
            "is_correct": bool(result.get("is_correct", False)),
            "grading_method": "ai-rubric-evidence-v3",
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
    return QuizService(
        supabase=get_supabase_admin(),
        provider=get_aux_text_provider(),
    )
