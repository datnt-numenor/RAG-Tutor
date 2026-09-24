from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter()


class Rectangle(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @field_validator("width")
    @classmethod
    def validate_width(cls, value: float, info):
        data = info.data
        x = float(data.get("x", 0))
        if x + value > 1.000001:
            raise ValueError("rectangle exceeds page width")
        return value

    @field_validator("height")
    @classmethod
    def validate_height(cls, value: float, info):
        data = info.data
        y = float(data.get("y", 0))
        if y + value > 1.000001:
            raise ValueError("rectangle exceeds page height")
        return value


class AnnotationCreate(BaseModel):
    page_number: int = Field(gt=0)
    annotation_type: Literal["text_highlight", "rectangle"] = "rectangle"
    selected_text: str | None = None
    rectangles: list[Rectangle] = Field(min_length=1)
    content: str | None = None
    color: str = "#F4D06F"

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be a hex value like #F4D06F")
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ValueError("invalid hex color") from exc
        return value.upper()


class AnnotationUpdate(BaseModel):
    content: str | None = None
    color: str | None = None
    rectangles: list[Rectangle] | None = None
    selected_text: str | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be a hex value like #F4D06F")
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ValueError("invalid hex color") from exc
        return value.upper()


def _assert_member(db, project_id: str, user_id: str) -> None:
    member = (
        db.table("project_members")
        .select("id")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Project not found")


def _get_version_or_404(
    db,
    project_id: str,
    document_id: str,
    version_id: str,
) -> dict:
    version = (
        db.table("document_versions")
        .select("id, document_id, project_id, mime_type, status, version_number")
        .eq("id", version_id)
        .eq("document_id", document_id)
        .eq("project_id", project_id)
        .maybe_single()
        .execute()
    )
    if not version.data:
        raise HTTPException(status_code=404, detail="Document version not found")
    if version.data["mime_type"] != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Annotations are currently supported for PDF versions only",
        )
    return version.data


@router.get(
    "/projects/{project_id}/documents/{document_id}/versions/{version_id}/annotations"
)
async def list_annotations(
    project_id: UUID,
    document_id: UUID,
    version_id: UUID,
    page: int | None = None,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> list[dict]:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    _get_version_or_404(
        db,
        str(project_id),
        str(document_id),
        str(version_id),
    )

    query = (
        db.table("notes")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("document_id", str(document_id))
        .eq("document_version_id", str(version_id))
        .eq("user_id", current_user.user_id)
        .order("created_at")
    )
    if page is not None:
        query = query.eq("page_number", page)

    return query.execute().data


@router.post(
    "/projects/{project_id}/documents/{document_id}/versions/{version_id}/annotations",
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(
    project_id: UUID,
    document_id: UUID,
    version_id: UUID,
    body: AnnotationCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    _assert_member(db, str(project_id), current_user.user_id)
    _get_version_or_404(
        db,
        str(project_id),
        str(document_id),
        str(version_id),
    )

    result = db.table("notes").insert({
        "user_id": current_user.user_id,
        "project_id": str(project_id),
        "document_id": str(document_id),
        "document_version_id": str(version_id),
        "page_number": body.page_number,
        "annotation_type": body.annotation_type,
        "selected_text": body.selected_text,
        "rectangles": [rect.model_dump() for rect in body.rectangles],
        "content": body.content,
        "color": body.color,
    }).execute()

    return result.data[0]


@router.patch("/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: UUID,
    body: AnnotationUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    db = get_supabase_admin()
    existing = (
        db.table("notes")
        .select("id, user_id")
        .eq("id", str(annotation_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Annotation not found")

    payload = body.model_dump(exclude_unset=True)
    if "rectangles" in payload and body.rectangles is not None:
        payload["rectangles"] = [rect.model_dump() for rect in body.rectangles]
    payload["version"] = 2
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        db.table("notes")
        .update(payload)
        .eq("id", str(annotation_id))
        .eq("user_id", current_user.user_id)
        .execute()
    )
    return result.data[0]


@router.delete(
    "/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_annotation(
    annotation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    db = get_supabase_admin()
    existing = (
        db.table("notes")
        .select("id")
        .eq("id", str(annotation_id))
        .eq("user_id", current_user.user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.table("notes").delete().eq(
        "id", str(annotation_id)
    ).eq(
        "user_id", current_user.user_id
    ).execute()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
