# Phase 2: Manager-Level Tracing

**Estimated Effort:** Large (5-7 days)
**Breaking Changes:** None

## Goals

- Add OTEL tracing to all manager services
- Ensure trace context is extracted from incoming HTTP requests (by ASGI/FastAPI instrumentation when enabled)
- Propagate trace context in outgoing HTTP requests
- Create meaningful spans for manager operations

## Prerequisite: HTTP Client Instrumentation Choice (Normative)

MADSci currently uses both `requests` (sync; primary for clients) and `httpx`
(async; used in some services/tests).

Rules:

- Phase 2 must instrument the HTTP client(s) actually used for cross-service
  calls. As of this plan revision, prioritize `requests` instrumentation first.
- Add `httpx` instrumentation only if/when manager outbound calls standardize on
  `httpx`.

Approach decision (this plan):

- Use auto-instrumentation for the HTTP boundary (server + client).
- Add manual, domain-level spans for lab logic (workflows, steps, node actions, resource operations).

Non-goal: relying on `opentelemetry-api` alone for manager tracing. Managers should participate in the same OTEL SDK setup strategy as EventClient so exporting/sampling are consistent.

## Definition: "OTEL Enabled" (Managers)

For Phase 2, "OTEL enabled" means:

- The manager process calls the shared OTEL bootstrap during startup (installing SDK providers/exporters).
- The server request span is created automatically via ASGI/FastAPI auto-instrumentation (using inbound context).
- Outbound HTTP calls create client spans automatically via HTTP client auto-instrumentation.
- Manual domain spans are created as child spans under the active context.

Obtaining a tracer via `trace.get_tracer(...)` without configuring SDK providers is treated as "not fully enabled"
(it will generally behave as a no-op).

## 2.0.0 Shared OTEL Bootstrap (Recommended)

To avoid duplicating OTEL expertise across managers/nodes/clients, create a small common library in `madsci_common` responsible for:

- Reading OTEL configuration (prefer upstream OTEL env vars)
- Creating and installing SDK providers (tracing + metrics)
- Creating a tracer/meter for the current service
- Providing helpers for context injection/extraction and current trace correlation
- Clean shutdown/flush

Proposed location:

- `src/madsci_common/madsci/common/otel/` (or similar), used by both `madsci_client` and manager services.

The target end-state is a single canonical module in `madsci.common.otel`.

All manager OTEL behavior must follow the configuration precedence rules defined in
`docs/dev/opentelemetry_integration_plan/00_principles.md`.

Recommendation: start this refactor in Phase 1 so both EventClient and managers rely on the same bootstrap and so SDK
setup is not duplicated.

Target end-state (required):

- All OTEL SDK/provider/exporter configuration lives in `madsci.common.otel`.
- All other packages (clients, managers, nodes) import OTEL functionality only from `madsci.common.otel`.
- Any remaining `madsci_client` OTEL module should be removed after migration.

### 2.0.0.1 Proposed API Surface

The shared OTEL package should provide one small, stable interface that managers/clients can use without being OTEL experts.

```python
from dataclasses import dataclass
from typing import Optional

from opentelemetry import metrics, trace


@dataclass
class OtelRuntime:
    """Handle to OTEL facilities for a running service."""

    enabled: bool
    service_name: str
    tracer: Optional[trace.Tracer]
    meter: Optional[metrics.Meter]

    def shutdown(self) -> None:
        """Flush and shutdown providers (TracerProvider and MeterProvider)."""


def configure_otel(
    *,
    enabled: bool,
    service_name: str,
    service_version: str | None = None,
    test_mode: bool = False,
) -> OtelRuntime:
    """Configure OTEL SDK/providers using upstream env var conventions."""

    # test_mode=True installs in-memory span/metric exporters/readers and
    # disables background export threads for deterministic unit tests.


def current_trace_context() -> dict[str, str]:
    """Return {"trace_id": "...", "span_id": "..."} if a span is active."""


def inject_headers(headers: dict[str, str]) -> None:
    """Inject W3C trace context into outbound headers."""


def extract_context_from_headers(headers: dict[str, str]):
    """Extract context from inbound headers."""
```

## 2.0.1 Instrumentation Strategy (Chosen)

This plan uses a hybrid strategy:

1. HTTP boundary (auto-instrumented)

   - Server spans are created automatically for all FastAPI/ASGI requests.
   - Client spans are created automatically for outbound HTTP calls.
   - This ensures consistent distributed traces even if developers forget to manually add spans.

2. Domain spans (manual, developer-authored)

   - Managers add child spans for meaningful operations (e.g., `workflow.execute`, `workflow.step`, `node.action`).
   - Domain spans must follow the Span Attribute Cardinality Policy.

Developer tooling requirement:

- `madsci.common.otel` must provide small helpers/context managers to make adding domain spans simple and consistent.

Non-goal:

- Manually starting a "request span" inside each endpoint. With auto-instrumentation enabled, manual endpoint spans
  should be used only as child spans when they represent a real sub-operation.

Notes:

- `configure_otel()` should be the only place that touches SDK/exporter/provider setup.
- `current_trace_context()` should replace any ad-hoc formatting of trace/span IDs.
- `inject_headers()` / `extract_context_from_headers()` should be the canonical propagation helpers.

## 2.0 Async Context Propagation Notes

Manager endpoints in MADSci are a mix of `def` and `async def` (e.g., EventManager endpoints are async; WorkcellManager is mixed). The instrumentation must:

- Work correctly for both sync and async endpoints
- Preserve context across `await` boundaries
 - Prefer request-header extraction as the primary source of inbound context

### 2.0.1 Request Spans and Parentage (Normative)

When ASGI/FastAPI auto-instrumentation is enabled, the request span is created
and parented automatically based on inbound headers.

Rules:

- Do not manually extract headers inside each endpoint just to parent child
  spans. Start child spans under the current context.
- Use manual extraction only for background tasks, thread/task handoff, or when
  you explicitly need a parent that is not the current span.

Recommended helper pattern (pseudo-code):

```python
from contextlib import nullcontext

from opentelemetry.propagate import extract

def _span_from_request(self, operation: str, request: Request | None, **attrs):
    if not self._tracer:
        return nullcontext()

    if request is None:
        return self._tracer.start_as_current_span(operation, attributes=attrs)

    # Only do this in places where you are *not* already inside an auto-instrumented
    # request span (e.g., background jobs). In normal endpoints, prefer relying on
    # the current context set by ASGI instrumentation.
    ctx = extract(dict(request.headers))
    return self._tracer.start_as_current_span(operation, context=ctx, attributes=attrs)
```

Note: `dict(request.headers)` is typically sufficient, but FastAPI/Starlette headers are case-insensitive and may
contain multi-values. If edge cases appear, switch to using an OTEL-provided header getter to preserve semantics.

Note: When server auto-instrumentation is enabled, inbound context extraction is handled for the request span.
Manual extraction helpers are still useful when creating spans in background tasks or when you need to explicitly set
a parent context that is not the current span.

## 2.1 Test Specifications

Create `src/madsci_common/tests/test_manager_otel.py`:

```python
class TestManagerBaseOtel:
    """Test OTEL integration in AbstractManagerBase."""

    def test_request_context_parentage_respected(self, mock_manager):
        """Test that inbound request context is respected for span parentage.

        When ASGI/FastAPI auto-instrumentation is enabled, the request span is
        responsible for header extraction. Manager domain spans should be
        children of the active request span.
        """

    def test_child_spans_created_for_operations(self, mock_manager):
        """Test that manager operations create child spans."""

    def test_span_attributes_include_operation_details(self, mock_manager):
        """Test that spans include relevant operation attributes."""


class TestEventManagerOtel:
    """Test OTEL in EventManager."""

    def test_event_receive_creates_span(self, mock_event_manager):
        """Test that receiving an event creates a span."""

    def test_trace_context_from_event_used(self, mock_event_manager):
        """Test that trace_id/span_id from Event are used for correlation."""


class TestWorkcellManagerOtel:
    """Test OTEL in WorkcellManager."""

    def test_workflow_execution_creates_trace(self, mock_workcell_manager):
        """Test that workflow execution creates a complete trace."""

    def test_step_execution_creates_child_spans(self, mock_workcell_manager):
        """Test that each workflow step creates a child span."""

    def test_node_action_calls_propagate_context(self, mock_workcell_manager):
        """Test that calls to nodes include trace context."""
```

## 2.2 Implementation Tasks

### 2.2.1 Add OTEL Support to AbstractManagerBase

Update `src/madsci_common/madsci/common/manager_base.py`:

```python
from opentelemetry import trace
from opentelemetry.propagate import extract

# Import the shared OTEL bootstrap from madsci.common.otel
from madsci.common.otel import OtelRuntime, configure_otel

class AbstractManagerBase(MadsciClientMixin, Generic[SettingsT, DefinitionT], Routable):
    _otel_runtime: Optional[OtelRuntime] = None
    _tracer: Optional[trace.Tracer] = None

    def _setup_otel(self) -> None:
        """Set up OpenTelemetry for this manager.

        This method initializes the OTEL SDK via the shared bootstrap, ensuring
        consistent configuration across all MADSci components.
        """
        if not self.settings.otel_enabled:
            return

        try:
            # Initialize SDK via shared bootstrap (idempotent, process-global)
            self._otel_runtime = configure_otel(
                enabled=True,
                service_name=self.settings.otel_service_name
                or f"madsci.{self.__class__.__name__.lower()}",
                service_version=getattr(self, "version", None),
            )
            self._tracer = self._otel_runtime.tracer

            self.logger.info(
                "OpenTelemetry initialized",
                otel_enabled=True,
                service_name=self._otel_runtime.service_name,
            )
        except Exception as e:
            self.logger.warning(
                "OTEL setup failed, continuing without tracing",
                error=str(e),
                exc_info=True,
            )
            self._otel_runtime = None
            self._tracer = None

    def shutdown(self) -> None:
        """Clean shutdown with telemetry flush."""
        if self._otel_runtime:
            self._otel_runtime.shutdown()
        # ... existing shutdown logic ...

    def _extract_trace_context(self, request: Request):
        """Extract OTEL trace context from request headers.

        Prefer relying on ASGI/FastAPI auto-instrumentation for endpoint request
        handling. This helper is primarily for background tasks or explicit
        parenting where there is no current request span.
        """

        return extract(dict(request.headers))

    def _create_operation_span(
        self,
        operation_name: str,
        request: Optional[Request] = None,
        **attributes,
    ):
        """Create a span for a manager operation."""
        if not self._tracer:
            return nullcontext()

        context = None
        if request:
            # Only use manual extraction when you are not already inside an
            # auto-instrumented request span.
            context = self._extract_trace_context(request)

        return self._tracer.start_as_current_span(
            operation_name,
            context=context,
            attributes=attributes,
        )
```

Span attribute guidance:

- Follow `docs/dev/opentelemetry_integration_plan/00_principles.md` (Span Attribute Cardinality Policy).
- Prefer low-cardinality operation metadata on spans.
- Record identifiers (ULIDs) in EventClient logs/events instead of span attributes.

### 2.2.2 Add Manager Settings for OTEL

Update manager settings classes to include OTEL configuration:

```python
class MadsciBaseSettings(BaseSettings):
    # ... existing fields ...

    otel_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing for this manager",
    )
    otel_service_name: Optional[str] = Field(
        default=None,
        description="Override service name for OTEL (defaults to manager name)",
    )
    otel_exporter: Literal["console", "otlp", "none"] = Field(
        default="console",
        description="OTEL exporter type",
    )
    otel_endpoint: Optional[str] = Field(
        default=None,
        description="OTLP exporter endpoint (e.g., http://otel-collector:4317)",
    )
```

### 2.2.3 Instrument Key Manager Endpoints

Example for EventManager (`src/madsci_event_manager/madsci/event_manager/event_server.py`):

```python
@self.app.post("/event")
async def log_event(self, request: Request, event: Event):
    with self._create_operation_span(
        "event.receive",
        request=request,
        **{
            "event.type": event.event_type.value,
            "event.level": event.log_level.name if event.log_level else "INFO",
        },
    ) as span:
        # If Event includes trace correlation fields, optionally add a link.
        # Note: constructing a valid SpanContext requires trace_flags/state; treat
        # this as conceptual pseudo-code and prefer SDK helpers in real code.
        if event.trace_id and event.span_id:
            ...

        result = await self._store_event(event)
        span.set_attribute("event.stored", True)
        return result
```

Example for WorkcellManager workflow execution:

```python
async def execute_workflow(self, workflow: Workflow, request: Request):
    with self._create_operation_span(
        "workflow.execute",
        request=request,
        **{
            "workflow.step_count": len(workflow.steps),
        },
    ) as workflow_span:
        for i, step in enumerate(workflow.steps):
            with self._tracer.start_as_current_span(
                f"workflow.step.{step.action}",
                attributes={
                    "step.index": i,
                    "step.node": step.node,
                    "step.action": step.action,
                },
            ) as step_span:
                result = await self._execute_step(step)
                step_span.set_attribute("step.status", result.status.value)

Note: `workflow.workflow_id` and similar identifiers should be logged via EventClient (with trace correlation)
instead of placed on spans as attributes.
```

## 2.3 Manager-Specific Instrumentation

| Manager | Key Operations to Trace |
|---------|------------------------|
| EventManager | `event.receive`, `event.query`, `event.archive` |
| WorkcellManager | `workflow.execute`, `workflow.step.*`, `node.action` |
| ExperimentManager | `experiment.create`, `experiment.start`, `experiment.complete` |
| ResourceManager | `resource.allocate`, `resource.release`, `resource.query` |
| DataManager | `data.save`, `data.query`, `data.export` |
| LocationManager | `location.create`, `attachment.create`, `reference.resolve` |
| LabManager (Squid) | `lab.start`, `lab.stop`, `manager.health` |

## 2.4 Acceptance Criteria

Progress (Implementation Notes, Feb 2026):

- AbstractManagerBase now bootstraps OTEL when `settings.otel_enabled=True`:
  - `src/madsci_common/madsci/common/manager_base.py`
- Added best-effort outbound HTTP client auto-instrumentation (requests):
  - Helper: `src/madsci_common/madsci/common/otel/requests_instrumentation.py`
  - Export: `madsci.common.otel.instrument_requests`
- Added best-effort inbound HTTP server auto-instrumentation (FastAPI):
  - Helper: `src/madsci_common/madsci/common/otel/fastapi_instrumentation.py`
  - Export: `madsci.common.otel.instrument_fastapi`
- Added a small domain-span helper for managers:
  - `AbstractManagerBase.span(name, attributes=...)`
- Added first manager domain span:
  - EventManager `/event` endpoint wraps inserts in `event.receive` span
    - `src/madsci_event_manager/madsci/event_manager/event_server.py`
- Added WorkcellManager domain spans:
  - Workflow submission/enqueue wraps in `workflow.execute` span
    - `src/madsci_workcell_manager/madsci/workcell_manager/workcell_server.py`
  - Engine step execution wraps in `workflow.step` span
    - `src/madsci_workcell_manager/madsci/workcell_manager/workcell_engine.py`
  - Node dispatch wraps in `node.action` span
    - `src/madsci_workcell_manager/madsci/workcell_manager/workcell_engine.py`
- Added DataManager datapoint ingestion span:
  - `/datapoint` wraps create/insert in `data.save` span
    - `src/madsci_data_manager/madsci/data_manager/data_server.py`
- Added ResourceManager domain spans:
  - Resource lifecycle + query endpoints wrap in `resource.*` spans
    - `src/madsci_resource_manager/madsci/resource_manager/resource_server.py`
- Added LocationManager domain spans:
  - Location create wraps in `location.create` span
  - Attach resource wraps in `attachment.create` span
  - Transfer planning wraps in `transfer.plan` span
    - `src/madsci_location_manager/madsci/location_manager/location_server.py`
- Optional deps for instrumentation added:
  - `src/madsci_common/pyproject.toml` (`otel-instrumentation` extra)

Acceptance Criteria:

- [x] AbstractManagerBase supports OTEL configuration (best-effort, optional)
- [x] Trace context is extracted from incoming requests via FastAPI auto-instrumentation (when installed/enabled)
- [~] Key operations create spans with meaningful attributes (EventManager + WorkcellManager started)
- [x] Cross-manager/client calls propagate trace context (requests instrumentation + existing header injection in EventClient)
- [~] Managers reuse a previously-configured process-global OTEL runtime when available
- [x] Manager health endpoint reports OTEL status when enabled
- [x] All manager tests pass (common + event manager)

## 2.5 OTEL Status and Health Checks

Add a lightweight OTEL status report (no external calls) to manager health output:

- `otel.enabled` (bool)
- `otel.exporter_type` (string)
- `otel.endpoint` (string or null)

This should not fail health checks if OTEL is unavailable; it should be informational.
