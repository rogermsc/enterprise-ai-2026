"""Telemetry and Observability Setup.

Configures OpenTelemetry for distributed tracing and metrics.
Integrates with common observability backends (Jaeger, Prometheus, etc.)
"""

import structlog
from fastapi import FastAPI

from gateway.config import settings

logger = structlog.get_logger()


def setup_telemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry instrumentation.

    Sets up:
    - Distributed tracing with span context propagation
    - Metrics collection
    - FastAPI auto-instrumentation
    """
    if not settings.otel_endpoint:
        logger.info("OpenTelemetry disabled (no endpoint configured)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource
        resource = Resource.create({
            "service.name": "goodai-platform",
            "service.version": "0.1.0",
            "deployment.environment": "production" if not settings.debug else "development",
        })

        # Configure tracer
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        logger.info("OpenTelemetry configured", endpoint=settings.otel_endpoint)

    except ImportError:
        logger.warning("OpenTelemetry packages not installed, skipping instrumentation")
    except Exception as e:
        logger.error("Failed to configure OpenTelemetry", error=str(e))


def get_tracer(name: str = "goodai-platform"):
    """Get a tracer instance for manual instrumentation."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return None
