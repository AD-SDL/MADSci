# Database Handler Reference

Each manager talks to its database through a handler ABC, with a real implementation for production and an in-memory implementation for tests. SKILL.md links here when you need handler details; everyday manager work doesn't need this file.

## Contents

- [DocumentStorageHandler (FerretDB / MongoDB)](#documentstoragehandler-ferretdb--mongodb)
- [CacheHandler (Valkey / Redis)](#cachehandler-valkey--redis)
- [PostgresHandler (PostgreSQL)](#postgreshandler-postgresql)
- [ObjectStorageHandler (S3-compatible)](#objectstoragehandler-s3-compatible)

## DocumentStorageHandler (FerretDB/MongoDB)

```python
from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,       # ABC
    PyDocumentStorageHandler,     # Real (pymongo)
    InMemoryDocumentStorageHandler,  # Testing
)

# Production:
handler = PyDocumentStorageHandler(url="mongodb://localhost:27017", database_name="madsci_events")
collection = handler.get_collection("events")
collection.insert_one({"event": "data"})

# Testing:
handler = InMemoryDocumentStorageHandler()
```

**Used by:** Event, Experiment, Data, Workcell, Location managers

## CacheHandler (Valkey/Redis)

```python
from madsci.common.db_handlers.cache_handler import (
    CacheHandler,          # ABC
    PyCacheHandler,        # Real (redis + pottery)
    InMemoryCacheHandler,  # Testing
)

# Production:
handler = PyCacheHandler(url="redis://localhost:6379")
state_dict = handler.create_dict("workcell_state")  # pottery RedisDict-like
lock = handler.create_lock("operation_lock", auto_release_time=30)

# Testing:
handler = InMemoryCacheHandler()
```

**Used by:** Workcell, Location managers

## PostgresHandler (PostgreSQL)

```python
from madsci.common.db_handlers.postgres_handler import (
    PostgresHandler,     # ABC
    SQLAlchemyHandler,   # Real (SQLAlchemy + PostgreSQL)
    SQLiteHandler,       # Testing (in-memory SQLite)
)

# Production:
handler = SQLAlchemyHandler(url="postgresql://localhost/resources")
engine = handler.get_engine()

# Testing:
handler = SQLiteHandler()  # StaticPool, check_same_thread=False
```

**Used by:** Resource manager

## ObjectStorageHandler (S3-compatible)

```python
from madsci.common.db_handlers.object_storage_handler import (
    ObjectStorageHandler,          # ABC
    RealObjectStorageHandler,      # Real (MinIO/SeaweedFS/S3)
    InMemoryObjectStorageHandler,  # Testing
)

# Production:
handler = RealObjectStorageHandler(settings=ObjectStorageSettings(...))

# Testing:
handler = InMemoryObjectStorageHandler()
```

**Used by:** Data manager (optional, for file storage)
