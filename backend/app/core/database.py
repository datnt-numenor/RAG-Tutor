from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.core.config import get_settings


_prisma_client: Any | None = None


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
