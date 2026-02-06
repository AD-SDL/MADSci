# Phase 4: Example Lab OTEL Infrastructure

**Estimated Effort:** Medium (3-5 days)
**Breaking Changes:** None
**Status:** Complete (February 2026)

## Goals

- Add open-source OTEL infrastructure to the example lab
- Validate that OTEL integration works end-to-end
- Demonstrate observability value for self-driving labs
- Provide a template for users to bootstrap their own implementation

## Completion Notes (February 2026)

Phase 4 implementation is complete. The following has been delivered:

### Infrastructure Components

1. **compose.otel.yaml**: Full observability stack overlay for docker compose
   - Jaeger (traces) - `jaegertracing/all-in-one:1.54.0`
   - Prometheus (metrics) - `prom/prometheus:v2.50.1`
   - Loki (logs) - `grafana/loki:2.9.4`
   - Grafana (unified dashboards) - `grafana/grafana:10.3.3`

2. **OTEL Collector Configuration**:
   - `example_lab/otel-collector.yaml`: Basic config with debug exporter (for base compose.yaml)
   - `example_lab/otel-collector-full.yaml`: Full config with Jaeger, Prometheus, and Loki exporters
   - Image pinned to `otel/opentelemetry-collector-contrib:0.96.0`

3. **Backend Configurations**:
   - `example_lab/otel/prometheus.yaml`: Prometheus configuration with remote write receiver
   - `example_lab/otel/loki.yaml`: Loki local-mode configuration

4. **Grafana Provisioning**:
   - `example_lab/otel/grafana/provisioning/datasources/datasources.yaml`: Auto-configured datasources
   - `example_lab/otel/grafana/provisioning/dashboards/dashboards.yaml`: Dashboard provider config
   - `example_lab/otel/grafana/provisioning/dashboards/json/madsci-overview.json`: Pre-built overview dashboard

5. **Documentation**:
   - `example_lab/OBSERVABILITY.md`: Comprehensive user guide for the observability stack

### Security Improvements

- All UI ports bound to localhost only (127.0.0.1) by default
- Image versions pinned for reproducibility
- Removed unnecessary health check container

### Usage

```bash
# Basic mode (collector with debug output)
docker compose up

# Full observability stack
docker compose -f compose.yaml -f compose.otel.yaml up
```

### Access URLs (localhost only)

- Grafana: http://localhost:3000 (admin/admin)
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090

---

Previous Status (Feb 2026):

- Added an OpenTelemetry Collector service to `compose.yaml` (`otel_collector`) using a file-based config mounted from `example_lab/otel-collector.yaml`.
- Collector config includes both `traces` and `metrics` OTLP pipelines with `debug` exporter for local validation.
- Validated EventManager OTLP export against the collector via docker compose.

## 4.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        MADSci Example Lab                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ EventClient  │  │ WorkcellMgr  │  │ ExperimentMgr│  ...          │
│  │ (traces)     │  │ (traces)     │  │ (traces)     │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                  │                  │                      │
│         └──────────────────┼──────────────────┘                      │
│                            │ OTLP (gRPC/HTTP)                        │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                    OTEL Collector                                ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              ││
│  │  │  Receivers  │→ │ Processors  │→ │  Exporters  │              ││
│  │  │  - OTLP     │  │  - Batch    │  │  - Jaeger   │              ││
│  │  │             │  │  - Memory   │  │  - Prometheus             ││
│  │  └─────────────┘  └─────────────┘  │  - Loki     │              ││
│  │                                     └─────────────┘              ││
│  └──────────────────────────────────────────────────────────────────┘│
│                            │                                         │
│         ┌──────────────────┼──────────────────┐                      │
│         ▼                  ▼                  ▼                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │    Jaeger    │  │  Prometheus  │  │    Loki      │               │
│  │  (Traces)    │  │  (Metrics)   │  │   (Logs)     │               │
│  │  :16686      │  │  :9090       │  │  :3100       │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│                            │                                         │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                      Grafana                                     ││
│  │           Unified Dashboard (Traces + Metrics + Logs)            ││
│  │                        :3000                                     ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 4.2 Docker Compose Services

Notes:

- Pin image versions for reproducibility (avoid `:latest`).
- For safer defaults in shared environments, prefer binding UIs to localhost and documenting how to expose them.
- Explicitly document OTLP receiver ports:
  - `4317/tcp` OTLP gRPC
  - `4318/tcp` OTLP HTTP

### 4.2.1 Port Binding Defaults (Recommended)

Default to localhost-only bindings for UI/inspection surfaces in the example lab to reduce accidental exposure on shared
networks:

- Grafana: bind `127.0.0.1:3000:3000`
- Jaeger UI: bind `127.0.0.1:16686:16686`
- Prometheus: bind `127.0.0.1:9090:9090`
- Loki: bind `127.0.0.1:3100:3100` (if enabled)

Collector OTLP receiver ports may remain on the docker network only (no host port publish) unless you need to send
telemetry from outside docker. If you do publish them, document it clearly.

If logs-to-Loki via the collector proves brittle across versions, treat Loki as optional in the first iteration and
deliver traces (Jaeger) + metrics (Prometheus) first.

Create `compose.otel.yaml` (or add to existing `compose.yaml`). Refer to the original plan for the full compose snippet.

### 4.2.2 Image Version Pinning

All observability images should use explicit versions (no floating tags). This applies to:

- `otel/opentelemetry-collector`
- `jaegertracing/all-in-one`
- `prom/prometheus`
- `grafana/grafana`
- `grafana/loki`

Pinning exact versions is required for troubleshooting and reproducible demo environments.

## 4.3 Acceptance Criteria

- [x] `docker compose -f compose.yaml -f compose.otel.yaml up` brings up working observability stack
- [x] All image versions pinned for reproducibility
- [x] UI ports bound to localhost only (127.0.0.1) for security
- [x] Jaeger receives and displays traces from MADSci managers
- [x] Prometheus receives metrics via remote write from OTEL collector
- [x] Loki receives logs from OTEL collector
- [x] Grafana pre-configured with all datasources (Jaeger, Prometheus, Loki)
- [x] MADSci overview dashboard pre-installed in Grafana
- [x] Trace correlation: logs link to traces via trace_id
- [x] Documentation provided (`example_lab/OBSERVABILITY.md`)
