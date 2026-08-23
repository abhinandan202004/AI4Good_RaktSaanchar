# 🔭 FastAPI Full-Stack Observability Lab

A complete, production-style, self-contained local observability lab demonstrating the **Three Pillars of Observability** (Metrics, Logs, Traces) along with unified dashboard visualization using:

* **Application**: FastAPI (Python 3.12) with OpenTelemetry auto-instrumentation & Prometheus Instrumentator
* **Metrics**: Prometheus
* **Logs**: Grafana Loki (collected and shipped via Promtail)
* **Traces**: Jaeger (OpenTelemetry OTLP receiver)
* **Dashboards & Unified UI**: Grafana (pre-provisioned datasources & dashboard)

---

## 🏛️ Architecture Overview

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

---

## 📦 Project Structure

```
observability-lab/
├── docker-compose.yml              # Orchestrates all 6 services
├── README.md                       # Comprehensive setup and user guide
├── app/
│   ├── Dockerfile                  # Python 3.12 slim container
│   ├── requirements.txt            # FastAPI, OpenTelemetry & Prometheus deps
│   ├── main.py                     # API endpoints, middleware & instrumentation
│   ├── telemetry.py                # OpenTelemetry TracerProvider & OTLP exporter
│   └── logger.py                   # Structured JSON logger with trace_id injection
├── prometheus/
│   └── prometheus.yml              # Prometheus scrape targets & intervals
├── loki/
│   └── loki-config.yml             # Loki filesystem & TSDB storage config
├── promtail/
│   └── promtail-config.yml         # Promtail Docker log collector & JSON pipeline
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasources.yml     # Auto-configured Prometheus, Loki, Jaeger
│       └── dashboards/
│           ├── dashboards.yml      # Dashboard provider definition
│           └── observability-dashboard.json # Pre-built unified KPI dashboard
└── docs/
    └── queries.md                  # Cheat sheet for PromQL, LogQL, and TraceQL
```

---

## 🚀 Quick Start

### 1. Start the entire observability stack

From inside the `observability-lab/` directory, run:

```bash
docker compose up -d --build
```

Verify all 6 containers are running:
```bash
docker compose ps
```

---

## 🌐 Service Access URLs

| Service | URL | Default Credentials | Purpose |
|---|---|---|---|
| **FastAPI App** | [http://localhost:8000](http://localhost:8000) | *None* | Application & Interactive Swagger Docs ([/docs](http://localhost:8000/docs)) |
| **FastAPI Metrics** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | *None* | Raw Prometheus metrics exposition format |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` | Unified Metrics, Logs, and Traces dashboards |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | *None* | Metric exploration, PromQL console & target health |
| **Jaeger UI** | [http://localhost:16686](http://localhost:16686) | *None* | Distributed tracing waterfall graphs & latency analysis |
| **Loki API** | [http://localhost:3100](http://localhost:3100) | *None* | Log store engine |

---

## 🧪 Testing & Generating Traffic

Generate sample traffic to populate metrics, logs, and traces:

### 1. Normal Requests (Baseline)
```bash
# Root endpoint
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health
```

### 2. Slow Requests (Multi-Span Trace Analysis)
```bash
# Triggers internal child spans: 'db_query_fetch_records' and 'process_and_serialize_payload'
curl "http://localhost:8000/slow?delay=1.5"
```

### 3. Error Requests (Simulate Failures)
```bash
# 500 Internal Server Error (Unhandled Exception with Stack Trace)
curl http://localhost:8000/error

# 400 Bad Request (Validation failure)
curl "http://localhost:8000/error?type=validation"
```

### 4. Continuous Traffic Generator (Simulate Live Load)
Run a quick bash/PowerShell loop to send varied traffic:

**PowerShell:**
```powershell
1..50 | ForEach-Object {
    Invoke-RestMethod http://localhost:8000/ | Out-Null
    Invoke-RestMethod http://localhost:8000/health | Out-Null
    if ($_ % 5 -eq 0) { Invoke-RestMethod "http://localhost:8000/slow?delay=1.2" | Out-Null }
    if ($_ % 7 -eq 0) { try { Invoke-RestMethod http://localhost:8000/error } catch {} }
    Start-Sleep -Milliseconds 300
}
```

**Bash:**
```bash
for i in {1..50}; do
  curl -s http://localhost:8000/ > /dev/null
  curl -s http://localhost:8000/health > /dev/null
  [ $((i % 5)) -eq 0 ] && curl -s "http://localhost:8000/slow?delay=1.2" > /dev/null
  [ $((i % 7)) -eq 0 ] && curl -s http://localhost:8000/error > /dev/null
  sleep 0.3
done
```

---

## 🧭 Verification Checklist

### 1. Verify Metrics in Prometheus (`http://localhost:9090`)
1. Open [http://localhost:9090/targets](http://localhost:9090/targets) $\rightarrow$ Confirm `fastapi-service` state is **UP**.
2. Go to **Graph** and query:
   ```promql
   sum(rate(http_request_duration_seconds_count[1m])) by (status)
   ```
3. Confirm status codes `200`, `400`, and `500` appear.

---

### 2. Verify Traces in Jaeger (`http://localhost:16686`)
1. Open [http://localhost:16686](http://localhost:16686).
2. Under **Service**, select `fastapi-service` $\rightarrow$ Click **Find Traces**.
3. Select a `GET /slow` trace:
   - Notice the trace duration matches the delay (~1.5s).
   - Observe the nested child spans:
     - ├─ `GET /slow` (root span)
     - ├── `db_query_fetch_records` (60% duration with SQL statement tag)
     - └── `process_and_serialize_payload` (40% duration)
4. Select a `GET /error` trace:
   - Notice the span is flagged in **red** with `error=true`.
   - Expand the span tags to see the exception event and stack trace.

---

### 3. Verify Logs in Loki
1. Open Grafana $\rightarrow$ **Explore** $\rightarrow$ Select `Loki` as datasource.
2. Run the LogQL query:
   ```logql
   {app=~".*fastapi.*"} | json
   ```
3. Expand any log entry: notice that `trace_id` and `span_id` are automatically extracted and populated!

---

### 4. Verify Unified Dashboard in Grafana (`http://localhost:3000`)
1. Login with `admin` / `admin`.
2. Go to **Dashboards** $\rightarrow$ **FastAPI Observability** $\rightarrow$ **FastAPI Observability Suite**.
3. Observe:
   - **Throughput (RPS)** & **5xx Error Rate %**
   - **p50, p90, p95, p99 Latency percentiles**
   - **Live Application Logs Stream**
   - **Log-to-Trace Link**: In the log viewer, click on the **TraceID** button next to a log line to jump straight into the corresponding Jaeger trace!

---

## 🛠️ Deep Dive: Telemetry Correlation

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Metrics Alert / Grafana Graph                            │
│    "5xx error rate spiked to 14%"                           │
└──────────────────────────────┬──────────────────────────────┘
                               │ Inspect time window
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Loki Logs                                                │
│    {app="fastapi"} | json | level="ERROR"                   │
│    Log contains: {"trace_id": "4bf92f3577b34da6a3ce929d0e0"}│
└──────────────────────────────┬──────────────────────────────┘
                               │ Click TraceID Link
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Jaeger Waterfall Trace                                   │
│    Root Span -> DB Query Span -> Exception Captured         │
│    Identifies root cause in seconds without guessing.       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧹 Teardown

To stop and remove all containers and volumes:

```bash
docker compose down -v
```
