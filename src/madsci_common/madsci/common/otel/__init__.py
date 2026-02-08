"""OpenTelemetry bootstrap and helpers.

This package provides a single canonical OpenTelemetry configuration surface
for MADSci processes.
"""

from .bootstrap import (
    OtelBootstrapConfig,
    OtelRuntime,
    collect_metrics,
    configure_otel,
    current_trace_context,
    get_otel_runtime,
)
from .fastapi_instrumentation import instrument_fastapi
from .propagation import inject_headers
from .requests_instrumentation import instrument_requests
from .tracing import (
    add_span_event,
    get_current_span,
    get_tracer,
    is_span_recording,
    safe_span_context,
    set_span_attributes,
    set_span_error,
    span_context,
    traced_class,
    with_span,
)

__all__ = [
    "OtelBootstrapConfig",
    "OtelRuntime",
    "add_span_event",
    "collect_metrics",
    "configure_otel",
    "current_trace_context",
    "get_current_span",
    "get_otel_runtime",
    "get_tracer",
    "inject_headers",
    "instrument_fastapi",
    "instrument_requests",
    "is_span_recording",
    "safe_span_context",
    "set_span_attributes",
    "set_span_error",
    "span_context",
    "traced_class",
    "with_span",
]
