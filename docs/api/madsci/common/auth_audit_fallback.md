Module madsci.common.auth_audit_fallback
========================================
Local audit-log fallback for consuming managers.

When a consuming manager cannot deliver an authentication-related audit
event to the Auth Manager (network partition, 5xx, etc.), the event is
appended to a local on-disk log. A background drain attempts re-delivery on
a configurable interval; events are removed locally only after the Auth
Manager confirms persistence.

The local log is bounded by a configurable max-size; when exceeded, the
oldest segment is rotated out and a structured warning event is emitted so
operators can upsize before bound-bites cause silent loss.

This module deliberately avoids any direct dependency on ``madsci.client``
so it can be imported by ``madsci.common.auth_middleware`` without creating
a circular dependency.

Classes
-------

`AuthAuditFallback(*, log_path: Optional[str] = None, max_bytes: int = 104857600, drain_interval: float = 60.0, deliver: Optional[Callable[[dict[str, Any]], bool]] = None)`
:   Append-only local fallback for auth audit events.
    
    Configure the fallback log path, size bound, drain interval, and delivery callable.

    ### Methods

    `append(self, event: dict[str, Any]) ‑> None`
    :   Persist an event to the local fallback log.

    `drain(self) ‑> int`
    :   Attempt to deliver all locally-queued events. Returns count drained.