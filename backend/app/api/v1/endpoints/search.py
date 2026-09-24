from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()


@router.get("/search")
async def global_search(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    q: str = Query(..., min_length=2, max_length=120),
) -> list[dict]:
    """Search projects and documents visible to the current user."""
    db = get_supabase_admin()
    needle = q.strip().casefold()

    memberships = (
        db.table("project_members")
        .select("project_id, projects(id, name, description, status)")
        .eq("user_id", current_user.user_id)
        .execute()
    )

    project_rows = []
    project_ids: list[str] = []
    project_name_by_id: dict[str, str] = {}

    for row in memberships.data or []:
        project = row.get("projects") or {}
        project_id = row["project_id"]
        project_ids.append(project_id)
        project_name_by_id[project_id] = project.get("name") or "Project"

        haystack = " ".join(
            [
                str(project.get("name") or ""),
                str(project.get("description") or ""),
            ]
        ).casefold()
        if needle in haystack:
            project_rows.append(
                {
                    "type": "project",
                    "id": project_id,
                    "project_id": project_id,
                    "title": project.get("name") or "Project",
                    "subtitle": project.get("description"),
                    "href": f"/projects/{project_id}",
                }
            )

    document_rows: list[dict] = []
    if project_ids:
        documents = (
            db.table("documents")
            .select("id, project_id, display_name, status, active_version_id")
            .in_("project_id", project_ids)
            .neq("status", "deleting")
            .limit(200)
            .execute()
        )

        for document in documents.data or []:
            if needle not in str(document.get("display_name") or "").casefold():
                continue

            project_id = document["project_id"]
            document_rows.append(
                {
                    "type": "document",
                    "id": document["id"],
                    "project_id": project_id,
                    "title": document.get("display_name") or "Document",
                    "subtitle": project_name_by_id.get(project_id, "Project"),
                    "href": (
                        f"/projects/{project_id}/documents/{document['id']}"
                    ),
                }
            )

    return (project_rows + document_rows)[:20]
