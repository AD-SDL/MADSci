"""Cache handler abstraction (Redis/Valkey compatible).

Provides an ABC for cache access and two implementations:
- PyCacheHandler: wraps a real redis.Redis client + pottery data structures (compatible with both Redis and Valkey)
- InMemoryCacheHandler: wraps InMemoryRedisClient for testing
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from collections.abc import MutableMapping
from typing import Any, ContextManager, Optional


class CacheHandler(ABC):
    """Abstract interface for cache access (Redis/Valkey compatible).

    Managers use this interface instead of directly depending on
    ``redis.Redis`` and ``pottery`` data structures, enabling
    in-memory substitution for tests.
    """

    @abstractmethod
    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key by *amount* and return the new value."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or ``None`` if missing."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set *key* to *value*."""

    @abstractmethod
    def ping(self) -> bool:
        """Check connectivity to the cache server.

        Returns:
            True if the cache server is reachable, False otherwise.
        """

    @abstractmethod
    def close(self) -> None:
        """Release cache connections and resources."""

    @abstractmethod
    def create_dict(self, key: str) -> MutableMapping:
        """Create a dict-like object backed by the cache.

        Returns an object supporting ``__getitem__``, ``__setitem__``,
        ``__delitem__``, ``__contains__``, ``__iter__``, ``__len__``,
        ``get``, ``items``, ``update``, ``clear``, ``to_dict``.
        """

    @abstractmethod
    def create_list(self, key: str) -> Any:
        """Create a list-like object backed by the cache.

        Returns an object supporting ``append``, ``remove``,
        ``__iter__``, ``__len__``, ``__contains__``.
        """

    @abstractmethod
    def create_lock(self, key: str, auto_release_time: int = 60) -> ContextManager:
        """Create a distributed lock.

        Returns an object supporting context manager protocol
        (``__enter__``/``__exit__``) and ``acquire``/``release``.

        Args:
            key: Lock identifier.
            auto_release_time: Seconds before auto-release.
        """


class PyCacheHandler(CacheHandler):
    """Cache handler backed by a real Redis/Valkey server.

    Uses ``redis.Redis`` for basic operations and ``pottery`` for
    RedisDict, RedisList, and Redlock data structures.

    Usage::

        handler = PyCacheHandler.from_settings(host="localhost", port=6379)
        d = handler.create_dict("my:key")
        d["foo"] = "bar"
    """

    def __init__(self, client: Any) -> None:
        """Initialize with an existing redis.Redis client.

        Args:
            client: A ``redis.Redis`` instance.
        """
        self._client = client

    @classmethod
    def from_settings(
        cls,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
    ) -> PyCacheHandler:
        """Create a handler by connecting to a cache server.

        Args:
            host: Cache server hostname.
            port: Cache server port.
            password: Optional cache server password.

        Returns:
            A new PyCacheHandler instance.
        """
        import redis  # noqa: PLC0415

        client = redis.Redis(
            host=host,
            port=port,
            db=0,
            decode_responses=True,
            password=password or None,
        )
        return cls(client)

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key in the cache."""
        return self._client.incr(key, amount)

    def get(self, key: str) -> Optional[str]:
        """Get a value from the cache."""
        return self._client.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache."""
        self._client.set(key, value)

    def ping(self) -> bool:
        """Ping the cache server."""
        try:
            return self._client.ping()
        except Exception:
            return False

    def close(self) -> None:
        """Close the cache connection."""
        with contextlib.suppress(Exception):
            self._client.close()

    def create_dict(self, key: str) -> Any:
        """Create a pottery RedisDict."""
        from pottery import RedisDict  # noqa: PLC0415

        return RedisDict(key=key, redis=self._client)

    def create_list(self, key: str) -> Any:
        """Create a pottery RedisList."""
        from pottery import RedisList  # noqa: PLC0415

        return RedisList(key=key, redis=self._client)

    def create_lock(self, key: str, auto_release_time: int = 60) -> Any:
        """Create a pottery Redlock."""
        from pottery import Redlock  # noqa: PLC0415

        return Redlock(
            key=key,
            masters={self._client},
            auto_release_time=auto_release_time,
        )


class InMemoryCacheHandler(CacheHandler):
    """Cache handler backed by in-memory data structures for testing.

    Usage::

        handler = InMemoryCacheHandler()
        d = handler.create_dict("my:key")
        d["foo"] = "bar"
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        """Initialize with an optional InMemoryRedisClient.

        If no client is provided, a new one is created and all
        registries are cleared for test isolation.

        Args:
            client: An existing ``InMemoryRedisClient`` instance.
        """
        from madsci.common.local_backends.inmemory_redis import (  # noqa: PLC0415
            InMemoryRedisClient,
            clear_all_registries,
        )

        if client is not None:
            self._client = client
        else:
            clear_all_registries()
            self._client = InMemoryRedisClient()

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key in the in-memory store."""
        return self._client.incr(key, amount)

    def get(self, key: str) -> Optional[str]:
        """Get a value from the in-memory store."""
        return self._client.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the in-memory store."""
        self._client.set(key, value)

    def ping(self) -> bool:
        """Always returns True for in-memory cache."""
        return True

    def close(self) -> None:
        """No-op for in-memory cache."""

    def create_dict(self, key: str) -> Any:
        """Create an InMemoryRedisDict."""
        from madsci.common.local_backends.inmemory_redis import (  # noqa: PLC0415
            InMemoryRedisDict,
        )

        return InMemoryRedisDict(key=key, redis=self._client)

    def create_list(self, key: str) -> Any:
        """Create an InMemoryRedisList."""
        from madsci.common.local_backends.inmemory_redis import (  # noqa: PLC0415
            InMemoryRedisList,
        )

        return InMemoryRedisList(key=key, redis=self._client)

    def create_lock(self, key: str, auto_release_time: int = 60) -> Any:
        """Create an InMemoryRedlock."""
        from madsci.common.local_backends.inmemory_redis import (  # noqa: PLC0415
            InMemoryRedlock,
        )

        return InMemoryRedlock(
            key=key,
            masters={self._client},
            auto_release_time=auto_release_time,
        )
