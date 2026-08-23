import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

SERVICE_NAME_VALUE = os.getenv("OTEL_SERVICE_NAME", "fastapi-service")
SERVICE_VERSION_VALUE = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
ENVIRONMENT_VALUE = os.getenv("DEPLOYMENT_ENVIRONMENT", "production-style-lab")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318/v1/traces")


def setup_telemetry(app: FastAPI):
    """
    Initializes OpenTelemetry TracerProvider, OTLP Exporter,
    and auto-instruments the FastAPI application.
    """
    # 1. Resource Metadata
    resource = Resource.create({
        SERVICE_NAME: SERVICE_NAME_VALUE,
        SERVICE_VERSION: SERVICE_VERSION_VALUE,
        DEPLOYMENT_ENVIRONMENT: ENVIRONMENT_VALUE,
    })

    # 2. Tracer Provider
    tracer_provider = TracerProvider(resource=resource)

    # 3. OTLP HTTP Span Exporter (to Jaeger)
    otlp_exporter = OTLPSpanExporter(
        endpoint=OTLP_ENDPOINT,
    )

    # 4. Batch Span Processor for high-performance async flushing
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # 5. Register global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # 6. Instrument FastAPI endpoints
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls="metrics,health"  # keeps noise down while preserving full app metrics
    )

    return trace.get_tracer(SERVICE_NAME_VALUE)


# Global application tracer for manual/nested spans
tracer = trace.get_tracer(SERVICE_NAME_VALUE)
