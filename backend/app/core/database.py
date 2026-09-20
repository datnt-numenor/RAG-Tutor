from __future__ import annotations

from functools import lru_cache

from prisma import Prisma
from supabase import Client, create_client

from app.core.config import get_settings

# Single shared Prisma client — connect on app startup, disconnect on shutdown
prisma = Prisma()


async def connect_db() -> None:
    await prisma.connect()


async def disconnect_db() -> None:
    await prisma.disconnect()


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
