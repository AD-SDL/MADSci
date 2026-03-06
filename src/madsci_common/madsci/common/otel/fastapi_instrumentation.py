"""FastAPI/ASGI auto-instrumentation.

Best-effort helpers that activate OTEL request spans when the optional
instrumentation dependencies are installed.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

_logger = logging.getLogger(__name__)


def instrument_fastapi(app: FastAPI, *, enabled: bool = True) -> bool:
    """Enable OpenTelemetry auto-instrumentation for FastAPI.

    Returns True when instrumentation was applied, otherwise False.
    """

    if not enabled:
        return False

    try:
        from opentelemetry.instrumentation.fastapi import (  # noqa: PLC0415
            FastAPIInstrumentor,
        )

        FastAPIInstrumentor.instrument_app(app)
        return True
    except Exception:
        _logger.debug("FastAPI instrumentation unavailable", exc_info=True)
        return False
