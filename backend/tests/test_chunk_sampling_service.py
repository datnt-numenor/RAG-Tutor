from app.services.chunk_sampling_service import (
    balanced_active_chunks,
    interleave_groups,
    sample_evenly,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.not_ = self

    def __getattr__(self, _name):
        return lambda *args, **kwargs: self

    def execute(self):
        return FakeResponse(self.data)


class FakeSupabase:
    def __init__(self, tables):
        self.tables = tables
        self.table_calls: list[str] = []

    def table(self, name):
        self.table_calls.append(name)
        return FakeQuery(self.tables[name])


def rows(count: int) -> list[dict]:
    return [{"chunk_index": index} for index in range(count)]


def test_sample_evenly_covers_beginning_middle_and_end():
    sampled = sample_evenly(rows(10), 4)
    indexes = [item["chunk_index"] for item in sampled]

    assert len(indexes) == 4
    assert indexes[0] == 0
    assert indexes[-1] == 9
    assert len(set(indexes)) == 4


def test_sample_evenly_returns_all_when_under_limit():
    source = rows(3)
    assert sample_evenly(source, 5) == source


def test_interleave_groups_round_robins_documents():
    result = interleave_groups(
        [
            [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}],
            [{"id": "b1"}, {"id": "b2"}],
            [{"id": "c1"}],
        ],
        6,
    )
    assert [item["id"] for item in result] == [
        "a1",
        "b1",
        "c1",
        "a2",
        "b2",
        "a3",
    ]


def test_interleave_respects_limit():
    result = interleave_groups(
        [
            [{"id": "a1"}, {"id": "a2"}],
            [{"id": "b1"}, {"id": "b2"}],
        ],
        3,
    )
    assert [item["id"] for item in result] == ["a1", "b1", "a2"]


def test_balanced_active_chunks_batch_loads_all_versions_once():
    db = FakeSupabase({
        "documents": [
            {
                "id": "doc-a",
                "active_version_id": "version-a",
                "status": "active",
                "document_versions": {
                    "id": "version-a",
                    "original_filename": "a.pdf",
                    "status": "ready",
                },
            },
            {
                "id": "doc-b",
                "active_version_id": "version-b",
                "status": "active",
                "document_versions": {
                    "id": "version-b",
                    "original_filename": "b.pdf",
                    "status": "ready",
                },
            },
        ],
        "chunks": [
            {
                "id": "a1",
                "document_id": "doc-a",
                "document_version_id": "version-a",
                "chunk_index": 0,
                "content": "a",
            },
            {
                "id": "b1",
                "document_id": "doc-b",
                "document_version_id": "version-b",
                "chunk_index": 0,
                "content": "b",
            },
        ],
    })

    result = balanced_active_chunks(db, "project", 2)

    assert db.table_calls == ["documents", "chunks"]
    assert [row["id"] for row in result] == ["a1", "b1"]
    assert result[0]["document_versions"]["original_filename"] == "a.pdf"
    assert result[1]["document_versions"]["original_filename"] == "b.pdf"
