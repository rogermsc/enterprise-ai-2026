"""FastAPI Gateway - Enterprise AI Platform Entry Point.

This module provides the main API gateway for the Enterprise AI Platform.
It handles authentication, request routing, rate limiting, and audit logging.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gateway.config import settings
from gateway.middleware import AuditMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from gateway.routes import agents, health, tasks
from gateway.telemetry import setup_telemetry

logger = structlog.get_logger()

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Enterprise AI Platform Gateway", version=__version__)
    setup_telemetry(app)
    yield
    # Shutdown
    logger.info("Shutting down Enterprise AI Platform Gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Good AI Enterprise Platform",
        description="Enterprise-grade AI Agent Orchestration Platform",
        version=__version__,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        lifespan=lifespan,
    )

    # Security middleware - explicit CORS configuration (no wildcards)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
    else:
        logger.warning("CORS not configured - set GOODAI_CORS_ORIGINS for cross-origin requests")

    # Custom middleware
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Register routes
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "request_id": request.state.request_id if hasattr(request.state, "request_id") else None,
            },
        )

    return app


app = create_app()


def run() -> None:
    """Run the gateway server."""
    import uvicorn
    uvicorn.run(
        "gateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    run()
