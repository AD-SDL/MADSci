"""Local audit-log fallback for consuming managers.

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
"""

from __future__ import annotations

import contextlib
import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_LOG_PATH = ".madsci/audit/auth-fallback.log"
DEFAULT_MAX_BYTES = 100 * 1024 * 1024  # 100 MB
DEFAULT_DRAIN_INTERVAL_SECONDS = 60.0


class AuthAuditFallback:
    """Append-only local fallback for auth audit events."""

    def __init__(
        self,
        *,
        log_path: Optional[str] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        drain_interval: float = DEFAULT_DRAIN_INTERVAL_SECONDS,
        deliver: Optional[Callable[[dict[str, Any]], bool]] = None,
    ) -> None:
        """Configure the fallback log path, size bound, drain interval, and delivery callable."""
        self._log_path = Path(log_path or DEFAULT_LOG_PATH)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max_bytes
        self._drain_interval = drain_interval
        self._deliver = deliver
        self._lock = threading.RLock()

    def append(self, event: dict[str, Any]) -> None:
        """Persist an event to the local fallback log."""
        with self._lock:
            self._rotate_if_needed()
            with self._log_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(event) + "\n")

    def _rotate_if_needed(self) -> None:
        try:
            size = self._log_path.stat().st_size
        except FileNotFoundError:
            return
        if size < self._max_bytes:
            return
        # Rotate: rename current to .1 (overwriting any existing) and emit a warning
        rotated = self._log_path.with_suffix(self._log_path.suffix + ".1")
        with contextlib.suppress(OSError):
            self._log_path.replace(rotated)
        logger.warning(
            "Local auth audit fallback exceeded %d bytes; rotated %s -> %s. "
            "Operators should investigate Auth Manager connectivity and "
            "consider upsizing local_audit_log_max_bytes (see "
            "docs/guides/auth_operator.md).",
            self._max_bytes,
            self._log_path,
            rotated,
        )

    def drain(self) -> int:
        """Attempt to deliver all locally-queued events. Returns count drained."""
        if self._deliver is None:
            return 0
        with self._lock:
            if not self._log_path.exists():
                return 0
            with self._log_path.open("r", encoding="utf-8") as fp:
                lines = fp.readlines()
            delivered = 0
            still_queued: list[str] = []
            for raw_line in lines:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                try:
                    ok = self._deliver(event)
                except Exception:
                    ok = False
                if ok:
                    delivered += 1
                else:
                    still_queued.append(stripped)
            if still_queued:
                with self._log_path.open("w", encoding="utf-8") as fp:
                    fp.write("\n".join(still_queued) + "\n")
            else:
                self._log_path.unlink(missing_ok=True)
            return delivered


__all__ = [
    "DEFAULT_DRAIN_INTERVAL_SECONDS",
    "DEFAULT_LOG_PATH",
    "DEFAULT_MAX_BYTES",
    "AuthAuditFallback",
]
