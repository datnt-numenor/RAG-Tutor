from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    projects,
    documents,
    document_jobs,
    chunks,
    chat,
    quiz,
    questions,
    annotations,
    invitations,
    topics,
    schedules,
    progress,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(document_jobs.router, prefix="/document-jobs", tags=["document-jobs"])
api_router.include_router(chunks.router, tags=["chunks"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(quiz.router, tags=["quiz"])
api_router.include_router(questions.router, tags=["questions"])
api_router.include_router(annotations.router, tags=["annotations"])
api_router.include_router(topics.router, tags=["topics"])
api_router.include_router(schedules.router, tags=["schedules"])
api_router.include_router(progress.router, tags=["progress"])
