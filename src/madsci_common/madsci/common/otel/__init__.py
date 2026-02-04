"""OpenTelemetry bootstrap and helpers.

This package provides a single canonical OpenTelemetry configuration surface
for MADSci processes.
"""

from .bootstrap import (
    OtelBootstrapConfig,
    OtelRuntime,
    configure_otel,
    current_trace_context,
)
from .propagation import inject_headers

__all__ = [
    "OtelBootstrapConfig",
    "OtelRuntime",
    "configure_otel",
    "current_trace_context",
    "inject_headers",
]
