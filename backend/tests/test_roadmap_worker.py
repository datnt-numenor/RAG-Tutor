from app.workers.roadmap_worker import generate_topic_roadmap


def test_roadmap_worker_returns_compact_result(monkeypatch) -> None:
    class FakeService:
        def generate_topics(self, project_id: str) -> list[dict]:
            assert project_id == "project-1"
            return [{"id": "topic-1"}, {"id": "topic-2"}]

    monkeypatch.setattr(
        "app.workers.roadmap_worker.get_topic_roadmap_service",
        lambda: FakeService(),
    )

    result = generate_topic_roadmap.run("project-1")

    assert result == {"project_id": "project-1", "topic_count": 2}
