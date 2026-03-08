Module madsci.common.db_handlers
================================
Database handler abstractions for MADSci.

This package provides ABC interfaces and implementations for database access,
allowing managers to use fast in-memory mocks in tests while using real
database connections in production.

Handler types:
- MongoHandler: MongoDB database access (PyMongoHandler, InMemoryMongoHandler)
- RedisHandler: Redis key-value + data structure access (PyRedisHandler, InMemoryRedisHandler)
- PostgresHandler: PostgreSQL/SQLite via SQLAlchemy (SQLAlchemyHandler, SQLiteHandler)
- MinioHandler: Object storage access (RealMinioHandler, InMemoryMinioHandler)

Sub-modules
-----------
* madsci.common.db_handlers.minio_handler
* madsci.common.db_handlers.mongo_handler
* madsci.common.db_handlers.postgres_handler
* madsci.common.db_handlers.redis_handler

Classes
-------

`InMemoryMinioHandler()`
:   Object storage handler backed by in-memory storage for testing.
    
    Stores files as bytes in a dictionary keyed by ``(bucket, object_name)``.
    
    Usage::
    
        handler = InMemoryMinioHandler()
        handler.make_bucket("test-bucket")
        handler.upload_file("test-bucket", "data.csv", "/path/to/data.csv")
        data = handler.get_object_data("test-bucket", "data.csv")
    
    Initialize with empty in-memory storage.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.minio_handler.MinioHandler
    * abc.ABC

    ### Methods

    `bucket_exists(self, bucket: str) ‑> bool`
    :   Check if a bucket exists in in-memory storage.

    `close(self) ‑> None`
    :   No-op for in-memory storage.

    `download_file(self, bucket: str, object_name: str, output_path: Union[str, Path]) ‑> None`
    :   Download an object from in-memory storage to a local file.

    `get_object_data(self, bucket: str, object_name: str) ‑> bytes`
    :   Get object contents from in-memory storage.

    `make_bucket(self, bucket: str) ‑> None`
    :   Create a bucket in in-memory storage.

    `ping(self) ‑> bool`
    :   Always returns True for in-memory storage.

    `upload_file(self, bucket: str, object_name: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[dict[str, str]] = None) ‑> dict[str, typing.Any]`
    :   Upload a file to in-memory storage.

`InMemoryMongoHandler(database: Optional[Any] = None, database_name: str = 'test')`
:   MongoDB handler backed by in-memory collections for testing.
    
    Usage::
    
        handler = InMemoryMongoHandler()
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    
    Initialize with an optional InMemoryDatabase.
    
    Args:
        database: An existing ``InMemoryDatabase`` instance.
            If not provided, a new ``InMemoryMongoClient`` is created.
        database_name: Name for the database (used when creating a new client).

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.mongo_handler.MongoHandler
    * abc.ABC

    ### Methods

    `close(self) ‑> None`
    :   No-op for in-memory databases.

    `command(self, cmd: str, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command (only ``ping`` is supported).

    `get_collection(self, name: str) ‑> Any`
    :   Return an InMemoryCollection.

    `list_collection_names(self) ‑> list[str]`
    :   Return collection names from the in-memory database.

    `ping(self) ‑> bool`
    :   Always returns True for in-memory databases.

`InMemoryRedisHandler(client: Optional[Any] = None)`
:   Redis handler backed by in-memory data structures for testing.
    
    Usage::
    
        handler = InMemoryRedisHandler()
        d = handler.create_dict("my:key")
        d["foo"] = "bar"
    
    Initialize with an optional InMemoryRedisClient.
    
    If no client is provided, a new one is created and all
    registries are cleared for test isolation.
    
    Args:
        client: An existing ``InMemoryRedisClient`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.redis_handler.RedisHandler
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

`MinioHandler()`
:   Abstract interface for object storage access.
    
    Managers use this interface instead of directly depending on
    ``minio.Minio``, enabling in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.minio_handler.InMemoryMinioHandler
    * madsci.common.db_handlers.minio_handler.RealMinioHandler

    ### Methods

    `bucket_exists(self, bucket: str) ‑> bool`
    :   Check if a bucket exists.
        
        Args:
            bucket: Bucket name.
        
        Returns:
            True if the bucket exists.

    `close(self) ‑> None`
    :   Release any connections or resources.

    `download_file(self, bucket: str, object_name: str, output_path: Union[str, Path]) ‑> None`
    :   Download an object to a local file.
        
        Args:
            bucket: Bucket name.
            object_name: Name/key of the object.
            output_path: Local path to write the file to.

    `ensure_bucket(self, bucket: str) ‑> None`
    :   Ensure a bucket exists, creating it if necessary.

    `get_object_data(self, bucket: str, object_name: str) ‑> bytes`
    :   Get object contents as bytes.
        
        Args:
            bucket: Bucket name.
            object_name: Name/key of the object.
        
        Returns:
            The object contents as bytes.

    `list_buckets(self) ‑> list[str]`
    :   Return names of all buckets.

    `make_bucket(self, bucket: str) ‑> None`
    :   Create a bucket.
        
        Args:
            bucket: Bucket name to create.

    `ping(self) ‑> bool`
    :   Check connectivity to the object storage service.
        
        Returns:
            True if the service is reachable, False otherwise.

    `upload_file(self, bucket: str, object_name: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[dict[str, str]] = None) ‑> dict[str, typing.Any]`
    :   Upload a file to object storage.
        
        Args:
            bucket: Bucket name.
            object_name: Name/key for the object.
            file_path: Local file path to upload.
            content_type: MIME type (auto-detected if not provided).
            metadata: Additional metadata to attach.
        
        Returns:
            Dictionary with storage information including bucket_name,
            object_name, etag, size_bytes, and content_type.

`MongoHandler()`
:   Abstract interface for MongoDB database access.
    
    Managers use this interface instead of directly depending on
    ``pymongo.Database``, enabling in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.mongo_handler.InMemoryMongoHandler
    * madsci.common.db_handlers.mongo_handler.PyMongoHandler

    ### Methods

    `close(self) ‑> None`
    :   Release database connections and resources.

    `command(self, cmd: str, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command (e.g. ``ping``).

    `get_collection(self, name: str) ‑> Any`
    :   Return a collection-like object for the given name.
        
        The returned object supports the pymongo Collection interface:
        insert_one, find_one, find, update_one, update_many, delete_one,
        delete_many, count_documents, create_index, drop_index, index_information.

    `list_collection_names(self) ‑> list[str]`
    :   Return the names of all collections in the database.

    `ping(self) ‑> bool`
    :   Check connectivity to the database.
        
        Returns:
            True if the database is reachable, False otherwise.

`PostgresHandler()`
:   Abstract interface for relational database access via SQLAlchemy.
    
    Managers use this interface instead of directly depending on
    ``sqlalchemy.Engine``, enabling SQLite substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.postgres_handler.SQLAlchemyHandler
    * madsci.common.db_handlers.postgres_handler.SQLiteHandler

    ### Methods

    `close(self) ‑> None`
    :   Release database connections and resources.

    `create_all_tables(self, metadata: Any) ‑> None`
    :   Create all tables defined in the given metadata.
        
        Args:
            metadata: A ``sqlalchemy.MetaData`` or ``sqlmodel.SQLModel.metadata`` object.

    `get_engine(self) ‑> Any`
    :   Return the SQLAlchemy Engine instance.

    `ping(self) ‑> bool`
    :   Check connectivity to the database.
        
        Returns:
            True if the database is reachable, False otherwise.

`PyMongoHandler(database: Any)`
:   MongoDB handler backed by a real pymongo connection.
    
    Usage::
    
        handler = PyMongoHandler.from_url("mongodb://localhost:27017", "my_db")
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    
    Initialize with an existing pymongo Database object.
    
    Args:
        database: A ``pymongo.database.Database`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.mongo_handler.MongoHandler
    * abc.ABC

    ### Static methods

    `from_url(url: str, database_name: str) ‑> madsci.common.db_handlers.mongo_handler.PyMongoHandler`
    :   Create a handler by connecting to a MongoDB server.
        
        Args:
            url: MongoDB connection URL.
            database_name: Name of the database to use.
        
        Returns:
            A new PyMongoHandler instance.

    ### Methods

    `close(self) ‑> None`
    :   Close the underlying MongoClient.

    `command(self, cmd: str, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command.

    `get_collection(self, name: str) ‑> Any`
    :   Return a pymongo Collection.

    `list_collection_names(self) ‑> list[str]`
    :   Return collection names from the database.

    `ping(self) ‑> bool`
    :   Ping the MongoDB server.

`PyRedisHandler(client: Any)`
:   Redis handler backed by a real Redis server.
    
    Uses ``redis.Redis`` for basic operations and ``pottery`` for
    RedisDict, RedisList, and Redlock data structures.
    
    Usage::
    
        handler = PyRedisHandler.from_settings(host="localhost", port=6379)
        d = handler.create_dict("my:key")
        d["foo"] = "bar"
    
    Initialize with an existing redis.Redis client.
    
    Args:
        client: A ``redis.Redis`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.redis_handler.RedisHandler
    * abc.ABC

    ### Static methods

    `from_settings(host: str = 'localhost', port: int = 6379, password: Optional[str] = None) ‑> madsci.common.db_handlers.redis_handler.PyRedisHandler`
    :   Create a handler by connecting to a Redis server.
        
        Args:
            host: Redis server hostname.
            port: Redis server port.
            password: Optional Redis password.
        
        Returns:
            A new PyRedisHandler instance.

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

`RealMinioHandler(client: Any)`
:   Object storage handler backed by a real MinIO/S3 server.
    
    Usage::
    
        handler = RealMinioHandler.from_settings(object_storage_settings)
        handler.upload_file("my-bucket", "data.csv", "/path/to/data.csv")
    
    Initialize with an existing Minio client.
    
    Args:
        client: A ``minio.Minio`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.minio_handler.MinioHandler
    * abc.ABC

    ### Static methods

    `from_settings(settings: Any) ‑> madsci.common.db_handlers.minio_handler.RealMinioHandler`
    :   Create a handler from ObjectStorageSettings.
        
        Args:
            settings: An ``ObjectStorageSettings`` instance with endpoint,
                access_key, secret_key, secure, and region fields.
        
        Returns:
            A new RealMinioHandler instance.

    ### Methods

    `bucket_exists(self, bucket: str) ‑> bool`
    :   Check if a bucket exists in MinIO.

    `close(self) ‑> None`
    :   No-op for MinIO client (uses HTTP, no persistent connection).

    `download_file(self, bucket: str, object_name: str, output_path: Union[str, Path]) ‑> None`
    :   Download an object from MinIO.

    `get_object_data(self, bucket: str, object_name: str) ‑> bytes`
    :   Get object contents from MinIO.

    `make_bucket(self, bucket: str) ‑> None`
    :   Create a bucket in MinIO.

    `ping(self) ‑> bool`
    :   Check connectivity by listing buckets.

    `upload_file(self, bucket: str, object_name: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[dict[str, str]] = None) ‑> dict[str, typing.Any]`
    :   Upload a file to MinIO.

`RedisHandler()`
:   Abstract interface for Redis access.
    
    Managers use this interface instead of directly depending on
    ``redis.Redis`` and ``pottery`` data structures, enabling
    in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.redis_handler.InMemoryRedisHandler
    * madsci.common.db_handlers.redis_handler.PyRedisHandler

    ### Methods

    `close(self) ‑> None`
    :   Release Redis connections and resources.

    `create_dict(self, key: str) ‑> Any`
    :   Create a dict-like object backed by Redis.
        
        Returns an object supporting ``__getitem__``, ``__setitem__``,
        ``__delitem__``, ``__contains__``, ``__iter__``, ``__len__``,
        ``get``, ``items``, ``update``, ``clear``, ``to_dict``.

    `create_list(self, key: str) ‑> Any`
    :   Create a list-like object backed by Redis.
        
        Returns an object supporting ``append``, ``remove``,
        ``__iter__``, ``__len__``, ``__contains__``.

    `create_lock(self, key: str, auto_release_time: int = 60) ‑> Any`
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

`SQLAlchemyHandler(engine: Any)`
:   PostgreSQL handler backed by a real SQLAlchemy engine.
    
    Usage::
    
        handler = SQLAlchemyHandler.from_url("postgresql://localhost/mydb")
        engine = handler.get_engine()
    
    Initialize with an existing SQLAlchemy Engine.
    
    Args:
        engine: A ``sqlalchemy.Engine`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.postgres_handler.PostgresHandler
    * abc.ABC

    ### Static methods

    `from_url(url: str, pool_size: int = 20, pool_pre_ping: bool = True) ‑> madsci.common.db_handlers.postgres_handler.SQLAlchemyHandler`
    :   Create a handler by connecting to a PostgreSQL database.
        
        Args:
            url: SQLAlchemy database URL.
            pool_size: Connection pool size.
            pool_pre_ping: Whether to verify connections before use.
        
        Returns:
            A new SQLAlchemyHandler instance.

    ### Methods

    `close(self) ‑> None`
    :   Dispose of the engine's connection pool.

    `create_all_tables(self, metadata: Any) ‑> None`
    :   Create all tables using the engine.

    `get_engine(self) ‑> Any`
    :   Return the SQLAlchemy Engine.

    `ping(self) ‑> bool`
    :   Execute ``SELECT 1`` to verify connectivity.

`SQLiteHandler(url: Optional[str] = None)`
:   SQLite handler for testing, using SQLAlchemy with a SQLite backend.
    
    Defaults to an in-memory database (``sqlite:///:memory:``) but can
    also use a file-based SQLite database.  In-memory databases use
    ``StaticPool`` so the same connection is shared across threads (required
    for ``TestClient`` and similar multi-threaded test harnesses).
    
    Usage::
    
        handler = SQLiteHandler()  # in-memory
        handler = SQLiteHandler("sqlite:///path/to/db.sqlite")  # file-based
    
    Initialize with an optional SQLite URL.
    
    Args:
        url: SQLite connection URL. Defaults to ``sqlite:///:memory:``.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.postgres_handler.PostgresHandler
    * abc.ABC

    ### Methods

    `close(self) ‑> None`
    :   Dispose of the engine's connection pool.

    `create_all_tables(self, metadata: Any) ‑> None`
    :   Create compatible tables using the SQLite engine.
        
        When a table uses PostgreSQL-specific features (e.g. ``AUTOINCREMENT``
        on a composite primary key), the handler builds SQLite-compatible DDL
        where the autoincrement column becomes the sole ``INTEGER PRIMARY KEY
        AUTOINCREMENT`` and other PK columns become regular ``NOT NULL`` columns.

    `get_engine(self) ‑> Any`
    :   Return the SQLAlchemy Engine.

    `ping(self) ‑> bool`
    :   Execute ``SELECT 1`` to verify connectivity.