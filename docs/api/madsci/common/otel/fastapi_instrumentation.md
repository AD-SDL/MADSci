Module madsci.common.otel.fastapi_instrumentation
=================================================
FastAPI/ASGI auto-instrumentation.

Best-effort helpers that activate OTEL request spans when the optional
instrumentation dependencies are installed.

Functions
---------

`instrument_fastapi(app: FastAPI, *, enabled: bool = True) ‑> bool`
:   Enable OpenTelemetry auto-instrumentation for FastAPI.

    Returns True when instrumentation was applied, otherwise False.
