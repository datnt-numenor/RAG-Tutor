from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.batch_size = max(1, int(settings.embedding_batch_size))
        self.model = _load_model(self.model_name)
        self.max_seq_length = int(getattr(self.model, "max_seq_length", 256) or 256)

    def count_tokens(self, text: str) -> int:
        tokenizer = self.model.tokenizer
        encoded = tokenizer(
            text,
            add_special_tokens=True,
            truncation=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        return len(encoded["input_ids"])

    def embed(self, text: str) -> list[float]:
        return self.model.encode(
            text,
            show_progress_bar=False,
        ).tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()
