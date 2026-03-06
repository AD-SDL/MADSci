"""OpenTelemetry context propagation helpers.

These helpers keep OTEL header propagation out of client/manager code so all
components share one consistent behavior.
"""

from __future__ import annotations

from typing import MutableMapping

from opentelemetry.propagate import inject


def inject_headers(headers: MutableMapping[str, str]) -> None:
    """Inject trace context into outbound HTTP headers."""

    inject(headers)
