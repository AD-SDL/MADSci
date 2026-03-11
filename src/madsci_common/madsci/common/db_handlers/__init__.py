"""Database handler abstractions for MADSci.

This package provides ABC interfaces and implementations for database access,
allowing managers to use fast in-memory mocks in tests while using real
database connections in production.

Handler types:
- DocumentStorageHandler: MongoDB-compatible document database access (PyDocumentStorageHandler, InMemoryDocumentStorageHandler)
- RedisHandler: Redis/Valkey key-value + data structure access (PyRedisHandler, InMemoryRedisHandler)
- PostgresHandler: PostgreSQL/SQLite via SQLAlchemy (SQLAlchemyHandler, SQLiteHandler)
- ObjectStorageHandler: S3-compatible object storage access (RealObjectStorageHandler, InMemoryObjectStorageHandler)
"""

from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,
    InMemoryDocumentStorageHandler,
    PyDocumentStorageHandler,
)
from madsci.common.db_handlers.object_storage_handler import (
    InMemoryObjectStorageHandler,
    ObjectStorageHandler,
    RealObjectStorageHandler,
)
from madsci.common.db_handlers.postgres_handler import (
    PostgresHandler,
    SQLAlchemyHandler,
    SQLiteHandler,
)
from madsci.common.db_handlers.redis_handler import (
    InMemoryRedisHandler,
    PyRedisHandler,
    RedisHandler,
)

__all__ = [
    "DocumentStorageHandler",
    "InMemoryDocumentStorageHandler",
    "InMemoryObjectStorageHandler",
    "InMemoryRedisHandler",
    "ObjectStorageHandler",
    "PostgresHandler",
    "PyDocumentStorageHandler",
    "PyRedisHandler",
    "RealObjectStorageHandler",
    "RedisHandler",
    "SQLAlchemyHandler",
    "SQLiteHandler",
]
