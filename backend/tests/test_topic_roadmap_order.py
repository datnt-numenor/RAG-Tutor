from app.services.topic_roadmap_service import TopicRoadmapService


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTopicQuery:
    def __init__(self, table_name: str, database):
        self.table_name = table_name
        self.database = database

    def __getattr__(self, _name):
        return lambda *args, **kwargs: self

    def execute(self):
        return FakeResponse([])

    def insert(self, rows):
        self.database.insert_calls.append((self.table_name, rows))
        if self.table_name == "topics":
            self._inserted = [
                {**row, "id": f"topic-{index}"}
                for index, row in enumerate(rows, start=1)
            ]
        else:
            self._inserted = rows
        return self

    def delete(self):
        return self

    @property
    def data(self):
        return getattr(self, "_inserted", [])


class FakeTopicDatabase:
    def __init__(self):
        self.insert_calls: list[tuple[str, list[dict]]] = []

    def table(self, name):
        query = FakeTopicQuery(name, self)

        original_execute = query.execute

        def execute():
            if hasattr(query, "_inserted"):
                return FakeResponse(query._inserted)
            return original_execute()

        query.execute = execute
        return query


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


def test_generate_topics_inserts_topic_rows_in_one_batch(monkeypatch):
    database = FakeTopicDatabase()
    provider = type("Provider", (), {
        "model_name": "test-model",
        "generate": lambda self, prompt, json_mode: (
            '{"topics": ['
            '{"name": "Basics", "source_chunk_numbers": [1], '
            '"prerequisites": []},'
            '{"name": "Advanced", "source_chunk_numbers": [2], '
            '"prerequisites": ["Basics"]}'
            ']}'
        ),
    })()
    service = TopicRoadmapService(database, provider)
    monkeypatch.setattr(service, "_active_chunks", lambda project_id: [
        {"id": "chunk-1", "content": "one", "page_number": 1},
        {"id": "chunk-2", "content": "two", "page_number": 2},
    ])
    monkeypatch.setattr(
        service,
        "get_roadmap",
        lambda project_id: {"topics": []},
    )

    service.generate_topics("project")

    topic_inserts = [
        rows for table, rows in database.insert_calls if table == "topics"
    ]
    assert len(topic_inserts) == 1
    assert [row["name"] for row in topic_inserts[0]] == [
        "Basics",
        "Advanced",
    ]
