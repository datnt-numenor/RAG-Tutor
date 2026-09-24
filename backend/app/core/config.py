from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key: str = "change-me"
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # ── Gemini ────────────────────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"

    # ── Embedding ─────────────────────────────────────────────────────────────
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
