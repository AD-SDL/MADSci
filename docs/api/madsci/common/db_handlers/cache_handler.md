Module madsci.common.db_handlers.cache_handler
==============================================
Cache handler abstraction (Redis/Valkey compatible).

Provides an ABC for cache access and two implementations:
- PyCacheHandler: wraps a real redis.Redis client + pottery data structures (compatible with both Redis and Valkey)
- InMemoryCacheHandler: wraps InMemoryRedisClient for testing

Classes
-------

`InMemoryCacheHandler(client: Optional[Any] = None)`
:   Cache handler backed by in-memory data structures for testing.
    
    Usage::
    
        handler = InMemoryCacheHandler()
        d = handler.create_dict("my:key")
        d["foo"] = "bar"
    
    Initialize with an optional InMemoryRedisClient.
    
    If no client is provided, a new one is created and all
    registries are cleared for test isolation.
    
    Args:
        client: An existing ``InMemoryRedisClient`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.cache_handler.CacheHandler
    * abc.ABC

    ### Methods

    `close(self) ‑> None`
    :   No-op for in-memory Redis.

    `create_dict(self, key: str) ‑> Any`
    :   Create an InMemoryRedisDict.

    `create_list(self, key: str) ‑> Any`
    :   Create an InMemoryRedisList.

    `create_lock(self, key: str, auto_release_time: int = 60) ‑> Any`
    :   Create an InMemoryRedlock.

    `get(self, key: str) ‑> str | None`
    :   Get a value from the in-memory store.

    `incr(self, key: str, amount: int = 1) ‑> int`
    :   Increment a key in the in-memory store.

    `ping(self) ‑> bool`
    :   Always returns True for in-memory Redis.

    `set(self, key: str, value: Any) ‑> None`
    :   Set a value in the in-memory store.

`PyCacheHandler(client: Any)`
:   Cache handler backed by a real Redis/Valkey server.
    
    Uses ``redis.Redis`` for basic operations and ``pottery`` for
    RedisDict, RedisList, and Redlock data structures.
    
    Usage::
    
        handler = PyCacheHandler.from_settings(host="localhost", port=6379)
        d = handler.create_dict("my:key")
        d["foo"] = "bar"
    
    Initialize with an existing redis.Redis client.
    
    Args:
        client: A ``redis.Redis`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.cache_handler.CacheHandler
    * abc.ABC

    ### Static methods

    `from_settings(host: str = 'localhost', port: int = 6379, password: Optional[str] = None) ‑> madsci.common.db_handlers.cache_handler.PyCacheHandler`
    :   Create a handler by connecting to a Redis server.
        
        Args:
            host: Redis server hostname.
            port: Redis server port.
            password: Optional Redis password.
        
        Returns:
            A new PyCacheHandler instance.

    ### Methods

    `close(self) ‑> None`
    :   Close the Redis connection.

    `create_dict(self, key: str) ‑> Any`
    :   Create a pottery RedisDict.

    `create_list(self, key: str) ‑> Any`
    :   Create a pottery RedisList.

    `create_lock(self, key: str, auto_release_time: int = 60) ‑> Any`
    :   Create a pottery Redlock.

    `get(self, key: str) ‑> str | None`
    :   Get a value from Redis.

    `incr(self, key: str, amount: int = 1) ‑> int`
    :   Increment a key in Redis.

    `ping(self) ‑> bool`
    :   Ping the Redis server.

    `set(self, key: str, value: Any) ‑> None`
    :   Set a value in Redis.

`CacheHandler()`
:   Abstract interface for cache (Redis/Valkey) access.
    
    Managers use this interface instead of directly depending on
    ``redis.Redis`` and ``pottery`` data structures, enabling
    in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.cache_handler.InMemoryCacheHandler
    * madsci.common.db_handlers.cache_handler.PyCacheHandler

    ### Methods

    `close(self) ‑> None`
    :   Release Redis connections and resources.

    `create_dict(self, key: str) ‑> <class 'collections.abc.MutableMapping'>`
    :   Create a dict-like object backed by Redis.
        
        Returns an object supporting ``__getitem__``, ``__setitem__``,
        ``__delitem__``, ``__contains__``, ``__iter__``, ``__len__``,
        ``get``, ``items``, ``update``, ``clear``, ``to_dict``.

    `create_list(self, key: str) ‑> Any`
    :   Create a list-like object backed by Redis.
        
        Returns an object supporting ``append``, ``remove``,
        ``__iter__``, ``__len__``, ``__contains__``.

    `create_lock(self, key: str, auto_release_time: int = 60) ‑> ContextManager`
    :   Create a distributed lock.
        
        Returns an object supporting context manager protocol
        (``__enter__``/``__exit__``) and ``acquire``/``release``.
        
        Args:
            key: Lock identifier.
            auto_release_time: Seconds before auto-release.

    `get(self, key: str) ‑> str | None`
    :   Return the value for *key*, or ``None`` if missing.

    `incr(self, key: str, amount: int = 1) ‑> int`
    :   Increment a key by *amount* and return the new value.

    `ping(self) ‑> bool`
    :   Check connectivity to Redis.
        
        Returns:
            True if Redis is reachable, False otherwise.

    `set(self, key: str, value: Any) ‑> None`
    :   Set *key* to *value*.