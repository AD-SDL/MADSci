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

__all__ = [
    "OtelBootstrapConfig",
    "OtelRuntime",
    "collect_metrics",
    "configure_otel",
    "current_trace_context",
    "get_otel_runtime",
    "inject_headers",
    "instrument_fastapi",
    "instrument_requests",
]
