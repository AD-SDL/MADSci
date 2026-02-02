# Phase 1: EventClient OTEL Completion

**Estimated Effort:** Medium (3-5 days)
**Breaking Changes:** None (OTEL remains optional)

## Goals

- Complete OTEL integration in EventClient so that when `otel_enabled=True`, traces and metrics are properly captured
- Automatically inject trace context into Event objects
- Add HTTP context propagation for events sent to EventManager
- Ensure graceful degradation when OTEL is misconfigured or unavailable

## Definition: "OTEL Enabled" (EventClient)

For Phase 1, "OTEL enabled" means:

- The process configures OpenTelemetry SDK providers/exporters (not only `opentelemetry-api` no-ops).
- EventClient injects trace correlation fields (`trace_id`, `span_id`) when a span is active.
- EventClient propagates context on outbound HTTP requests (e.g., `traceparent`).

It does *not* mean that each log call creates its own span.

## 1.0 Implementation Principles (EventClient)

## 1.0.0 Configuration Precedence

EventClient must follow the shared precedence rules defined in
`docs/dev/opentelemetry_integration_plan/00_principles.md`.

In particular:

- `otel_enabled` must be able to force-disable OTEL even if upstream `OTEL_*` env vars are set.
- When enabled, MADSci settings may override env vars for local/dev/test, but behavior must be deterministic.

### 1.0.1 OTLP Endpoint Format (gRPC vs HTTP)

The OTLP exporter supports both gRPC and HTTP transports.

- **gRPC** endpoints typically look like `http://otel-collector:4317` (no path).
- **HTTP** endpoints typically look like `http://otel-collector:4318` (no path) and may use `/v1/traces`, `/v1/metrics`
  internally depending on exporter configuration.

**Decision: Use `str` for OTLP endpoints, not `AnyUrl`.**

Pydantic's `AnyUrl` normalizes URLs and ensures a trailing `/`, which can break OTLP configurations that are sensitive
to unexpected paths. MADSci will:

1. Store `otel_endpoint` as `Optional[str]` in all settings classes
2. Validate endpoint format at initialization time using a dedicated validator
3. Support both gRPC and HTTP protocols via the `otel_protocol` field

```python
from pydantic import field_validator

class OtelSettings:
    otel_endpoint: Optional[str] = Field(
        default=None,
        description="OTLP endpoint (e.g., 'http://localhost:4317' for gRPC)",
    )
    otel_protocol: Literal["grpc", "http"] = Field(
        default="grpc",
        description="OTLP transport protocol",
    )

    @field_validator("otel_endpoint")
    @classmethod
    def validate_endpoint(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("OTLP endpoint must start with http:// or https://")
        # Strip trailing slash to prevent path issues
        return v.rstrip("/")
```

### 1.0.2 Canonical Trace Correlation Rule

MADSci must have exactly one interpretation for `Event.trace_id` / `Event.span_id`:

- They represent the *current active span context at the time the Event is created*.

Implementation guidance:

- Prefer using `madsci.common.otel.current_trace_context()` (and/or OTEL-aware structlog processors) rather than
  formatting IDs by hand in multiple locations.
- When no span is active (or OTEL is disabled), omit these fields or set them to `None`.

This is the primary mechanism for correlating high-cardinality identifiers (workflow IDs, resource IDs, ULIDs) with
traces: those identifiers belong in structured events/logs, not span attributes.

### 1.0.3 Graceful Degradation

`EventClient` must not fail to initialize or log if OTEL setup fails.

- OTEL setup failures should result in OTEL being disabled for that instance
- A warning event should be logged (with `exc_info=True`) when OTEL setup fails

### 1.0.4 Trace/Span ID Format Requirements

The `Event` model already defines `trace_id` and `span_id` as optional strings. When populated they should be:

- `trace_id`: 32 lowercase hex characters
- `span_id`: 16 lowercase hex characters

Add unit tests validating that injected IDs match these formats.

## 1.1 Test Specifications

Create/extend `src/madsci_client/tests/test_event_client_otel.py`:

```python
class TestEventClientOtelIntegration:
    """Test EventClient OpenTelemetry integration."""

    def test_otel_disabled_by_default(self, config_without_server):
        """Test that OTEL is disabled by default."""
        client = EventClient(config=config_without_server)
        assert client.config.otel_enabled is False
        # Verify no tracer/meter initialized

    def test_otel_enabled_initializes_tracer(self, config_with_otel):
        """Test that enabling OTEL initializes tracer and meter."""
        client = EventClient(config=config_with_otel)
        assert client._otel_runtime is not None
        assert client._otel_runtime.tracer is not None
        assert client._otel_runtime.meter is not None

    def test_log_injects_trace_context_when_span_active(self, config_with_otel):
        """Test that EventClient injects trace_id/span_id when a span is active."""
        # Start a span, log, and verify trace_id/span_id populated

    def test_trace_context_injected_into_event(self, config_with_otel):
        """Test that trace_id and span_id are injected into Event objects."""
        client = EventClient(config=config_with_otel)
        # Mock the event sending, verify trace_id/span_id populated

    def test_trace_and_span_id_format(self, config_with_otel):
        """Test that injected trace_id/span_id match OTEL hex formats."""
        # trace_id: 32 lowercase hex, span_id: 16 lowercase hex

    def test_context_propagated_in_http_headers(self, config_with_otel_and_server):
        """Test that trace context is propagated in HTTP headers to EventManager."""
        # Mock HTTP client, verify traceparent header present

    def test_metrics_recorded_on_log(self, config_with_otel):
        """Test that metrics are recorded when logging."""
        # Verify event counter incremented
        # Verify latency histogram recorded (when sending to server)

    def test_otel_exporter_receives_spans(self, config_with_otel):
        """Test that configured exporter receives spans (use an in-memory exporter)."""
        # Avoid asserting on stdout; verify exporter/export() calls instead

    def test_otel_otlp_exporter_configuration(self, config_with_otel_otlp):
        """Test OTLP exporter is configured correctly."""
        # Verify OTLP exporter initialized with correct endpoint


class TestEventClientOtelMetrics:
    """Test EventClient OTEL metrics collection."""

    def test_event_counter_by_type(self, config_with_otel):
        """Test event counter tracks events by type."""

    def test_event_counter_by_level(self, config_with_otel):
        """Test event counter tracks events by log level."""

    def test_send_latency_histogram(self, config_with_otel_and_server):
        """Test send latency is recorded in histogram."""

    def test_buffer_size_gauge(self, config_with_otel):
        """Test buffer size gauge reflects actual queue size.

        Note: in OTEL Python this should be implemented as an ObservableGauge
        (callback-based), not as an imperative "settable" gauge.
        """

    def test_retry_counter(self, config_with_otel_and_server):
        """Test retry counter incremented on send failures."""


class TestEventClientOtelContextPropagation:
    """Test trace context propagation."""

    def test_bind_preserves_trace_context(self, config_with_otel):
        """Test that context binding preserves trace context."""

    def test_nested_spans_have_correct_parent(self, config_with_otel):
        """Test nested operations create child spans with correct parent."""

    def test_exception_recorded_in_span(self, config_with_otel):
        """Test that exceptions are recorded as span events."""
```

## 1.4 Metrics Testing Strategy (Normative)

OTEL traces and OTEL metrics have different testing ergonomics.

Traces:

- Use an in-memory span exporter/processor and assert on exported spans.
- Do not assert on console output.

Metrics:

- Prefer using an in-memory metric reader (or a test reader) to collect metrics from the MeterProvider.
- Tests should assert on:

  - Instrument existence (counter/histogram/observable gauge are created when OTEL is enabled)
  - Monotonic behavior (counters increment as expected)
  - Attribute sets are low-cardinality and match the expected keys (`event.level`, `event.type`)

- Avoid tests that require standing up a real OTLP collector, Prometheus scrape, or timed periodic export.
  Those belong in optional integration tests / compose validation (Phase 4).

Practical guidance:

- Configure the shared bootstrap to support a "test mode" that:
   - uses an in-memory span exporter
   - uses an in-memory metric reader
   - disables background export threads (deterministic tests)

### 1.4.1 Gauge Semantics (Normative)

OpenTelemetry Python metrics are callback-oriented for gauge-like values.

Rule:

- When this plan refers to a "gauge" (e.g., buffer size), implement it as an
  `ObservableGauge` whose callback reads the current value.

Testing guidance:

- Use an in-memory metric reader to collect, then assert the observed gauge
  value. Do not rely on a custom "set" API.

Acceptance target for Phase 1 tests:

- Unit tests cover counters/recorders at the API level via in-memory readers/exporters.
- End-to-end metric visibility is validated later via the example lab OTEL stack.

## 1.2 Implementation Tasks

### 1.2.0 Adopt Canonical OTEL Bootstrap (`madsci.common.otel`)

Phase 1 must not deepen the existing split-brain OTEL implementation between `madsci_client` and `madsci_common`.

Requirement:

- EventClient must initialize OTEL using the canonical bootstrap in `madsci.common.otel`.
- Any existing OTEL setup code in `madsci_client` should be migrated into `madsci.common.otel` and then removed from
  `madsci_client`.

Migration guidance:

- First, implement `madsci.common.otel.configure_otel()` and `madsci.common.otel.current_trace_context()`.
- Then update EventClient to use these helpers.
- Only after EventClient is migrated should managers be updated in Phase 2.

### 1.2.1 Integrate `madsci.common.otel` into EventClient

Update `src/madsci_client/madsci/client/event_client.py` (conceptual example):

```python
from madsci.common.otel import configure_otel, current_trace_context

class EventClient:
    def __init__(self, config: Optional[EventClientConfig] = None, **kwargs):
        # ... existing initialization ...

        self._otel_runtime = None
        if self.config.otel_enabled:
            self._setup_otel()

    def _setup_otel(self) -> None:
        """Initialize OpenTelemetry tracing and metrics."""
        self._otel_runtime = configure_otel(
            enabled=True,
            service_name=self.config.otel_service_name or f"madsci.{self.name}",
            service_version=getattr(self.config, "version", None) or "unknown",
        )

        # Note: OTEL SDK providers are typically process-global. Setup must be idempotent so multiple
        # EventClient instances in the same process do not fight each other.

        self._log_startup_info()  # Log that OTEL was enabled
```

### 1.2.2 Add Span Creation to Logging Methods

Creating a new span for every log call is usually too high-volume.

Recommended initial approach:

- Do *not* create spans for generic `info()` / `debug()` calls.
- Record metrics for log volume.
- Inject correlation fields (`trace_id`, `span_id`) from the *current* active span context (if any).
- Create spans around higher-level operations (workflow execution, manager endpoints, HTTP calls) instead (Phase 2).

```python
def info(self, message: str, **kwargs) -> None:
    """Log an info message."""
    event_data = self._prepare_event_data(message, EventLogLevel.INFO, **kwargs)
    event_data.update(current_trace_context())
    self._do_log(message, EventLogLevel.INFO, event_data)
    self._record_metrics("INFO", event_data.get("event_type", "log_info"))
```

### 1.2.3 Add HTTP Context Propagation

```python
from opentelemetry.propagate import inject

def _send_event_to_server(self, event: Event) -> None:
    """Send event to EventManager with trace context propagation."""
    headers = {"Content-Type": "application/json"}

    if self._otel_runtime and self._otel_runtime.enabled:
        inject(headers)  # Injects trace context (e.g., traceparent, tracestate)

    response = self._http_client.post(
        f"{self.event_server}/event",
        json=event.model_dump(mode="json"),
        headers=headers,
    )
```

Note:

- The MADSci Python clients currently use `requests` for outbound HTTP (including
  EventClient). Phase 2 should therefore prioritize `opentelemetry-instrumentation-requests`
  for client spans. `httpx` instrumentation may be added later if/when managers
  standardize on `httpx`.

### 1.2.4 Add Metrics Recording

```python
def _record_metrics(self, level: str, event_type: str) -> None:
    """Record OTEL metrics for event logging."""
    if not self._otel_manager:
        return

    self._otel_manager.event_counter.add(
        1,
        {"event.level": level, "event.type": event_type},
    )

def _record_send_latency(self, latency_ms: float, event_type: str) -> None:
    """Record event send latency."""
    if not self._otel_manager:
        return

    self._otel_manager.send_latency.record(
        latency_ms,
        {"event.type": event_type},
    )
```

## 1.3 Acceptance Criteria

- [ ] OTEL is initialized when `config.otel_enabled=True`
- [ ] Logging does not create a new span per log call (by design)
- [ ] `trace_id` and `span_id` are injected when a span is active
- [ ] `trace_id` and `span_id` are populated in Event objects
- [ ] HTTP requests to EventManager include `traceparent` header
- [ ] Metrics (counter, histogram, observable gauge) are recorded
- [ ] Exporters can be validated via in-memory exporter tests
- [ ] OTLP exporter can be configured via settings
- [ ] All tests pass
