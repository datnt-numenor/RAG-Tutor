from __future__ import annotations

from prisma import Prisma

# Single shared Prisma client — connect on app startup, disconnect on shutdown
prisma = Prisma()


async def connect_db() -> None:
    await prisma.connect()


async def disconnect_db() -> None:
    await prisma.disconnect()
