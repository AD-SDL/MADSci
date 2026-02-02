# Principles

## Glossary (Quick Reference)

- **Trace**: A tree of spans representing a single distributed operation.
- **Span**: A timed unit of work within a trace (has a name, attributes, status).
- **Context propagation**: Passing trace context across process/service boundaries (typically via HTTP headers).
- **Collector**: A service that receives telemetry (OTLP) and exports it to backends.
- **Resource attributes**: Stable attributes describing the emitting service (e.g., `service.name`, `service.version`).
- **High-cardinality attributes**: Attributes with many unique values (e.g., ULIDs), which can blow up cost/storage.

## Graceful Degradation

OTEL integration must **never** break core functionality. All OTEL operations should:

1. **Fail silently** when OTEL infrastructure is unavailable
2. **Log warnings** but continue normal operation
3. **Allow full disabling** without code changes (via configuration)

```python
# Pattern for graceful degradation
def _setup_otel(self) -> None:
    """Initialize OpenTelemetry with graceful degradation."""
    try:
        self._otel_runtime = configure_otel(
            enabled=True,
            service_name=self.config.otel_service_name or f"madsci.{self.name}",
        )
    except Exception as e:
        self.logger.warning(
            "OTEL setup failed, continuing without tracing",
            error=str(e),
            exc_info=True,
        )
        self._otel_runtime = None
```

## Non-Goals (Initial Scope)

To keep OTEL integration safe and maintainable, the first iteration intentionally avoids:

1. Creating a new OTEL span for every log line (high volume + noisy traces)
2. Adding high-cardinality span attributes (e.g., ULIDs) except where explicitly justified
3. Re-implementing context extraction/injection differently in each component

## Span Attribute Cardinality Policy (Normative)

Span attributes are indexed and stored by tracing backends. High-cardinality attributes can significantly increase
cost and degrade query performance.

Rules:

1. Prefer low-cardinality attributes for spans (bounded enums, booleans, small integers).
2. Do not attach ULIDs, database IDs, workflow IDs, experiment IDs, resource IDs, event IDs, or similar identifiers as
   span attributes by default.
3. If an identifier is essential for debugging, prefer:

   - Logging the identifier to EventManager (structured logs/events), which already carries trace correlation fields.
   - Adding the identifier only as a span `event` (not attribute) in rare cases.

4. For user-facing name-like fields, treat as potentially high-cardinality unless bounded/controlled. Prefer
   normalized categorical values (e.g., `workflow.step.action`, `manager.operation`, `http.method`, `http.route`).

Allowed attribute examples (low-cardinality):

- `madsci.manager` (manager name)
- `madsci.operation` (operation name)
- `workflow.step.index` (integer)
- `workflow.step.action` (from a bounded action set)
- `event.type` (from `EventType` enum)
- `event.level` (log level)
- `http.method`, `http.route`, `http.status_code`

If this policy is later relaxed, it should be done deliberately with sampling/cost awareness and documented in this
plan.

## Configuration Principles and Precedence

This plan follows upstream OpenTelemetry conventions while keeping MADSci ergonomics.

## Configuration Precedence (Normative)

OpenTelemetry SDK configuration is process-global. To avoid ambiguous behavior, MADSci uses an explicit precedence
order between MADSci settings fields (e.g., `otel_enabled`) and upstream OpenTelemetry environment variables
(e.g., `OTEL_TRACES_EXPORTER`).

Scope:

- This precedence applies to all processes that use MADSci OTEL (managers, nodes, clients).
- The shared OTEL bootstrap is responsible for implementing this precedence.

### Precedence Table

| Capability | MADSci Setting(s) | Upstream Env Var(s) | Precedence Rule |
|------------|-------------------|---------------------|-----------------|
| Enable/disable OTEL | `otel_enabled` | `OTEL_SDK_DISABLED` | If `otel_enabled` is explicitly set (True/False), it wins. Otherwise, fall back to `OTEL_SDK_DISABLED` semantics (disabled when `OTEL_SDK_DISABLED=true`). |
| Traces exporter | `otel_exporter` | `OTEL_TRACES_EXPORTER` | If `otel_exporter` is set, it wins. Otherwise, use `OTEL_TRACES_EXPORTER`. |
| Metrics exporter | `otel_metrics_exporter` (optional) | `OTEL_METRICS_EXPORTER` | If `otel_metrics_exporter` is set, it wins. Otherwise, use `OTEL_METRICS_EXPORTER`. |
| Logs exporter | `otel_logs_exporter` (optional) | `OTEL_LOGS_EXPORTER` | If `otel_logs_exporter` is set, it wins. Otherwise, use `OTEL_LOGS_EXPORTER`. |
| OTLP endpoint | `otel_endpoint` | `OTEL_EXPORTER_OTLP_ENDPOINT` | If `otel_endpoint` is set, it wins. Otherwise, use `OTEL_EXPORTER_OTLP_ENDPOINT`. |
| OTLP protocol | `otel_protocol` | `OTEL_EXPORTER_OTLP_PROTOCOL` | If `otel_protocol` is set, it wins. Otherwise, use `OTEL_EXPORTER_OTLP_PROTOCOL`. |
| Sampling | `otel_sampler`, `otel_sampler_arg` (optional) | `OTEL_TRACES_SAMPLER`, `OTEL_TRACES_SAMPLER_ARG` | If MADSci sampler fields are set, they win. Otherwise, use the upstream env vars. |
| Resource attributes | `otel_resource_attributes` (optional) | `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_SERVICE_NAME` | MADSci can add/override attributes for dev/test. In production, prefer env vars; when both are set, MADSci should merge with env vars and allow explicit per-field override (documented by the bootstrap). |

Notes:

- The `enabled` rule is intentionally strict: disabling must always be possible via MADSci config even if env vars
  enable exporting.
- Where MADSci settings are not implemented yet (e.g., metrics/log exporters, sampler), the precedence rules act as
  the target behavior for the shared bootstrap API.

### Defaults (When Neither Is Set)

- `otel_enabled`: defaults to False in MADSci settings.
- Exporters: default to upstream OTEL SDK defaults (typically `otlp` when configured by env, otherwise `none`).
- Endpoint/protocol: only required when using OTLP exporters.

### Compatibility With Existing Code

Some existing components may only implement a subset of these settings today. The plan's acceptance criteria require
that the shared bootstrap documents and enforces one consistent precedence model across the repo.

Important: OpenTelemetry SDK configuration is generally process-global; this plan assumes each service process
initializes OTEL once, idempotently.

## Global Provider / Idempotency

OpenTelemetry providers (TracerProvider / MeterProvider) are typically global per-process. To avoid surprising side
effects (especially in tests), all SDK/provider/exporter setup should:

- Be centralized in a single shared bootstrap.
- Be idempotent (safe to call multiple times; the first call “wins”).
- Provide a clean shutdown hook for flush.

## Single Shared OTEL Module (Core Requirement)

MADSci will implement **one canonical OTEL integration module** in `madsci.common.otel`.

All OTEL implementation details (SDK/provider configuration, exporter setup, propagators, trace correlation helpers,
and safe shutdown) should live in this module.

All other packages/components (clients, managers, nodes) should:

1. Import OTEL functionality only via `madsci.common.otel`
2. Avoid direct OTEL SDK/provider/exporter configuration
3. Avoid re-implementing trace/span ID extraction or header propagation

This is the primary mechanism used to enforce consistent behavior and prevent configuration drift across services.

## Security Considerations

1. **Never hardcode credentials** in configuration files
2. **Use environment variables** for sensitive values (passwords, API keys)
3. **Document proper secrets management** for production deployments
4. **Sanitize span attributes** to avoid leaking sensitive data

```yaml
# Example: Use environment variables for Grafana credentials
grafana:
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-changeme}
```

## Async Context Propagation

Many MADSci managers use async FastAPI endpoints.

Preferred approach:

- Extract inbound context from request headers using the OTEL propagator.
- Start spans with `context=...` so the extracted parent is used.
- Avoid manual `attach()` / `detach()` unless you have a specific context isolation need.

```python
from opentelemetry.propagate import extract

async def async_operation_with_tracing(self, request: Request):
    """Async operation with context extracted from headers."""
    if not self._tracer:
        return await self._do_async_work()

    ctx = extract(dict(request.headers))
    with self._tracer.start_as_current_span("async.operation", context=ctx) as span:
        result = await self._do_async_work()
        return result
```

## Shutdown Handling

OTEL providers must be properly shutdown to flush pending telemetry:

```python
# In manager shutdown or application exit
def shutdown(self) -> None:
    """Clean shutdown with telemetry flush."""
    if self._otel_runtime:
        self._otel_runtime.shutdown()  # Flushes pending spans/metrics
```

The canonical shutdown/flush behavior must live in `madsci.common.otel`.
