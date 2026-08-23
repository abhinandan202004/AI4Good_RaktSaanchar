import logging
import sys
import os
from pythonjsonlogger import jsonlogger
from opentelemetry import trace

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that automatically enriches log records
    with OpenTelemetry trace_id and span_id for Log-to-Trace correlation.
    """
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Standard field formatting
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = os.getenv("OTEL_SERVICE_NAME", "fastapi-service")
        
        # OpenTelemetry Trace Context injection
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            if ctx and ctx.is_valid:
                log_record["trace_id"] = f"{ctx.trace_id:032x}"
                log_record["span_id"] = f"{ctx.span_id:016x}"
                log_record["trace_flags"] = ctx.trace_flags


def setup_logger(name: str = "app") -> logging.Logger:
    """Configures structured JSON logging writing to stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if already initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = CustomJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger

logger = setup_logger("fastapi-service")
