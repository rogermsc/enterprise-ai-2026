"""Gateway Middleware - Security, Audit, and Rate Limiting.

Implements enterprise-grade middleware for:
- Request/Response audit logging
- Rate limiting per client
- Request ID tracking
- Security headers
"""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from gateway.config import settings

logger = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware for compliance and debugging.

    Logs all requests with:
    - Request ID (for correlation)
    - Client IP
    - User agent
    - Request path and method
    - Response status and latency
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log request
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Process request
        start_time = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"

        # Log response
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm.

    Limits requests per client IP within a configurable time window.
    Uses in-memory storage (swap to Redis for distributed deployments).
    """

    def __init__(self, app, max_requests: int | None = None, window_seconds: int | None = None):
        super().__init__(app)
        self.max_requests = max_requests or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window_seconds
        self._requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Initialize or clean old requests
        if client_ip not in self._requests:
            self._requests[client_ip] = []

        # Remove requests outside window
        window_start = current_time - self.window_seconds
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]

        # Check rate limit
        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                requests_in_window=len(self._requests[client_ip]),
            )
            return Response(
                content='{"error": "rate_limit_exceeded", "message": "Too many requests"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Record request
        self._requests[client_ip].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.max_requests - len(self._requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
