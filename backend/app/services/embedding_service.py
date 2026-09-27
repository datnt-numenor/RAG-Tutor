from __future__ import annotations

import ctypes
import gc
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def _trim_process_memory() -> None:
    """Best-effort release of freed CPU memory back to the OS."""
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.batch_size = max(1, int(settings.embedding_batch_size))
        self.model: SentenceTransformer | None = _load_model(self.model_name)
        self.max_seq_length = int(getattr(self.model, "max_seq_length", 256) or 256)

    def _require_model(self) -> SentenceTransformer:
        if self.model is None:
            raise RuntimeError("Embedding model has been released")
        return self.model

    def count_tokens(self, text: str) -> int:
        tokenizer = self._require_model().tokenizer
        encoded = tokenizer(
            text,
            add_special_tokens=True,
            truncation=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        return len(encoded["input_ids"])

    def embed(self, text: str) -> list[float]:
        return self._require_model().encode(
            text,
            show_progress_bar=False,
        ).tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self._require_model().encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def close(self) -> None:
        """Release model memory for low-memory background workers."""
        self.model = None
        _load_model.cache_clear()
        _trim_process_memory()
