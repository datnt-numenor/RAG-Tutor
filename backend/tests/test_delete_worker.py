from types import SimpleNamespace

from app.workers.delete_worker import (
    _remove_orphaned_topics,
    _retire_orphaned_questions,
)


class FakeQuery:
    def __init__(self, db, table: str):
        self.db = db
        self.table = table
        self.operation = "select"
        self.values = None

    def select(self, *args, **kwargs):
        return self

    def update(self, values):
        self.operation = "update"
        self.values = values
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def in_(self, column, values):
        self.db.filters.append((self.table, self.operation, column, values))
        return self

    def execute(self):
        self.db.executions.append((self.table, self.operation, self.values))
        return SimpleNamespace(data=self.db.rows.get(self.table, []))


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.executions = []

    def table(self, name):
        return FakeQuery(self, name)


def test_orphan_cleanup_uses_batched_queries() -> None:
    db = FakeDatabase({
        "question_sources": [{"question_id": "q2"}],
        "topic_sources": [{"topic_id": "t2"}],
    })

    _retire_orphaned_questions(db, {"q1", "q2", "q3"})
    _remove_orphaned_topics(db, {"t1", "t2", "t3"})

    assert ("questions", "update", "id", ["q1", "q3"]) in db.filters
    assert ("topics", "delete", "id", ["t1", "t3"]) in db.filters
    assert len(db.executions) == 4
