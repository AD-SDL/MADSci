Module madsci.common.local_backends.inmemory_redis
==================================================
In-memory drop-in replacements for Redis, pottery.RedisDict, pottery.RedisList, and pottery.Redlock.

These classes mirror the interfaces used by WorkcellStateHandler and LocationStateHandler,
enabling the MADSci stack to run without a Redis server. All classes are thread-safe.

Usage::

    client = InMemoryRedisClient()
    d = InMemoryRedisDict(key="my:key", redis=client)
    d["foo"] = "bar"
    assert d["foo"] == "bar"

Functions
---------

`clear_all_registries() ‑> None`
:   Clear all module-level registries.
    
    Useful in test fixtures to prevent cross-test state pollution.

Classes
-------

`InMemoryRedisClient(**_kwargs: Any)`
:   Drop-in replacement for ``redis.Redis`` supporting the subset of
    methods used by MADSci state handlers: ``incr``, ``get``, and ``ping``.
    
    Initialize the in-memory Redis client.

    ### Methods

    `get(self, key: str) ‑> str | None`
    :   Return the value for *key*, or ``None`` if missing.

    `incr(self, key: str, amount: int = 1) ‑> int`
    :   Increment a key by *amount* and return the new value.

    `ping(self) ‑> bool`
    :   Return ``True`` (always healthy).

    `set(self, key: str, value: Any) ‑> None`
    :   Set *key* to *value*.

`InMemoryRedisDict(*, key: str, redis: Any)`
:   Drop-in replacement for ``pottery.RedisDict``.
    
    Inherits from ``MutableMapping`` so Pydantic's ``model_validate``
    treats it as a dict-like, matching the behavior of ``pottery.RedisDict``.
    
    Multiple instances created with the same *key* and *redis* client share
    the same underlying storage, mirroring Redis semantics.
    
    Initialize a shared-storage dict keyed by *key*.

    ### Ancestors (in MRO)

    * collections.abc.MutableMapping
    * collections.abc.Mapping
    * collections.abc.Collection
    * collections.abc.Sized
    * collections.abc.Iterable
    * collections.abc.Container

    ### Methods

    `clear(self) ‑> None`
    :   Remove all entries.

    `get(self, key: str, default: Any = None) ‑> Any`
    :   Return the value for *key*, or *default* if missing.

    `items(self) ‑> list[tuple[str, typing.Any]]`
    :   Return all (key, value) pairs as a list.

    `to_dict(self) ‑> dict[str, typing.Any]`
    :   Return a plain ``dict`` copy of the data.

    `update(self, *args: Any, **kwargs: Any) ‑> None`
    :   Update the dict with key-value pairs.

`InMemoryRedisList(*, key: str, redis: Any)`
:   Drop-in replacement for ``pottery.RedisList``.
    
    Supports: ``append()``, ``remove()``, ``iter()``, ``len()``.
    
    Multiple instances created with the same *key* and *redis* client share
    the same underlying storage.
    
    Initialize a shared-storage list keyed by *key*.

    ### Methods

    `append(self, value: Any) ‑> None`
    :   Append a value to the list.

    `remove(self, value: Any) ‑> None`
    :   Remove the first occurrence of *value*.

`InMemoryRedlock(*, key: str, masters: Any = None, auto_release_time: int = 60)`
:   Drop-in replacement for ``pottery.Redlock``.
    
    Uses ``threading.RLock`` for single-process locking.  The ``masters``
    and ``auto_release_time`` parameters are accepted for API compatibility
    but are not enforced (no network timeouts in single-process mode).
    
    Initialize a reentrant lock keyed by *key*.

    ### Methods

    `acquire(self) ‑> bool`
    :   Acquire the lock and return ``True``.

    `locked(self) ‑> bool`
    :   Return ``True`` if the lock is currently held by another thread.

    `release(self) ‑> None`
    :   Release the lock.