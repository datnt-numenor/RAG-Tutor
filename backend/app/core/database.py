from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from postgrest._sync.request_builder import SyncMaybeSingleRequestBuilder
from supabase import Client, create_client

from app.core.config import get_settings


_prisma_client: Any | None = None


@dataclass(frozen=True)
class _EmptyMaybeSingleResponse:
    """Keep the response shape stable when PostgREST finds no matching row."""

    data: None = None
    count: int | None = None


def _normalize_maybe_single_response(response: Any) -> Any:
    """
    Normalize postgrest-py 2.31's zero-row result.

    ``SyncMaybeSingleRequestBuilder.execute`` now returns ``None`` when a
    maybe-single query matches no rows. The application historically consumes
    Supabase responses through ``response.data`` in authorization and
    not-found branches, so normalizing only the empty result preserves that
    response contract without changing successful single-row responses.
    """
    return response if response is not None else _EmptyMaybeSingleResponse()


def _install_maybe_single_compatibility() -> None:
    """Install the response normalization once for all sync Supabase clients."""
    current_execute = SyncMaybeSingleRequestBuilder.execute
    if getattr(current_execute, "_ragtutor_normalizes_empty", False):
        return

    def execute_with_empty_response(self: Any) -> Any:
        return _normalize_maybe_single_response(current_execute(self))

    execute_with_empty_response._ragtutor_normalizes_empty = True  # type: ignore[attr-defined]
    SyncMaybeSingleRequestBuilder.execute = execute_with_empty_response  # type: ignore[method-assign]


_install_maybe_single_compatibility()


def get_prisma() -> Any:
    """
    Return the optional Prisma runtime client.

    The production vertical slice uses Supabase directly, so importing backend
    modules must not require a generated Prisma client. Prisma is imported and
    instantiated only when this function is actually called.
    """
    global _prisma_client

    if _prisma_client is not None:
        return _prisma_client

    try:
        from prisma import Prisma
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError(
            "Prisma client is unavailable. Run "
            "'python -m prisma generate --schema=prisma/schema.prisma' "
            "before using Prisma runtime features."
        ) from exc

    try:
        _prisma_client = Prisma()
    except RuntimeError as exc:
        raise RuntimeError(
            "Prisma client has not been generated. Run "
            "'python -m prisma generate --schema=prisma/schema.prisma' "
            "before using Prisma runtime features."
        ) from exc

    return _prisma_client


async def connect_db() -> None:
    await get_prisma().connect()


async def disconnect_db() -> None:
    global _prisma_client

    if _prisma_client is None:
        return

    if _prisma_client.is_connected():
        await _prisma_client.disconnect()


@lru_cache
def get_supabase_admin() -> Client:
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key,
    )


@lru_cache
def get_supabase_anon() -> Client:
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
