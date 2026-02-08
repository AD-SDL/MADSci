Module madsci.common.otel.propagation
=====================================
OpenTelemetry context propagation helpers.

These helpers keep OTEL header propagation out of client/manager code so all
components share one consistent behavior.

Functions
---------

`inject_headers(headers: MutableMapping[str, str]) ‑> None`
:   Inject trace context into outbound HTTP headers.
