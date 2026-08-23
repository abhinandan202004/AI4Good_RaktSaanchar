import time
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from logger import logger
from telemetry import setup_telemetry, tracer

# Initialize FastAPI App
app = FastAPI(
    title="Observability Lab API",
    description="Production-style FastAPI service instrumented with Prometheus, Loki, and Jaeger",
    version="1.0.0"
)

# 1. Setup OpenTelemetry auto-instrumentation
setup_telemetry(app)

# 2. Setup Prometheus Metrics Instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")


# ── Request / Response Logging Middleware ─────────────────────────────────────

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"

    # Avoid cluttering logs with frequent metrics scrapes
    is_metrics = path in ("/metrics",)

    if not is_metrics:
        logger.info(
            f"Incoming request {method} {path}",
            extra={
                "http_method": method,
                "http_path": path,
                "client_ip": client_ip,
                "event_type": "request_started"
            }
        )

    try:
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not is_metrics:
            level = logger.warning if response.status_code >= 400 else logger.info
            level(
                f"Completed {method} {path} with status {response.status_code} in {duration_ms}ms",
                extra={
                    "http_method": method,
                    "http_path": path,
                    "http_status": response.status_code,
                    "duration_ms": duration_ms,
                    "event_type": "request_finished"
                }
            )
        return response

    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled exception on {method} {path}: {str(exc)}",
            exc_info=True,
            extra={
                "http_method": method,
                "http_path": path,
                "duration_ms": duration_ms,
                "error_type": exc.__class__.__name__,
                "event_type": "request_failed"
            }
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# ── Application Endpoints ─────────────────────────────────────────────────────

@app.get("/", tags=["General"])
async def root():
    """Root endpoint returning basic service information."""
    logger.info("Handling root endpoint request")
    return {
        "service": "observability-lab-api",
        "status": "online",
        "message": "Welcome to the FastAPI Observability Lab!",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "slow": "/slow?delay=1.5",
            "error": "/error",
            "metrics": "/metrics"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container probes and uptime monitoring."""
    return {
        "status": "healthy",
        "uptime": "ok",
        "checks": {
            "database": "connected",
            "memory": "optimal",
            "storage": "available"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/slow", tags=["Telemetry Demo"])
async def slow_endpoint(delay: float = 1.2):
    """
    Simulates a slow endpoint with artificial latency.
    Generates internal child spans to illustrate nested trace hierarchy in Jaeger.
    """
    logger.info(f"Received request for slow endpoint with delay={delay}s")

    # 1. Child Span 1: Simulated Database Query
    with tracer.start_as_current_span("db_query_fetch_records") as db_span:
        db_span.set_attribute("db.system", "postgresql")
        db_span.set_attribute("db.statement", "SELECT * FROM large_dataset WHERE active = true")
        db_span.set_attribute("db.simulated_latency_sec", delay * 0.6)
        
        logger.info("Executing simulated database query...")
        await asyncio.sleep(delay * 0.6)
        db_span.set_attribute("db.rows_returned", 15420)

    # 2. Child Span 2: Simulated Data Transformation / Computation
    with tracer.start_as_current_span("process_and_serialize_payload") as comp_span:
        comp_span.set_attribute("app.records_processed", 15420)
        comp_span.set_attribute("app.compression", "gzip")
        
        logger.info("Transforming and aggregating data...")
        await asyncio.sleep(delay * 0.4)

    logger.info(f"Slow request processing finished successfully after {delay}s")
    return {
        "status": "success",
        "message": f"Successfully simulated slow operation taking {delay} seconds",
        "breakdown": {
            "database_query_sec": round(delay * 0.6, 2),
            "data_processing_sec": round(delay * 0.4, 2)
        },
        "total_delay_sec": delay,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/error", tags=["Telemetry Demo"])
async def error_endpoint(type: Optional[str] = "database"):
    """
    Simulates an intentional error/exception.
    Generates error logs, increments Prometheus error metrics, and marks the trace span with error status.
    """
    logger.warning(f"Simulating intentional failure (type={type})")

    with tracer.start_as_current_span("risky_operation") as span:
        span.set_attribute("error.simulation_type", type)

        if type == "validation":
            logger.error("Validation failure: invalid payload parameters received")
            span.set_status(Status(StatusCode.ERROR, "Validation failed: payload missing required schema"))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Simulated Bad Request: Schema validation failed"
            )
        
        # Default: Unhandled Database Connection Failure
        logger.error("Fatal exception: database pool exhausted while acquiring connection", exc_info=True)
        span.set_status(Status(StatusCode.ERROR, "DatabaseConnectionTimeout: pool timeout after 30000ms"))
        span.record_exception(RuntimeError("Connection pool timeout: unable to connect to primary read replica"))
        
        raise RuntimeError("CRITICAL: Database connection failed during transaction commit")
