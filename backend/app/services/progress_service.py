from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.database import get_supabase_admin


class ProgressService:
    def __init__(self, supabase=None):
        self.supabase = supabase or get_supabase_admin()

    def _user_timezone(self, user_id: str) -> ZoneInfo:
        user = (
            self.supabase.table("users")
            .select("timezone")
            .eq("id", user_id)
            .single()
            .execute()
        ).data
        try:
            return ZoneInfo(user.get("timezone") or "UTC")
        except Exception:
            return ZoneInfo("UTC")

    def _local_date_for(
        self,
        user_id: str,
        occurred_at: datetime | None = None,
    ) -> date:
        tz = self._user_timezone(user_id)
        value = occurred_at or datetime.now(timezone.utc)
        return value.astimezone(tz).date()

    def _utc_bounds(
        self,
        user_id: str,
        snapshot_date: date,
    ) -> tuple[str, str]:
        tz = self._user_timezone(user_id)
        local_start = datetime.combine(snapshot_date, time.min, tzinfo=tz)
        local_end = local_start + timedelta(days=1)
        return (
            local_start.astimezone(timezone.utc).isoformat(),
            local_end.astimezone(timezone.utc).isoformat(),
        )

    def record_event(
        self,
        *,
        user_id: str,
        project_id: str,
        event_type: str,
        source_id: str | None = None,
        topic_id: str | None = None,
        duration_seconds: int | None = None,
        metadata: dict | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
        rebuild: bool = True,
    ) -> dict | None:
        event_time = occurred_at or datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "project_id": project_id,
            "topic_id": topic_id,
            "event_type": event_type,
            "duration_seconds": duration_seconds,
            "occurred_at": event_time.isoformat(),
            "source_id": source_id,
            "idempotency_key": idempotency_key,
            "metadata": metadata,
        }

        try:
            result = self.supabase.table("study_events").insert(payload).execute()
            event = result.data[0] if result.data else None
        except Exception:
            # Idempotent repeat: if the key already exists, do not double count.
            if idempotency_key:
                existing = (
                    self.supabase.table("study_events")
                    .select("*")
                    .eq("idempotency_key", idempotency_key)
                    .maybe_single()
                    .execute()
                )
                event = existing.data
            else:
                raise

        if rebuild:
            snapshot_date = self._local_date_for(user_id, event_time)
            self.rebuild_snapshot(
                user_id=user_id,
                project_id=project_id,
                snapshot_date=snapshot_date,
            )

        return event

    def remove_event(
        self,
        *,
        user_id: str,
        idempotency_key: str,
    ) -> None:
        existing = (
            self.supabase.table("study_events")
            .select("project_id, occurred_at")
            .eq("user_id", user_id)
            .eq("idempotency_key", idempotency_key)
            .maybe_single()
            .execute()
        )
        if not existing.data:
            return

        occurred_at = datetime.fromisoformat(
            existing.data["occurred_at"].replace("Z", "+00:00")
        )
        project_id = existing.data["project_id"]

        self.supabase.table("study_events").delete().eq(
            "user_id", user_id
        ).eq(
            "idempotency_key", idempotency_key
        ).execute()

        self.rebuild_snapshot(
            user_id=user_id,
            project_id=project_id,
            snapshot_date=self._local_date_for(user_id, occurred_at),
        )

    def rebuild_snapshot(
        self,
        *,
        user_id: str,
        project_id: str,
        snapshot_date: date,
    ) -> dict:
        start_utc, end_utc = self._utc_bounds(user_id, snapshot_date)

        attempts = (
            self.supabase.table("quiz_attempts")
            .select(
                "score, max_score_snapshot, is_correct, question_id, "
                "questions(topic_id)"
            )
            .eq("user_id", user_id)
            .eq("project_id", project_id)
            .eq("status", "graded")
            .gte("graded_at", start_utc)
            .lt("graded_at", end_utc)
            .execute()
        ).data

        attempted = len(attempts)
        correct = sum(1 for row in attempts if row.get("is_correct") is True)

        ratios: list[float] = []
        topic_ids: set[str] = set()
        for row in attempts:
            max_score = float(row.get("max_score_snapshot") or 0)
            if max_score > 0:
                ratios.append(float(row.get("score") or 0) / max_score * 100)

            question = row.get("questions") or {}
            topic_id = question.get("topic_id")
            if topic_id:
                topic_ids.add(topic_id)

        events = (
            self.supabase.table("study_events")
            .select("duration_seconds")
            .eq("user_id", user_id)
            .eq("project_id", project_id)
            .gte("occurred_at", start_utc)
            .lt("occurred_at", end_utc)
            .execute()
        ).data
        duration_seconds = sum(
            max(0, int(row.get("duration_seconds") or 0))
            for row in events
        )

        payload = {
            "user_id": user_id,
            "project_id": project_id,
            "snapshot_date": snapshot_date.isoformat(),
            "questions_attempted": attempted,
            "questions_correct": correct,
            "avg_score": round(sum(ratios) / len(ratios), 2) if ratios else 0,
            "topics_covered": len(topic_ids),
            "study_minutes": round(duration_seconds / 60),
        }

        result = self.supabase.table("progress_snapshots").upsert(
            payload,
            on_conflict="user_id,project_id,snapshot_date",
        ).execute()
        return result.data[0]

    def rebuild_range(
        self,
        *,
        user_id: str,
        project_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        output = []
        cursor = start_date
        while cursor <= end_date:
            output.append(
                self.rebuild_snapshot(
                    user_id=user_id,
                    project_id=project_id,
                    snapshot_date=cursor,
                )
            )
            cursor += timedelta(days=1)
        return output


@lru_cache
def get_progress_service() -> ProgressService:
    return ProgressService()
