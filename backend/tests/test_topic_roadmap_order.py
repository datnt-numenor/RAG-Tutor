from app.services.topic_roadmap_service import TopicRoadmapService


def make_service() -> TopicRoadmapService:
    return object.__new__(TopicRoadmapService)


def test_ordered_topics_respects_prerequisites():
    service = make_service()
    topics = [
        {"id": "advanced", "name": "Advanced", "is_core": False},
        {"id": "basic", "name": "Basic", "is_core": True},
        {"id": "middle", "name": "Middle", "is_core": True},
    ]
    prerequisites = [
        {
            "topic_id": "middle",
            "prerequisite_topic_id": "basic",
        },
        {
            "topic_id": "advanced",
            "prerequisite_topic_id": "middle",
        },
    ]

    ordered = service._ordered_topics(topics, prerequisites)
    assert [item["id"] for item in ordered] == [
        "basic",
        "middle",
        "advanced",
    ]


def test_ordered_topics_survives_cycle_without_dropping_topics():
    service = make_service()
    topics = [
        {"id": "a", "name": "A", "is_core": True},
        {"id": "b", "name": "B", "is_core": False},
    ]
    prerequisites = [
        {"topic_id": "a", "prerequisite_topic_id": "b"},
        {"topic_id": "b", "prerequisite_topic_id": "a"},
    ]

    ordered = service._ordered_topics(topics, prerequisites)
    assert {item["id"] for item in ordered} == {"a", "b"}
    assert len(ordered) == 2
