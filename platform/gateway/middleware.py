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
    Supports both in-memory (single instance) and Redis (distributed) backends.
    """

    def __init__(self, app, max_requests: int | None = None, window_seconds: int | None = None):
        super().__init__(app)
        self.max_requests = max_requests or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window_seconds
        self._local_requests: dict[str, list[float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup stale entries every 5 minutes
        self._redis_client = None
        self._redis_available = False
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis client for distributed rate limiting."""
        try:
            import redis
            redis_url = settings.redis_url
            if redis_url:
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self._redis_client.ping()
                self._redis_available = True
                logger.info("rate_limiter_redis_enabled", redis_url=redis_url[:20] + "...")
        except ImportError:
            logger.info("rate_limiter_using_memory", reason="redis package not installed")
        except Exception as e:
            logger.warning("rate_limiter_using_memory", reason=str(e))

    async def _check_rate_limit_redis(self, client_ip: str) -> tuple[bool, int]:
        """Check rate limit using Redis (distributed)."""
        key = f"ratelimit:{client_ip}"
        current_time = time.time()
        window_start = current_time - self.window_seconds

        try:
            pipe = self._redis_client.pipeline()
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            # Add current request with unique member to avoid collisions within same second
            member = f"{current_time}:{uuid.uuid4().hex[:8]}"
            pipe.zadd(key, {member: current_time})
            # Set expiry
            pipe.expire(key, self.window_seconds)
            results = pipe.execute()

            request_count = results[1]  # zcard result
            remaining = max(0, self.max_requests - request_count - 1)

            if request_count >= self.max_requests:
                return False, 0

            return True, remaining
        except Exception as e:
            logger.warning("redis_rate_limit_error", error=str(e))
            # Fall back to in-memory
            return self._check_rate_limit_memory(client_ip)

    def _check_rate_limit_memory(self, client_ip: str) -> tuple[bool, int]:
        """Check rate limit using in-memory storage (single instance)."""
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Periodic cleanup of stale entries to prevent memory leak
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_stale_entries(window_start)
            self._last_cleanup = current_time

        if client_ip not in self._local_requests:
            self._local_requests[client_ip] = []

        # Remove old entries for this IP
        self._local_requests[client_ip] = [
            t for t in self._local_requests[client_ip] if t > window_start
        ]

        request_count = len(self._local_requests[client_ip])

        if request_count >= self.max_requests:
            return False, 0

        self._local_requests[client_ip].append(current_time)
        remaining = self.max_requests - request_count - 1

        return True, remaining

    def _cleanup_stale_entries(self, window_start: float) -> None:
        """Remove IPs with no recent requests to prevent memory leak."""
        stale_ips = [
            ip for ip, timestamps in self._local_requests.items()
            if not timestamps or all(t <= window_start for t in timestamps)
        ]
        for ip in stale_ips:
            del self._local_requests[ip]
        if stale_ips:
            logger.debug("rate_limiter_cleanup", removed_ips=len(stale_ips))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if self._redis_available:
            allowed, remaining = await self._check_rate_limit_redis(client_ip)
        else:
            allowed, remaining = self._check_rate_limit_memory(client_ip)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                backend="redis" if self._redis_available else "memory",
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

        # Process request
        response = await call_next(request)

        # Add rate limit headers
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
