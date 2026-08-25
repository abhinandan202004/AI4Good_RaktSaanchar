# 🔭 Full Architecture & Implementation Guide: Observability Stack for FastAPI

## 1. Executive Summary

This document provides a comprehensive end-to-end breakdown of the local, production-style observability stack implemented in the `observability-lab/` directory.

The stack demonstrates the **Three Pillars of Observability** (Metrics, Logs, and Traces) using industry-standard tools:
* **Application**: FastAPI (Python 3.12) with OpenTelemetry SDK and Prometheus Instrumentator
* **Metrics**: Prometheus (Pull-based time-series scraping)
* **Logs**: Grafana Loki (Storage & LogQL) + Promtail (Docker container log collector)
* **Distributed Tracing**: Jaeger (OTLP receiver on ports 4317/4318 with waterfall graph visualization)
* **Unified Visualization & Correlation**: Grafana (Pre-provisioned dashboards with derived field log-to-trace linking)

---

## 2. Architecture & Data Flow

```
                               ┌────────────────────────────────────────┐
                               │          FastAPI Application           │
                               │        (Port 8000 / FastAPI API)       │
                               └────┬──────────────┬──────────────┬─────┘
                                    │              │              │
                         Prometheus │   Structured │         OTLP │ OpenTelemetry
                            Metrics │    JSON Logs │       Traces │ gRPC / HTTP
                                    │              │              │
                                    ▼              ▼              ▼
                             ┌────────────┐ ┌────────────┐ ┌────────────┐
                             │ Prometheus │ │  Promtail  │ │   Jaeger   │
                             │(Port 9090) │ │(Port 9080) │ │(Port 16686)│
                             └─────┬──────┘ └──────┬─────┘ └──────┬─────┘
                                   │               │              │
                                   │        Logs   ▼              │
                                   │        ┌────────────┐        │
                                   │        │    Loki    │        │
                                   │        │(Port 3100) │        │
                                   │        └──────┬─────┘        │
                                   │               │              │
                                   └───────┐       │       ┌──────┘
                                           ▼       ▼       ▼
                                     ┌───────────────────────────┐
                                     │          Grafana          │
                                     │ (Port 3000 / Dashboards)  │
                                     └───────────────────────────┘
```

### Telemetry Pipeline Breakdown:
1. **Metrics Flow**:
   * FastAPI uses `prometheus-fastapi-instrumentator` to track request rates, latency histograms, and in-flight counters at `/metrics`.
   * Prometheus queries (scrapes) `http://fastapi:8000/metrics` every 15 seconds (5 seconds in testing).
2. **Logs Flow**:
   * FastAPI generates structured JSON logs to `stdout` containing `level`, `duration_ms`, `http_status`, `trace_id`, and `span_id`.
   * Promtail reads the Docker daemon container stream via `/var/run/docker.sock`, parses the JSON fields, labels them, and pushes them to Loki (`http://loki:3100`).
3. **Traces Flow**:
   * OpenTelemetry instrumentation automatically creates a root span for every HTTP request and pushes span packets to Jaeger's OTLP HTTP receiver (`http://jaeger:4318/v1/traces`).
   * Custom nested child spans (`db_query_fetch_records`, `process_and_serialize_payload`, `risky_operation`) are created for deep-dive latency analysis.
4. **Visualization & 1-Click Correlation**:
   * Grafana queries Prometheus for KPIs, Loki for logs, and Jaeger for traces.
   * A derived field in Grafana matches `"trace_id": "<hex>"` in Loki logs and renders a **View Trace in Jaeger** button that jumps directly to the exact span in Jaeger.

---

## 3. Directory Structure & File Inventory

```
observability-lab/
├── docker-compose.yml              # 6 Orchestrated Docker services
├── README.md                       # Quick start user guide
├── traffic.py                      # Multi-endpoint load & error generation script
├── app/
│   ├── Dockerfile                  # Container definition for FastAPI
│   ├── requirements.txt            # Python dependencies
│   ├── main.py                     # API routes, middleware, and metrics exposition
│   ├── telemetry.py                # OpenTelemetry TracerProvider & OTLP exporter
│   └── logger.py                   # Custom JSON formatter injecting trace_id/span_id
├── prometheus/
│   └── prometheus.yml              # Prometheus scrape jobs & intervals
├── loki/
│   └── loki-config.yml             # Loki TSDB & filesystem storage engine config
├── promtail/
│   └── promtail-config.yml         # Promtail Docker socket scraper & pipeline stages
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasources.yml     # Auto-configured Prometheus, Loki, & Jaeger sources
│       └── dashboards/
│           ├── dashboards.yml      # Dashboards provider loader
│           └── observability-dashboard.json # Pre-built unified KPI dashboard
└── docs/
    └── queries.md                  # Comprehensive PromQL, LogQL, & TraceQL cheat sheet
```

---

## 4. Detailed Component Implementation

### 4.1 FastAPI Application (`app/`)

#### A. Structured Logger with Trace Context (`app/logger.py`)
Automatically queries OpenTelemetry's active span context. If a trace is active, `trace_id` and `span_id` are injected into every JSON log record.

```python
from opentelemetry import trace
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["service"] = "fastapi-service"
        
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            if ctx and ctx.is_valid:
                log_record["trace_id"] = f"{ctx.trace_id:032x}"
                log_record["span_id"] = f"{ctx.span_id:016x}"
```

#### B. OpenTelemetry Setup (`app/telemetry.py`)
Initializes the `TracerProvider`, creates the `OTLPSpanExporter` sending to Jaeger, and attaches `FastAPIInstrumentor`.

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(app: FastAPI):
    resource = Resource.create({"service.name": "fastapi-service", "service.version": "1.0.0"})
    tracer_provider = TracerProvider(resource=resource)
    
    otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4318/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(tracer_provider)
    
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider, excluded_urls="metrics,health")
    return trace.get_tracer("fastapi-service")
```

#### C. Endpoints & Prometheus Metrics (`app/main.py`)
* `GET /`: Service metadata and welcome message.
* `GET /health`: Health status probe.
* `GET /slow?delay=1.5`: Simulates multi-stage latency using nested child spans:
  * Span 1: `db_query_fetch_records` (database query simulation with SQL statement tag).
  * Span 2: `process_and_serialize_payload` (data compression/serialization simulation).
* `GET /error`: Simulates internal crashes (500) and validation errors (400), marking the trace span with `StatusCode.ERROR` and recording exception stack traces.
* `GET /metrics`: Prometheus formatted metric stream.

---

### 4.2 Prometheus Configuration (`prometheus/prometheus.yml`)

Configured to pull metrics every 15s (5s for lab responsiveness):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "fastapi-service"
    metrics_path: "/metrics"
    scrape_interval: 5s
    static_configs:
      - targets: ["fastapi:8000"]
        labels:
          app: "fastapi"
          service: "fastapi-service"
```

---

### 4.3 Loki & Promtail Configuration (`loki/` & `promtail/`)

* **Loki (`loki/loki-config.yml`)**: Configured with single-binary TSDB indexing and local filesystem chunk storage.
* **Promtail (`promtail/promtail-config.yml`)**: Discovers Docker containers with `logging=promtail` label, applies a JSON parsing stage to extract `level`, `trace_id`, `http_status`, and ships them to `http://loki:3100/loki/api/v1/push`.

---

### 4.4 Grafana Provisioning (`grafana/`)

#### A. Data Sources (`grafana/provisioning/datasources/datasources.yml`)
* **Prometheus**: Primary metric source.
* **Loki**: Log viewer with a regex derived field:
  * Regex: `"trace_id":\s*"([a-fA-F0-9]+)"`
  * Action: Generates a clickable link that opens the trace directly in the **Jaeger** datasource.
* **Jaeger**: Trace visualizer with `tracesToLogs` reverse-linking back to Loki queries.

#### B. Provisioned Dashboard (`observability-dashboard.json`)
Pre-loaded with:
1. **KPI Stats**: Request Rate (RPS), 5xx Error Rate %, p95 Latency, Total Request Count, Active In-Flight Requests.
2. **Time-Series Charts**: Throughput by Status Code (200, 400, 500), Response Latency Percentiles (p50, p90, p95, p99), Request Rate by Endpoint Handler.
3. **Log Stream Panels**: Live streaming log console + dedicated Warning & Error log table.

---

### 4.5 Orchestration (`docker-compose.yml`)

Unified Docker Compose configuration with restart policies, dedicated bridge network (`observability-net`), and named persistent volumes:

| Service Name | Image | Port Mapping | Purpose |
|---|---|---|---|
| `fastapi` | `observability-lab-fastapi` (Local Build) | `8000:8000` | Application API & Metrics |
| `prometheus` | `prom/prometheus:v2.51.0` | `9090:9090` | Metrics Engine & Scraper |
| `loki` | `grafana/loki:2.9.4` | `3100:3100` | Log Storage & LogQL |
| `promtail` | `grafana/promtail:2.9.4` | `9080` (Internal) | Docker Log Collector Agent |
| `jaeger` | `jaegertracing/all-in-one:1.55` | `16686:16686`, `4317`, `4318` | OTLP Receiver & Trace UI |
| `grafana` | `grafana/grafana:10.4.0` | `3000:3000` | Unified UI Dashboard |

---

## 5. How to Run and Test

### 5.1 Starting the Stack
```powershell
cd observability-lab
docker compose up -d --build
```

### 5.2 Generating Telemetry Traffic
Run the automated multi-endpoint traffic generator:
```powershell
..\venv\Scripts\python.exe traffic.py
```

### 5.3 Accessing the User Interfaces
* **Grafana**: [http://localhost:3000](http://localhost:3000) *(User: `admin` / Password: `admin`)*
* **Jaeger Tracing**: [http://localhost:16686](http://localhost:16686) *(Service: `fastapi-service`)*
* **Prometheus**: [http://localhost:9090](http://localhost:9090)
* **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5.4 Stopping the Stack
```powershell
cd observability-lab
docker compose down
```

---

## 6. Query Cheat Sheet (PromQL & LogQL)

### Top PromQL Queries:
* **Request Throughput (RPS)**:
  `sum(rate(http_request_duration_seconds_count{app="fastapi"}[1m]))`
* **5xx Error Rate Percentage**:
  `(sum(rate(http_request_duration_seconds_count{app="fastapi", status=~"5.."}[1m])) / sum(rate(http_request_duration_seconds_count{app="fastapi"}[1m]))) * 100`
* **p95 Latency**:
  `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{app="fastapi"}[1m])) by (le))`
* **In-Flight Requests**:
  `sum(http_requests_inprogress{app="fastapi"})`

### Top LogQL Queries:
* **All Application Logs**: `{app=~".*fastapi.*"}`
* **Error Logs Only**: `{app=~".*fastapi.*"} | json | level="ERROR"`
* **Slow Requests (> 500ms)**: `{app=~".*fastapi.*"} | json | duration_ms > 500`
* **Filter by Trace ID**: `{app=~".*fastapi.*"} | json | trace_id="<HEX_ID>"`

---

## 7. Resource Sizing & Free-Tier Strategy

| Hosting Option | RAM Required | Best Recommendation |
|---|---|---|
| **Standard Stack (Current)** | ~750 MB – 1.5 GB | Run on Oracle Cloud **Ampere A1.Flex** (4 OCPU / 24 GB RAM Always Free) or GCP Free Trial. |
| **Ultra-Lightweight Stack** | ~260 MB | Replace Prometheus with **VictoriaMetrics** (~35MB) and Promtail with **Vector** (~15MB). Runs comfortably on 1 GB free VMs. |
| **Grafana Cloud Free Tier** | **0 MB** on VM | Push OTLP directly to Grafana Cloud SaaS (50 GB logs/traces free forever). |
