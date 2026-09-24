from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from google import genai

from app.core.config import get_settings
from app.core.database import get_supabase_admin


class TopicRoadmapService:
    def __init__(self, supabase, gemini_api_key: str, gemini_model: str):
        self.supabase = supabase
        self.model = gemini_model
        self.client = genai.Client(api_key=gemini_api_key)

    def _parse_json(self, text: str):
        clean = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", text.strip(), flags=re.I)
        clean = re.sub(r"\s*\x60\x60\x60\s*$", "", clean)
        return json.loads(clean)

    def _active_chunks(self, project_id: str, limit: int = 24) -> list[dict]:
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
        rows = []
        for row in response.data or []:
            doc = row.get("documents") or {}
            if doc.get("active_version_id") == row.get("document_version_id"):
                rows.append(row)
        return rows

    def generate_topics(self, project_id: str) -> list[dict]:
        chunks = self._active_chunks(project_id)
        if not chunks:
            raise ValueError("No ready active chunks found for this project")

        parts = []
        for i, chunk in enumerate(chunks, start=1):
            filename = (chunk.get("document_versions") or {}).get("original_filename", "unknown")
            excerpt = chunk["content"][:1800]
            parts.append(
                f"[Chunk {i} | {filename} | page {chunk.get('page_number')}]\n{excerpt}"
            )
        context = "\n\n".join(parts)

        prompt = f"""
Phân tích tài liệu học tập và trích xuất roadmap chủ đề.
Chỉ dùng CONTEXT.

Return ONLY JSON:
{{
  "topics": [
    {{
      "name": "...",
      "description": "...",
      "difficulty": "basic|intermediate|advanced",
      "bloom_level": "remember|understand|apply|analyze",
      "is_core": true,
      "source_chunk_numbers": [1,2],
      "prerequisites": ["tên topic khác"]
    }}
  ]
}}

Yêu cầu:
- Tối đa 12 topics, không trùng nghĩa.
- Bao phủ toàn bộ kiến thức chính.
- prerequisite chỉ tham chiếu topic có trong cùng output.
- Không bỏ topic nền tảng.
- source_chunk_numbers chỉ dùng các chunk thực sự chứa bằng chứng.

CONTEXT:
{context}
""".strip()

        interaction = self.client.interactions.create(model=self.model, input=prompt)
        parsed = self._parse_json(interaction.output_text)
        topics = parsed.get("topics", [])
        if not isinstance(topics, list) or not topics:
            raise ValueError("Gemini did not return topics")

        self.supabase.table("topics").delete().eq("project_id", project_id).execute()

        inserted = []
        by_name: dict[str, dict] = {}
        source_map: dict[str, list[int]] = {}
        prereq_map: dict[str, list[str]] = {}

        for item in topics[:12]:
            name = str(item["name"]).strip()
            row = {
                "project_id": project_id,
                "name": name,
                "description": item.get("description"),
                "difficulty": item.get("difficulty"),
                "bloom_level": item.get("bloom_level"),
                "is_core": bool(item.get("is_core", False)),
                "model_name": self.model,
                "prompt_version": "topics-v1",
            }
            created = self.supabase.table("topics").insert(row).execute().data[0]
            inserted.append(created)
            by_name[name.casefold()] = created
            source_map[created["id"]] = [
                int(n) for n in item.get("source_chunk_numbers", [])
                if isinstance(n, int) or (isinstance(n, str) and n.isdigit())
            ]
            prereq_map[created["id"]] = [str(x).strip() for x in item.get("prerequisites", [])]

        source_rows = []
        for topic in inserted:
            for n in source_map.get(topic["id"], []):
                if 1 <= n <= len(chunks):
                    source_rows.append({
                        "topic_id": topic["id"],
                        "chunk_id": chunks[n - 1]["id"],
                        "relevance": 1.0,
                    })
        if source_rows:
            self.supabase.table("topic_sources").insert(source_rows).execute()

        prereq_rows = []
        for topic in inserted:
            for prereq_name in prereq_map.get(topic["id"], []):
                prereq = by_name.get(prereq_name.casefold())
                if prereq and prereq["id"] != topic["id"]:
                    prereq_rows.append({
                        "topic_id": topic["id"],
                        "prerequisite_topic_id": prereq["id"],
                        "strength": 1.0,
                    })
        if prereq_rows:
            self.supabase.table("topic_prerequisites").insert(prereq_rows).execute()

        return self.get_roadmap(project_id)["topics"]

    def _ordered_topics(self, topics: list[dict], prerequisites: list[dict]) -> list[dict]:
        by_id = {t["id"]: t for t in topics}
        indegree = {topic_id: 0 for topic_id in by_id}
        edges: dict[str, list[str]] = defaultdict(list)

        for rel in prerequisites:
            topic_id = rel["topic_id"]
            prereq_id = rel["prerequisite_topic_id"]
            if topic_id in by_id and prereq_id in by_id:
                edges[prereq_id].append(topic_id)
                indegree[topic_id] += 1

        queue = deque(
            sorted(
                [topic_id for topic_id, deg in indegree.items() if deg == 0],
                key=lambda x: (not by_id[x].get("is_core", False), by_id[x]["name"].casefold()),
            )
        )
        ordered_ids = []
        while queue:
            current = queue.popleft()
            ordered_ids.append(current)
            for nxt in edges[current]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        for topic_id in by_id:
            if topic_id not in ordered_ids:
                ordered_ids.append(topic_id)

        return [by_id[topic_id] for topic_id in ordered_ids]

    def get_roadmap(self, project_id: str) -> dict:
        project = self.supabase.table("projects").select(
            "id, name, target_score, exam_date, weekly_study_minutes"
        ).eq("id", project_id).single().execute().data

        topics = self.supabase.table("topics").select("*").eq("project_id", project_id).execute().data
        prereqs = []
        if topics:
            ids = [t["id"] for t in topics]
            prereqs = (
                self.supabase.table("topic_prerequisites")
                .select("*")
                .in_("topic_id", ids)
                .execute()
            ).data

        ordered = self._ordered_topics(topics, prereqs)
        prereq_names: dict[str, list[str]] = defaultdict(list)
        by_id = {t["id"]: t for t in topics}
        for rel in prereqs:
            prereq = by_id.get(rel["prerequisite_topic_id"])
            if prereq:
                prereq_names[rel["topic_id"]].append(prereq["name"])

        for index, topic in enumerate(ordered, start=1):
            topic["order"] = index
            topic["prerequisites"] = prereq_names.get(topic["id"], [])

        return {"project": project, "topics": ordered}

    def generate_schedule(self, project_id: str, user_id: str) -> list[dict]:
        roadmap = self.get_roadmap(project_id)
        project = roadmap["project"]
        topics = roadmap["topics"]
        if not topics:
            raise ValueError("Generate roadmap topics first")

        target = float(project.get("target_score") or 80)
        weekly = int(project.get("weekly_study_minutes") or 300)

        user = (
            self.supabase.table("users")
            .select("timezone")
            .eq("id", user_id)
            .single()
            .execute()
        ).data
        try:
            user_tz = ZoneInfo(user.get("timezone") or "UTC")
        except Exception:
            user_tz = ZoneInfo("UTC")

        today = datetime.now(user_tz).date()
        exam_date_raw = project.get("exam_date")
        if exam_date_raw:
            exam = date.fromisoformat(str(exam_date_raw))
        else:
            exam = today + timedelta(days=30)
        available_days = max(1, (exam - today).days)
        depth_multiplier = 0.85 if target < 70 else 1.0 if target < 85 else 1.2 if target < 95 else 1.35
        daily_budget = max(30, min(180, round(weekly / 5)))

        difficulty_weight = {"basic": 0.8, "intermediate": 1.0, "advanced": 1.25}
        bloom_weight = {"remember": 0.8, "understand": 1.0, "apply": 1.15, "analyze": 1.3}

        self.supabase.table("schedules").delete().eq(
            "project_id", project_id
        ).eq("source", "ai_suggested").eq(
            "suggestion_status", "suggested"
        ).execute()

        rows = []
        cursor_day = today + timedelta(days=1)

        for topic in topics:
            base = daily_budget * difficulty_weight.get(topic.get("difficulty"), 1.0)
            base *= bloom_weight.get(topic.get("bloom_level"), 1.0)
            minutes = max(30, min(180, round(base * depth_multiplier)))

            if cursor_day > exam:
                cursor_day = exam

            local_start = datetime.combine(cursor_day, time(hour=19), tzinfo=user_tz)
            start_dt = local_start.astimezone(timezone.utc)
            end_dt = start_dt + timedelta(minutes=minutes)

            rows.append({
                "project_id": project_id,
                "created_by": user_id,
                "topic_id": topic["id"],
                "title": f"Học: {topic['name']}",
                "description": (
                    f"{topic.get('description') or ''}\n"
                    f"Difficulty: {topic.get('difficulty') or 'n/a'} · "
                    f"Bloom: {topic.get('bloom_level') or 'n/a'} · "
                    f"Target score: {target:g}"
                ).strip(),
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "event_type": "study",
                "source": "ai_suggested",
                "suggestion_status": "suggested",
            })
            cursor_day += timedelta(days=max(1, available_days // max(1, len(topics))))

        deadline_start = datetime.combine(
            exam,
            time(hour=9),
            tzinfo=user_tz,
        ).astimezone(timezone.utc)
        rows.append({
            "project_id": project_id,
            "created_by": user_id,
            "topic_id": None,
            "title": "Exam / target deadline",
            "description": f"Target score: {target:g}",
            "start_time": deadline_start.isoformat(),
            "end_time": None,
            "event_type": "deadline",
            "source": "ai_suggested",
            "suggestion_status": "suggested",
        })

        return self.supabase.table("schedules").insert(rows).execute().data


@lru_cache
def get_topic_roadmap_service() -> TopicRoadmapService:
    settings = get_settings()
    return TopicRoadmapService(
        supabase=get_supabase_admin(),
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
    )
