from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import connect_db, disconnect_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting RAGTutor API", env=settings.app_env)
    await connect_db()
    yield
    await disconnect_db()
    logger.info("Shutting down RAGTutor API")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RAGTutor API",
        description="AI Study Assistant — RAG chat, quiz, PDF annotation, spaced repetition",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health_check() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "1.0.0"})

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
