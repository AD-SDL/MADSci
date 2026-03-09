"""In-memory drop-in replacements for Redis, pottery.RedisDict, pottery.RedisList, and pottery.Redlock.

These classes mirror the interfaces used by WorkcellStateHandler and LocationStateHandler,
enabling the MADSci stack to run without a Redis server. All classes are thread-safe.

Usage::

    client = InMemoryRedisClient()
    d = InMemoryRedisDict(key="my:key", redis=client)
    d["foo"] = "bar"
    assert d["foo"] == "bar"
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, MutableMapping
from typing import Any, ClassVar, Optional

# ---------------------------------------------------------------------------
# Module-level registries keyed by (client_id, key) so that multiple
# InMemoryRedisDict / InMemoryRedisList instances with the **same** key and
# client share the same underlying data **and lock** — exactly like Redis does.
# Each entry is a (data, lock) tuple so that all instances sharing a key
# synchronise on the same lock.
# ---------------------------------------------------------------------------
_dict_registry: dict[tuple[int, str], tuple[dict[str, Any], threading.Lock]] = {}
_dict_registry_lock = threading.Lock()

_list_registry: dict[tuple[int, str], tuple[list[Any], threading.Lock]] = {}
_list_registry_lock = threading.Lock()


def clear_all_registries() -> None:
    """Clear all module-level registries.

    Useful in test fixtures to prevent cross-test state pollution.
    """
    with _dict_registry_lock:
        _dict_registry.clear()
    with _list_registry_lock:
        _list_registry.clear()
    with InMemoryRedlock._registry_lock:
        InMemoryRedlock._locks.clear()


class InMemoryRedisClient:
    """Drop-in replacement for ``redis.Redis`` supporting the subset of
    methods used by MADSci state handlers: ``incr``, ``get``, and ``ping``.
    """

    def __init__(self, **_kwargs: Any) -> None:
        """Initialize the in-memory Redis client."""
        self._data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key by *amount* and return the new value."""
        with self._lock:
            val = int(self._data.get(key, 0)) + amount
            self._data[key] = str(val)
            return val

    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or ``None`` if missing."""
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set *key* to *value*."""
        with self._lock:
            self._data[key] = str(value)

    def ping(self) -> bool:
        """Return ``True`` (always healthy)."""
        return True


class InMemoryRedisDict(MutableMapping):
    """Drop-in replacement for ``pottery.RedisDict``.

    Inherits from ``MutableMapping`` so Pydantic's ``model_validate``
    treats it as a dict-like, matching the behavior of ``pottery.RedisDict``.

    Multiple instances created with the same *key* and *redis* client share
    the same underlying storage, mirroring Redis semantics.
    """

    def __init__(self, *, key: str, redis: Any) -> None:
        """Initialize a shared-storage dict keyed by *key*."""
        self._key = key
        self._redis = redis
        self._client_id = id(redis)

        with _dict_registry_lock:
            registry_key = (self._client_id, self._key)
            if registry_key not in _dict_registry:
                _dict_registry[registry_key] = ({}, threading.Lock())
            self._store, self._lock = _dict_registry[registry_key]

    # --- dict-like interface ---

    def __getitem__(self, key: str) -> Any:
        """Get a value by key."""
        with self._lock:
            return self._store[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value by key."""
        with self._lock:
            self._store[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete a key."""
        with self._lock:
            del self._store[key]

    def __contains__(self, key: object) -> bool:
        """Check if a key exists."""
        with self._lock:
            return key in self._store

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        with self._lock:
            keys = list(self._store.keys())
        return iter(keys)

    def __len__(self) -> int:
        """Return the number of entries."""
        with self._lock:
            return len(self._store)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if missing."""
        with self._lock:
            return self._store.get(key, default)

    def items(self) -> list[tuple[str, Any]]:
        """Return all (key, value) pairs as a list."""
        with self._lock:
            return list(self._store.items())

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Update the dict with key-value pairs."""
        with self._lock:
            self._store.update(*args, **kwargs)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def to_dict(self) -> dict[str, Any]:
        """Return a plain ``dict`` copy of the data."""
        with self._lock:
            return dict(self._store)


class InMemoryRedisList:
    """Drop-in replacement for ``pottery.RedisList``.

    Supports: ``append()``, ``remove()``, ``iter()``, ``len()``.

    Multiple instances created with the same *key* and *redis* client share
    the same underlying storage.
    """

    def __init__(self, *, key: str, redis: Any) -> None:
        """Initialize a shared-storage list keyed by *key*."""
        self._key = key
        self._redis = redis
        self._client_id = id(redis)

        with _list_registry_lock:
            registry_key = (self._client_id, self._key)
            if registry_key not in _list_registry:
                _list_registry[registry_key] = ([], threading.Lock())
            self._store, self._lock = _list_registry[registry_key]

    def append(self, value: Any) -> None:
        """Append a value to the list."""
        with self._lock:
            self._store.append(value)

    def remove(self, value: Any) -> None:
        """Remove the first occurrence of *value*."""
        with self._lock:
            self._store.remove(value)

    def __iter__(self) -> Iterator[Any]:
        """Iterate over list items."""
        with self._lock:
            items = list(self._store)
        return iter(items)

    def __len__(self) -> int:
        """Return the list length."""
        with self._lock:
            return len(self._store)

    def __contains__(self, value: object) -> bool:
        """Check if a value is in the list."""
        with self._lock:
            return value in self._store


class InMemoryRedlock:
    """Drop-in replacement for ``pottery.Redlock``.

    Uses ``threading.RLock`` for single-process locking.  The ``masters``
    and ``auto_release_time`` parameters are accepted for API compatibility
    but are not enforced (no network timeouts in single-process mode).
    """

    # Module-level lock registry so the same key always resolves to the same RLock.
    _locks: ClassVar[dict[str, threading.RLock]] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        *,
        key: str,
        masters: Any = None,  # noqa: ARG002
        auto_release_time: int = 60,  # noqa: ARG002
    ) -> None:
        """Initialize a reentrant lock keyed by *key*."""
        self._key = key
        with InMemoryRedlock._registry_lock:
            if key not in InMemoryRedlock._locks:
                InMemoryRedlock._locks[key] = threading.RLock()
            self._rlock = InMemoryRedlock._locks[key]

    def __enter__(self) -> InMemoryRedlock:
        """Acquire the lock on context entry."""
        self._rlock.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        """Release the lock on context exit."""
        self._rlock.release()

    def acquire(self) -> bool:
        """Acquire the lock and return ``True``."""
        return self._rlock.acquire()

    def release(self) -> None:
        """Release the lock."""
        self._rlock.release()

    def locked(self) -> bool:
        """Return ``True`` if the lock is currently held by another thread."""
        # Try to acquire without blocking; if we can, it wasn't locked.
        if self._rlock.acquire(blocking=False):
            self._rlock.release()
            return False
        return True
