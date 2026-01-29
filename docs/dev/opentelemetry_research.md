# OpenTelemetry Research for MADSci

> **Issue:** [#215 - Research: OpenTelemetry and the EventManager](https://github.com/AD-SDL/MADSci/issues/215)
> **Created:** January 2026
> **Status:** Complete

## Executive Summary

This document presents research findings on integrating OpenTelemetry (OTEL) with MADSci's EventClient and EventManager components. OpenTelemetry provides a vendor-neutral observability framework for distributed tracing, metrics, and logs correlation - capabilities that would significantly enhance MADSci's ability to monitor and debug complex laboratory automation workflows.

### Key Recommendations

1. **Adopt OpenTelemetry for distributed tracing** across MADSci components
2. **Integrate OTEL with structlog** using a custom processor (Phase 4 integration)
3. **Start with Console exporter** for development, plan for OTLP in production
4. **Add trace context to Event objects** to correlate logs with traces
5. **Implement basic metrics** for event counts, latency, and buffer sizes

---

## 1. OpenTelemetry Overview

### 1.1 What is OpenTelemetry?

OpenTelemetry is an observability framework and toolkit for creating, collecting, and exporting telemetry data (traces, metrics, and logs). It is:

- **Vendor-neutral**: Works with any observability backend (Jaeger, Prometheus, Datadog, etc.)
- **Standardized**: CNCF project with widespread industry adoption
- **Unified**: Single API for traces, metrics, and logs
- **Extensible**: Plugin architecture for custom exporters and processors

### 1.2 Core Concepts

#### Traces
A **trace** represents the complete journey of a request through a distributed system. It consists of:

- **Spans**: Individual units of work with start/end times, attributes, and events
- **Trace ID**: 128-bit identifier unique to the entire trace
- **Span ID**: 64-bit identifier unique to each span within a trace
- **Parent Span ID**: Links child spans to their parent

```
Trace: Experiment Execution
├── Span: WorkflowManager.submit_workflow
│   ├── Span: WorkcellManager.process_workflow
│   │   ├── Span: NodeModule.execute_action (robot_arm)
│   │   ├── Span: NodeModule.execute_action (pipette)
│   │   └── Span: DataManager.save_result
│   └── Span: EventManager.log_event
└── Span: ExperimentManager.complete_experiment
```

#### Metrics
**Metrics** are numerical measurements over time:

- **Counter**: Cumulative values that only increase (e.g., event count)
- **Gauge**: Point-in-time values that can go up/down (e.g., buffer size)
- **Histogram**: Distribution of values (e.g., latency percentiles)

#### Logs
**Logs** are timestamped text records. OTEL's Logs API allows:

- Correlation with traces via trace_id/span_id
- Structured log attributes
- Integration with existing logging frameworks

#### Context Propagation
**Context** carries trace information across process boundaries:

- **W3C Trace Context**: Standard HTTP headers (`traceparent`, `tracestate`)
- **B3 Propagation**: Alternative format used by Zipkin
- **Context Variables**: Python's `contextvars` for async context

---

## 2. OpenTelemetry Python SDK

### 2.1 Installation

```bash
# Core packages
pip install opentelemetry-api opentelemetry-sdk

# Exporters
pip install opentelemetry-exporter-otlp  # OTLP (recommended for production)
pip install opentelemetry-exporter-jaeger  # Jaeger
pip install opentelemetry-exporter-prometheus  # Prometheus metrics

# Instrumentation libraries (optional)
pip install opentelemetry-instrumentation-requests  # Auto-instrument requests
pip install opentelemetry-instrumentation-fastapi  # Auto-instrument FastAPI
pip install opentelemetry-instrumentation-pymongo  # Auto-instrument MongoDB
```

### 2.2 Basic Tracing Example

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource

# Configure the tracer provider
resource = Resource.create({
    "service.name": "madsci-event-client",
    "service.version": "1.0.0",
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Get a tracer
tracer = trace.get_tracer(__name__)

# Create spans
with tracer.start_as_current_span("log_event") as span:
    span.set_attribute("event.type", "LOG_INFO")
    span.set_attribute("event.id", "01HXYZ...")
    # ... do work ...
    span.add_event("event_sent_to_server")
```

### 2.3 Context Propagation Across Services

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract

# Client side: inject trace context into headers
def send_event_to_server(event: Event):
    headers = {}
    inject(headers)  # Adds traceparent header

    response = requests.post(
        url=f"{event_server}/event",
        json=event.model_dump(),
        headers=headers,
    )

# Server side: extract trace context from headers
from fastapi import Request

@app.post("/event")
async def log_event(request: Request, event: Event):
    context = extract(request.headers)
    with tracer.start_as_current_span("process_event", context=context):
        # This span is now a child of the client's span
        pass
```

### 2.4 Metrics Example

```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader

# Configure metrics
reader = PrometheusMetricReader()
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Get a meter
meter = metrics.get_meter(__name__)

# Create instruments
event_counter = meter.create_counter(
    name="madsci.events.total",
    description="Total number of events logged",
    unit="1",
)

event_latency = meter.create_histogram(
    name="madsci.events.latency",
    description="Event logging latency",
    unit="ms",
)

buffer_size = meter.create_observable_gauge(
    name="madsci.events.buffer_size",
    description="Current event buffer size",
    callbacks=[lambda options: [Observation(event_buffer.qsize())]],
)

# Record metrics
event_counter.add(1, {"event.type": "LOG_INFO"})
event_latency.record(15.5, {"event.type": "LOG_INFO"})
```

### 2.5 Logs Integration

```python
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

# Configure logs provider
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter())
)
set_logger_provider(logger_provider)

# Create a handler for stdlib logging
handler = LoggingHandler(
    level=logging.DEBUG,
    logger_provider=logger_provider,
)

# Attach to existing logger
logger = logging.getLogger(__name__)
logger.addHandler(handler)
```

---

## 3. Structlog + OpenTelemetry Integration

### 3.1 Native Integration Approach

Structlog provides excellent integration with OpenTelemetry through custom processors. The recommended approach is to create a processor that extracts trace context and adds it to log events.

### 3.2 Trace Context Processor

From the structlog documentation, here's the recommended pattern:

```python
from opentelemetry import trace

def add_open_telemetry_spans(_, __, event_dict):
    """Structlog processor to add OpenTelemetry trace context to logs."""
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),
        "trace_id": format(ctx.trace_id, "032x"),
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }

    return event_dict
```

### 3.3 Complete Structlog Configuration with OTEL

```python
import structlog
from opentelemetry import trace

def add_otel_context(_, __, event_dict):
    """Add OpenTelemetry trace context to log events."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict

# Configure structlog with OTEL processor
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_otel_context,  # Add OTEL trace context
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### 3.4 Per-Instance Logger with OTEL

For MADSci's EventClient (which uses per-instance configuration), we can use `structlog.wrap_logger()`:

```python
import structlog
from opentelemetry import trace

def create_otel_structlog_logger(
    name: str,
    otel_enabled: bool = True,
    output_format: str = "console",
):
    """Create a structlog logger with optional OTEL integration."""

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if otel_enabled:
        processors.append(add_otel_context)

    processors.extend([
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ])

    if output_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    stdlib_logger = logging.getLogger(name)

    return structlog.wrap_logger(
        stdlib_logger,
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        cache_logger_on_first_use=False,
    )
```

---

## 4. Distributed Tracing in MADSci

### 4.1 MADSci Architecture Overview

MADSci follows a microservices architecture where trace context should flow through:

```
Experiment Application
    │
    ├── ExperimentManager (experiments, campaigns)
    │   │
    │   └── WorkcellManager (workflow scheduling)
    │       │
    │       ├── NodeModule (robot actions)
    │       │   └── Resource Manager (allocations)
    │       │
    │       ├── EventManager (logging)
    │       │
    │       └── DataManager (data capture)
    │
    └── LocationManager (locations, attachments)
```

### 4.2 Recommended Trace Boundaries

| Component | Span Name Pattern | Attributes |
|-----------|-------------------|------------|
| ExperimentManager | `experiment.{action}` | experiment_id, campaign_id |
| WorkcellManager | `workflow.{action}` | workflow_id, step_index |
| NodeModule | `node.{action_name}` | node_id, action_id |
| EventManager | `event.log` | event_id, event_type |
| DataManager | `data.{action}` | data_id, format |
| ResourceManager | `resource.{action}` | resource_id, location_id |

### 4.3 Context Propagation Strategy

#### HTTP Headers (Between Managers)

All HTTP clients should inject trace context:

```python
from opentelemetry.propagate import inject

class MadsciHttpClient:
    def _inject_trace_context(self, headers: dict) -> dict:
        """Inject OTEL trace context into HTTP headers."""
        if self.otel_enabled:
            inject(headers)
        return headers

    def post(self, url: str, data: dict, **kwargs) -> Response:
        headers = kwargs.pop("headers", {})
        headers = self._inject_trace_context(headers)
        return self.session.post(url, json=data, headers=headers, **kwargs)
```

All FastAPI endpoints should extract context:

```python
from opentelemetry.propagate import extract
from fastapi import Request

class AbstractManagerBase:
    def _extract_trace_context(self, request: Request):
        """Extract OTEL trace context from request headers."""
        return extract(dict(request.headers))
```

#### Event Objects

Add optional trace context to Event model:

```python
class Event(MadsciBaseModel):
    # ... existing fields ...

    trace_id: Optional[str] = Field(
        default=None,
        description="OpenTelemetry trace ID for correlation",
    )
    span_id: Optional[str] = Field(
        default=None,
        description="OpenTelemetry span ID for correlation",
    )
```

### 4.4 Example: Tracing a Workflow Execution

```python
from opentelemetry import trace

tracer = trace.get_tracer("madsci.workcell_manager")

class WorkcellManager:
    async def start_workflow(self, workflow: Workflow):
        with tracer.start_as_current_span(
            "workflow.start",
            attributes={
                "workflow.id": workflow.workflow_id,
                "workflow.name": workflow.name,
                "workflow.steps": len(workflow.steps),
            }
        ) as span:
            for i, step in enumerate(workflow.steps):
                with tracer.start_as_current_span(
                    f"workflow.step.{step.action}",
                    attributes={
                        "step.index": i,
                        "step.node": step.node,
                        "step.action": step.action,
                    }
                ):
                    result = await self.execute_step(step)
                    span.add_event(
                        "step_completed",
                        attributes={"step.status": result.status},
                    )
```

---

## 5. OTEL Exporter Evaluation

### 5.1 Exporter Options

| Exporter | Use Case | Pros | Cons |
|----------|----------|------|------|
| **Console** | Development | No setup, instant feedback | Not for production |
| **OTLP** | Production | Standard protocol, works with any backend | Requires collector/backend |
| **Jaeger** | Tracing-focused | Great UI, open source | Traces only |
| **Prometheus** | Metrics-focused | Industry standard for metrics | Metrics only |
| **Zipkin** | Legacy systems | Wide compatibility | Limited features |

### 5.2 Recommended Configuration

#### Development

```python
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

# Console exporters for immediate feedback
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
metric_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(),
    export_interval_millis=5000,
)
```

#### Production

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# OTLP exporters to collector
span_processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://otel-collector:4317")
)
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4317")
)
```

### 5.3 Configuration via Environment Variables

OTEL supports standard environment variable configuration:

```bash
# Enable/disable OTEL
OTEL_SDK_DISABLED=false

# Service identification
OTEL_SERVICE_NAME=madsci-event-manager
OTEL_SERVICE_VERSION=1.0.0

# Exporter configuration
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Sampling
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # Sample 10% of traces
```

---

## 6. Integration Recommendations

### 6.1 Phase 4 Integration Plan

Since Phase 4 introduces structlog, OTEL integration should be added simultaneously:

1. **Add OTEL dependencies** to `madsci_client/pyproject.toml`:
   ```toml
   dependencies = [
       "structlog>=24.1.0",
       "opentelemetry-api>=1.20.0",
       "opentelemetry-sdk>=1.20.0",
   ]

   [project.optional-dependencies]
   otel = [
       "opentelemetry-exporter-otlp>=1.20.0",
   ]
   ```

2. **Create OTEL configuration module** (`structlog_otel.py`):
   - Trace context processor for structlog
   - Tracer and meter initialization
   - Configurable via EventClientConfig

3. **Update EventClientConfig**:
   ```python
   otel_enabled: bool = Field(
       default=False,
       description="Enable OpenTelemetry integration",
   )
   otel_service_name: Optional[str] = Field(
       default=None,
       description="Override service name for OTEL",
   )
   otel_exporter: Literal["console", "otlp", "none"] = Field(
       default="console",
       description="OTEL exporter type",
   )
   ```

4. **Add trace context to Event model** (optional field for backward compatibility)

5. **Instrument HTTP client** in EventClient for context propagation

### 6.2 EventClient Integration Points

```python
class EventClient:
    def __init__(self, config: EventClientConfig):
        # ... existing init ...

        if config.otel_enabled:
            self._setup_otel()

    def _setup_otel(self):
        """Initialize OpenTelemetry tracing and metrics."""
        from opentelemetry import trace, metrics

        self._tracer = trace.get_tracer(
            "madsci.event_client",
            tracer_provider=self._get_tracer_provider(),
        )
        self._meter = metrics.get_meter(
            "madsci.event_client",
            meter_provider=self._get_meter_provider(),
        )

        # Create metrics instruments
        self._event_counter = self._meter.create_counter(
            "madsci.events.logged",
            description="Number of events logged",
        )
        self._event_latency = self._meter.create_histogram(
            "madsci.events.send_latency_ms",
            description="Latency of sending events to server",
        )

    def log(self, event: Event, level: int = None):
        with self._tracer.start_as_current_span(
            "event.log",
            attributes={
                "event.type": event.event_type.value,
                "event.level": event.log_level.name,
            }
        ) as span:
            # Inject trace context into event
            ctx = span.get_span_context()
            event.trace_id = format(ctx.trace_id, "032x")
            event.span_id = format(ctx.span_id, "016x")

            # Log the event
            self._logger.log(level, event.model_dump_json())

            # Record metrics
            self._event_counter.add(1, {"event.type": event.event_type.value})

            # Send to server
            if self.event_server:
                start = time.time()
                self._send_event_to_event_server(event)
                self._event_latency.record(
                    (time.time() - start) * 1000,
                    {"event.type": event.event_type.value},
                )
```

### 6.3 EventManager Integration Points

```python
class EventManager(AbstractManagerBase):
    def initialize(self):
        super().initialize()

        if self.settings.otel_enabled:
            self._setup_otel()

    @post("/event")
    async def log_event(self, request: Request, event: Event):
        # Extract trace context from request headers
        context = extract(dict(request.headers))

        with self._tracer.start_as_current_span(
            "event.receive",
            context=context,
            attributes={
                "event.id": event.event_id,
                "event.type": event.event_type.value,
            }
        ):
            # Process event with trace context
            return await self._process_event(event)
```

---

## 7. Recommended Metrics

### 7.1 EventClient Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `madsci.events.logged` | Counter | Total events logged | event_type, level |
| `madsci.events.send_latency_ms` | Histogram | Latency sending to server | event_type |
| `madsci.events.buffer_size` | Gauge | Current buffer queue size | - |
| `madsci.events.send_errors` | Counter | Failed sends to server | error_type |
| `madsci.events.retries` | Counter | Event send retries | - |

### 7.2 EventManager Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `madsci.event_manager.events_received` | Counter | Events received | event_type |
| `madsci.event_manager.events_stored` | Counter | Events stored in DB | - |
| `madsci.event_manager.db_latency_ms` | Histogram | MongoDB operation latency | operation |
| `madsci.event_manager.alerts_sent` | Counter | Email alerts sent | - |

---

## 8. Trade-offs and Considerations

### 8.1 Performance Impact

**Overhead:**
- Span creation: ~1-5 microseconds per span
- Context propagation: ~10-50 microseconds per HTTP request
- Metric recording: ~100 nanoseconds per metric

**Mitigation:**
- Use sampling in production (e.g., 10% of traces)
- Batch span/metric export (default behavior)
- Make OTEL optional via configuration flag

### 8.2 Dependency Considerations

**New Dependencies:**
- `opentelemetry-api`: ~200KB, no transitive deps
- `opentelemetry-sdk`: ~500KB, includes protobuf
- `opentelemetry-exporter-otlp`: ~300KB (optional)

**Compatibility:**
- Python 3.8+ required (MADSci already requires 3.9+)
- Works with existing logging setup
- Non-breaking addition to Event model

### 8.3 Deployment Considerations

**Development:**
- Console exporter requires no infrastructure
- Traces/metrics printed to stdout

**Production:**
- Requires OTEL Collector or direct backend
- Recommended: Deploy OTEL Collector as sidecar
- Popular backends: Jaeger, Tempo, Honeycomb, Datadog

---

## 9. PoC Implementation Plan

### 9.1 PoC Scope

The proof-of-concept (branch: `feature/otel-poc`) will demonstrate:

1. **Basic tracing in EventClient**
   - Span creation for log operations
   - Trace context injection into HTTP requests

2. **Log correlation**
   - Structlog processor adding trace_id/span_id
   - Event model with optional trace fields

3. **Basic metrics**
   - Event counter by type
   - Send latency histogram
   - Buffer size gauge

4. **Console exporter** for easy demonstration

### 9.2 PoC Files

```
src/madsci_client/madsci/client/
├── otel_config.py          # OTEL configuration and setup
├── otel_processors.py      # Structlog processors for OTEL
└── event_client.py         # Updated with OTEL integration

src/madsci_common/madsci/common/types/
└── event_types.py          # Event model with trace fields

examples/
└── otel_demo.py            # Demo script showing OTEL in action
```

### 9.3 PoC Assessment Criteria

After PoC implementation, evaluate:

| Criteria | Pass Condition |
|----------|----------------|
| Trace visibility | Spans appear in console output |
| Log correlation | trace_id appears in log entries |
| Context propagation | Child spans have correct parent |
| Metrics collection | Counters and histograms record values |
| Performance | <5% overhead in benchmarks |
| Code cleanliness | Clean separation, easy to merge |

---

## 10. References

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Python SDK](https://github.com/open-telemetry/opentelemetry-python)
- [Structlog OpenTelemetry Integration](https://www.structlog.org/en/stable/frameworks.html#opentelemetry)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

---

## Appendix A: Quick Reference

### A.1 Trace Context Format

```
traceparent: 00-{trace_id}-{span_id}-{trace_flags}
            │   │           │         └── 01 = sampled
            │   │           └── 16 hex chars (64-bit span ID)
            │   └── 32 hex chars (128-bit trace ID)
            └── version (always 00)

Example:
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

### A.2 Minimal Integration Checklist

- [ ] Add `opentelemetry-api` and `opentelemetry-sdk` dependencies
- [ ] Create tracer provider with appropriate exporter
- [ ] Add structlog processor for trace context
- [ ] Instrument EventClient.log() with spans
- [ ] Inject trace context into HTTP headers
- [ ] Extract trace context in EventManager endpoints
- [ ] Add trace_id/span_id fields to Event model
- [ ] Create basic metrics (counter, histogram)
- [ ] Add otel_enabled config option
- [ ] Document configuration options
