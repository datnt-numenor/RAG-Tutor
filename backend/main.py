from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting RAGTutor API", env=settings.app_env)
    yield
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

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=exc.__class__.__name__,
            )
            raise

        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health_check() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "1.0.0"})

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
