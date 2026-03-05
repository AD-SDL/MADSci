Module madsci.common.otel.requests_instrumentation
==================================================
Requests auto-instrumentation.

This module provides best-effort initialization for requests client spans.
It is safe to call even when the optional instrumentation dependency is not
installed.

Functions
---------

`instrument_requests(*, enabled: bool = True) ‑> bool`
:   Enable OpenTelemetry auto-instrumentation for `requests`.
    
    Returns True when instrumentation was applied, otherwise False.