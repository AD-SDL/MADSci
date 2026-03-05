"""Requests auto-instrumentation.

This module provides best-effort initialization for requests client spans.
It is safe to call even when the optional instrumentation dependency is not
installed.
"""

from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


def instrument_requests(*, enabled: bool = True) -> bool:
    """Enable OpenTelemetry auto-instrumentation for `requests`.

    Returns True when instrumentation was applied, otherwise False.
    """

    if not enabled:
        return False

    try:
        from opentelemetry.instrumentation.requests import (  # noqa: PLC0415
            RequestsInstrumentor,
        )

        RequestsInstrumentor().instrument()
        return True
    except Exception:
        _logger.debug("Requests instrumentation unavailable", exc_info=True)
        return False
