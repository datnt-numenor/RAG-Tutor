from app.services.quiz_service import QuizService


class FakeProvider:
    model_name = "test-model"

    def generate(self, prompt: str) -> str:
        return """[
          {
            "question_text": "Question one?",
            "options": ["A", "B"],
            "correct_answer": "A",
            "source_chunk_numbers": [1],
            "topic_name": null
          },
          {
            "question_text": "Question two?",
            "options": ["C", "D"],
            "correct_answer": "C",
            "source_chunk_numbers": [2],
            "topic_name": null
          }
        ]"""


class InsertQuery:
    def __init__(self, db, table: str):
        self.db = db
        self.table = table
        self.rows = []

    def insert(self, rows):
        self.rows = rows
        return self

    def execute(self):
        self.db.inserts.append((self.table, self.rows))
        if self.table == "questions":
            return type("Response", (), {"data": [
                {**row, "id": f"q{index}"}
                for index, row in enumerate(self.rows, start=1)
            ]})()
        return type("Response", (), {"data": self.rows})()


class InsertDatabase:
    def __init__(self):
        self.inserts = []

    def table(self, name: str):
        return InsertQuery(self, name)


def test_duplicate_text_detects_near_duplicate_questions():
    assert QuizService._is_duplicate_text(
        "TCP khác UDP như thế nào?",
        "TCP khác với UDP như thế nào?",
    )


def test_duplicate_text_keeps_different_questions():
    assert not QuizService._is_duplicate_text(
        "TCP khác UDP như thế nào?",
        "Địa chỉ IP dùng để làm gì trong mạng?",
    )


def test_question_generation_batches_question_and_source_inserts(monkeypatch):
    db = InsertDatabase()
    service = QuizService(db, FakeProvider())
    monkeypatch.setattr(service, "_active_chunks", lambda *args, **kwargs: [
        {"id": "c1", "content": "First source", "page_number": 1},
        {"id": "c2", "content": "Second source", "page_number": 2},
    ])
    monkeypatch.setattr(service, "_topic_lookup", lambda project_id: ({}, []))
    monkeypatch.setattr(service, "_existing_question_texts", lambda project_id: [])

    result = service.generate_questions("project-1", count=2)

    assert [row["id"] for row in result] == ["q1", "q2"]
    assert [table for table, _ in db.inserts] == [
        "questions",
        "question_sources",
    ]
