# =============================================================================
# Enterprise AI Platform - Multi-stage Dockerfile
# =============================================================================
#
# Build: docker build -t ai-platform --target gateway .
# Targets: gateway, orchestrator, policy, memory, eval
#
# =============================================================================

# -----------------------------------------------------------------------------
# Base Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# -----------------------------------------------------------------------------
# Builder Stage
# -----------------------------------------------------------------------------
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY platform/pyproject.toml platform/README.md ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -e ".[all]"

# Copy application code
COPY platform/ ./

# -----------------------------------------------------------------------------
# Gateway Image
# -----------------------------------------------------------------------------
FROM base AS gateway

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app /app

# Switch to non-root user
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health/live || exit 1

CMD ["uvicorn", "gateway.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]

# -----------------------------------------------------------------------------
# Orchestrator Image
# -----------------------------------------------------------------------------
FROM base AS orchestrator

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER appuser

EXPOSE 8081

CMD ["python", "-m", "orchestrator.worker"]

# -----------------------------------------------------------------------------
# Policy Engine Image
# -----------------------------------------------------------------------------
FROM base AS policy

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER appuser

EXPOSE 8082

CMD ["python", "-m", "policy.server"]

# -----------------------------------------------------------------------------
# Memory Service Image
# -----------------------------------------------------------------------------
FROM base AS memory

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER appuser

EXPOSE 8083

CMD ["python", "-m", "memory.server"]

# -----------------------------------------------------------------------------
# Evaluation Runner Image
# -----------------------------------------------------------------------------
FROM base AS eval

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER appuser

CMD ["python", "-m", "eval.runner"]
