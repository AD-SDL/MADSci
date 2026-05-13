"""Deny-list service for revoked access-token jtis.

Revoked jtis are persisted to ``revoked_access_tokens`` and cached in memory
for fast read at the ``GET /deny-list`` endpoint. The cache is hydrated from
the database on startup so revocations survive Auth Manager restarts.

Entries whose ``exp`` is in the past are evicted both from the in-memory set
and from the database, bounding the list size to currently-revoked-and-still-
unexpired tokens.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from madsci.auth_manager.tables import RevokedAccessTokenTable
from sqlmodel import Session, delete, select


class DenyListService:
    """Persistent jti deny-list with in-memory cache and ETag support."""

    def __init__(self, engine: Any, *, persist_grace_seconds: int = 300) -> None:
        """Bind the deny-list to a SQLAlchemy engine and hydrate from the table."""
        self._engine = engine
        self._persist_grace = persist_grace_seconds
        self._lock = threading.RLock()
        # jti -> exp (unix epoch seconds)
        self._cache: dict[str, int] = {}
        self._etag = "0"
        self._hydrate()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _hydrate(self) -> None:
        """Rebuild the in-memory cache from the persisted table."""
        with self._lock:
            self._cache.clear()
            now = datetime.now(timezone.utc)
            with Session(self._engine) as session:
                rows = session.exec(select(RevokedAccessTokenTable)).all()
                for row in rows:
                    exp = row.exp
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp >= now:
                        self._cache[row.jti] = int(exp.timestamp())
            self._recompute_etag()

    def _recompute_etag(self) -> None:
        # Stable hash of (jti, exp) tuples so consumers can use If-None-Match.
        items = sorted(self._cache.items())
        h = hashlib.sha256(json.dumps(items, sort_keys=True).encode("utf-8"))
        self._etag = h.hexdigest()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def revoke(self, jti: str, exp_unix: int) -> None:
        """Revoke a jti with the given expiration (unix seconds)."""
        exp_dt = datetime.fromtimestamp(exp_unix, tz=timezone.utc)
        with self._lock, Session(self._engine) as session:
            existing = session.get(RevokedAccessTokenTable, jti)
            if existing is None:
                session.add(RevokedAccessTokenTable(jti=jti, exp=exp_dt))
                session.commit()
            self._cache[jti] = exp_unix
            self._recompute_etag()

    def is_revoked(self, jti: str) -> bool:
        """Return True if ``jti`` is in the deny-list and not yet expired."""
        with self._lock:
            exp = self._cache.get(jti)
            if exp is None:
                return False
            if exp < int(datetime.now(timezone.utc).timestamp()):
                # lazily evict
                self._cache.pop(jti, None)
                self._recompute_etag()
                return False
            return True

    def evict_expired(self) -> int:
        """Evict expired entries from cache and DB. Returns count removed."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self._persist_grace)
        removed = 0
        with self._lock:
            for jti, exp_unix in list(self._cache.items()):
                if exp_unix < int(now.timestamp()):
                    self._cache.pop(jti, None)
                    removed += 1
            with Session(self._engine) as session:
                session.exec(
                    delete(RevokedAccessTokenTable).where(
                        RevokedAccessTokenTable.exp < cutoff
                    )
                )
                session.commit()
            if removed:
                self._recompute_etag()
        return removed

    # ------------------------------------------------------------------
    # Read API for /deny-list endpoint
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Snapshot for the ``GET /deny-list`` response."""
        with self._lock:
            return {
                "etag": self._etag,
                "entries": [
                    {"jti": jti, "exp": exp_unix}
                    for jti, exp_unix in sorted(self._cache.items())
                ],
            }

    @property
    def etag(self) -> str:
        """Current ETag of the deny-list snapshot (sha256 over (jti, exp) tuples)."""
        with self._lock:
            return self._etag
