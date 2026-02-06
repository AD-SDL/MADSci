# OpenTelemetry Observability Stack

This guide explains how to use the OpenTelemetry (OTEL) observability stack included with the MADSci example lab.

## Overview

The MADSci example lab includes a complete observability stack that provides:

- **Traces**: Distributed tracing to understand request flow across services
- **Metrics**: Performance and operational metrics from all managers
- **Logs**: Centralized log aggregation with trace correlation

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        MADSci Example Lab                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ EventManager │  │ WorkcellMgr  │  │ DataManager  │  ...          │
│  │ (traces)     │  │ (traces)     │  │ (traces)     │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                  │                  │                      │
│         └──────────────────┼──────────────────┘                      │
│                            │ OTLP (gRPC :4317)                       │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                    OTEL Collector                                ││
│  │  Receives → Processes → Exports to backends                     ││
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

## Quick Start

### Basic Mode (Collector + Debug Output)

The base `compose.yaml` includes the OTEL collector with debug output. Traces and metrics are received but only logged to the collector's stdout.

```bash
docker compose up
```

### Full Observability Stack

To enable the full observability stack with Jaeger, Prometheus, Loki, and Grafana:

```bash
docker compose -f compose.yaml -f compose.otel.yaml up
```

## Accessing the UIs

All services use host network mode:

| Service    | URL                       | Description                        |
|------------|---------------------------|------------------------------------|
| Grafana    | http://localhost:3000     | Unified dashboards (admin/admin)   |
| Jaeger     | http://localhost:16686    | Distributed tracing UI             |
| Prometheus | http://localhost:9090     | Metrics querying                   |
| Loki       | http://localhost:3100     | Log aggregation API                |

**Note:** Jaeger's OTLP receiver is configured on ports 14317 (gRPC) and 14318 (HTTP)
to avoid conflicts with the OTEL collector's receiver ports (4317/4318).

### Default Credentials

- **Grafana**: admin / admin (you'll be prompted to change on first login)

To set a different Grafana password, set the environment variable before starting:

```bash
export GRAFANA_ADMIN_PASSWORD=your-secure-password
docker compose -f compose.yaml -f compose.otel.yaml up
```

## What's Included

### Pre-configured Grafana

- **Datasources**: Jaeger, Prometheus, and Loki are automatically configured
- **Dashboards**: MADSci Lab Overview dashboard is pre-installed
- **Correlations**: Trace IDs in logs link directly to Jaeger traces

### OTEL Collector Pipelines

1. **Traces Pipeline**: OTLP → Batch Processing → Jaeger
2. **Metrics Pipeline**: OTLP → Batch Processing → Prometheus Remote Write
3. **Logs Pipeline**: OTLP → Batch Processing → Loki

## Configuration

### Enabling OTEL in Managers

OTEL is enabled per-manager via environment variables. The example lab's `.env` file has these enabled by default:

```bash
# Event Manager
EVENT_OTEL_ENABLED=true
EVENT_OTEL_SERVICE_NAME="madsci.event"
EVENT_OTEL_EXPORTER="otlp"
EVENT_OTEL_ENDPOINT="http://localhost:4317"
EVENT_OTEL_PROTOCOL="grpc"

# Similar for other managers...
```

### Disabling OTEL

To disable OTEL for a specific manager, set:

```bash
EVENT_OTEL_ENABLED=false
```

### Custom Configuration

Configuration files are located in `example_lab/otel/`:

- `otel-collector-full.yaml`: Full collector config with all exporters
- `prometheus.yaml`: Prometheus configuration
- `loki.yaml`: Loki configuration
- `grafana/provisioning/`: Grafana auto-provisioning configs

## Viewing Traces

### In Jaeger

1. Open http://localhost:16686
2. Select a service from the dropdown (e.g., `madsci.event`)
3. Click "Find Traces"
4. Click on a trace to see the full request flow

### In Grafana

1. Open http://localhost:3000
2. Navigate to "Explore"
3. Select "Jaeger" datasource
4. Search for traces by service or trace ID

## Viewing Metrics

### In Prometheus

1. Open http://localhost:9090
2. Use PromQL queries like:
   - `sum(rate(otelcol_receiver_accepted_spans[5m]))` - Spans per second
   - `sum(rate(otelcol_receiver_accepted_metric_points[5m]))` - Metrics per second

### In Grafana

1. Open http://localhost:3000
2. Go to the "MADSci Lab Overview" dashboard
3. View telemetry rates and trends

## Viewing Logs

### In Grafana

1. Open http://localhost:3000
2. Navigate to "Explore"
3. Select "Loki" datasource
4. Use LogQL queries like:
   - `{job=~".+"}` - All logs
   - `{service_name="madsci.event"}` - Logs from Event Manager

## Trace Correlation

When OTEL is enabled, MADSci automatically:

1. **Propagates trace context** across HTTP requests between services
2. **Includes trace_id/span_id** in structured log events
3. **Links logs to traces** via Grafana's derived fields

This allows you to:
- Click on a trace ID in logs to jump to the full trace
- See which logs were generated during a specific request
- Understand the full flow of a workflow across all managers

## Troubleshooting

### No traces appearing in Jaeger

1. Check that OTEL is enabled in the manager:
   ```bash
   docker compose logs event_manager | grep -i otel
   ```

2. Verify the collector is receiving data:
   ```bash
   docker compose logs otel_collector | grep -i span
   ```

3. Ensure the collector is running:
   ```bash
   docker compose ps otel_collector
   ```

### Collector showing export errors

Check that all backend services are running:
```bash
docker compose -f compose.yaml -f compose.otel.yaml ps
```

### Grafana can't connect to datasources

The datasources use localhost URLs which work with `network_mode: host`. If you're not using host networking, update the datasource URLs in `grafana/provisioning/datasources/datasources.yaml`.

## Data Persistence

Telemetry data is stored in `.madsci/` subdirectories:

- `.madsci/jaeger/` - Trace data
- `.madsci/prometheus/` - Metrics data
- `.madsci/loki/` - Log data
- `.madsci/grafana/` - Grafana settings and dashboards

To reset all observability data:

```bash
docker compose -f compose.yaml -f compose.otel.yaml down
rm -rf .madsci/jaeger .madsci/prometheus .madsci/loki .madsci/grafana
```

## Production Considerations

This observability stack is designed for development and demonstration. For production:

1. **Security**: Use proper authentication, don't expose UIs publicly without protection
2. **Storage**: Configure appropriate retention periods and storage backends
3. **Sampling**: Enable trace sampling to reduce data volume
4. **High Availability**: Consider distributed deployments for Jaeger, Prometheus, and Loki
5. **Secrets**: Use proper secrets management for credentials

## Further Reading

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
