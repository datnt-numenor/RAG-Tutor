from app.services.embedding_service import EmbeddingService


class _Encoded:
    def __init__(self, rows):
        self.rows = rows

    def tolist(self):
        return self.rows


class _FakeModel:
    def __init__(self):
        self.kwargs = None

    def encode(self, texts, **kwargs):
        self.kwargs = kwargs
        rows = [[float(index)] for index, _ in enumerate(texts)]
        return _Encoded(rows)


def test_embed_many_uses_bounded_batch_size_without_progress_bar():
    service = object.__new__(EmbeddingService)
    service.batch_size = 16
    service.model = _FakeModel()

    result = service.embed_many(["a", "b", "c"])

    assert result == [[0.0], [1.0], [2.0]]
    assert service.model.kwargs["batch_size"] == 16
    assert service.model.kwargs["show_progress_bar"] is False
    assert service.model.kwargs["convert_to_numpy"] is True
