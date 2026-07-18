"""
Repository stubs — data access layer on top of Prisma.

Each repository wraps Prisma calls and keeps business logic out of endpoints.
"""
from __future__ import annotations

from app.core.database import prisma


class ProjectRepository:
    async def get_by_id(self, project_id: str):
        return await prisma.project.find_unique(where={"id": project_id})

    async def list_for_user(self, user_id: str):
        members = await prisma.projectmember.find_many(
            where={"user_id": user_id},
            include={"project": True},
        )
        return [m.project for m in members if m.project]

    async def create(self, owner_id: str, data: dict):
        # Full atomic creation handled by Supabase RPC `create_project_with_owner`
        raise NotImplementedError("Use Supabase RPC for atomic project creation")

    async def is_member(self, project_id: str, user_id: str) -> bool:
        m = await prisma.projectmember.find_first(
            where={"project_id": project_id, "user_id": user_id}
        )
        return m is not None

    async def is_owner(self, project_id: str, user_id: str) -> bool:
        m = await prisma.projectmember.find_first(
            where={"project_id": project_id, "user_id": user_id, "role": "owner"}
        )
        return m is not None
