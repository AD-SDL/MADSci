# Phase 4: Example Lab OTEL Infrastructure

**Estimated Effort:** Medium (3-5 days)
**Breaking Changes:** None

## Goals

- Add open-source OTEL infrastructure to the example lab
- Validate that OTEL integration works end-to-end
- Demonstrate observability value for self-driving labs
- Provide a template for users to bootstrap their own implementation

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
