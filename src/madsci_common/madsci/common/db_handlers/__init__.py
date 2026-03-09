"""Database handler abstractions for MADSci.

This package provides ABC interfaces and implementations for database access,
allowing managers to use fast in-memory mocks in tests while using real
database connections in production.

Handler types:
- MongoHandler: MongoDB database access (PyMongoHandler, InMemoryMongoHandler)
- RedisHandler: Redis key-value + data structure access (PyRedisHandler, InMemoryRedisHandler)
- PostgresHandler: PostgreSQL/SQLite via SQLAlchemy (SQLAlchemyHandler, SQLiteHandler)
- MinioHandler: Object storage access (RealMinioHandler, InMemoryMinioHandler)
"""

from madsci.common.db_handlers.minio_handler import (
    InMemoryMinioHandler,
    MinioHandler,
    RealMinioHandler,
)
from madsci.common.db_handlers.mongo_handler import (
    InMemoryMongoHandler,
    MongoHandler,
    PyMongoHandler,
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
    "InMemoryMinioHandler",
    "InMemoryMongoHandler",
    "InMemoryRedisHandler",
    "MinioHandler",
    "MongoHandler",
    "PostgresHandler",
    "PyMongoHandler",
    "PyRedisHandler",
    "RealMinioHandler",
    "RedisHandler",
    "SQLAlchemyHandler",
    "SQLiteHandler",
]
