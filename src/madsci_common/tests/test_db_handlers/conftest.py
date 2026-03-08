"""Shared fixtures for database handler tests."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.minio_handler import InMemoryMinioHandler
from madsci.common.db_handlers.mongo_handler import InMemoryMongoHandler
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.db_handlers.redis_handler import InMemoryRedisHandler

# ---------------------------------------------------------------------------
# In-memory fixtures (always available, no Docker required)
# ---------------------------------------------------------------------------


@pytest.fixture()
def inmemory_mongo_handler():
    """Create an InMemoryMongoHandler for testing."""
    handler = InMemoryMongoHandler(database_name="test_db")
    yield handler
    handler.close()


@pytest.fixture()
def inmemory_redis_handler():
    """Create an InMemoryRedisHandler for testing."""
    handler = InMemoryRedisHandler()
    yield handler
    handler.close()


@pytest.fixture()
def sqlite_handler():
    """Create a SQLiteHandler with in-memory SQLite for testing."""
    handler = SQLiteHandler()
    yield handler
    handler.close()


@pytest.fixture()
def inmemory_minio_handler():
    """Create an InMemoryMinioHandler for testing."""
    handler = InMemoryMinioHandler()
    yield handler
    handler.close()


# ---------------------------------------------------------------------------
# Testcontainer fixtures (require Docker, marked as integration)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_mongo_handler():
    """Create a PyMongoHandler backed by a real MongoDB container."""
    try:
        from testcontainers.mongodb import MongoDbContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[mongodb] not installed")

    from madsci.common.db_handlers.mongo_handler import PyMongoHandler  # noqa: PLC0415

    with MongoDbContainer("mongo:7") as mongo:
        url = mongo.get_connection_url()
        handler = PyMongoHandler.from_url(url, "test_db")
        yield handler
        handler.close()


@pytest.fixture(scope="module")
def real_redis_handler():
    """Create a PyRedisHandler backed by a real Redis container."""
    try:
        from testcontainers.redis import RedisContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[redis] not installed")

    from madsci.common.db_handlers.redis_handler import PyRedisHandler  # noqa: PLC0415

    with RedisContainer("redis:7") as redis_container:
        host = redis_container.get_container_host_ip()
        port = int(redis_container.get_exposed_port(6379))
        handler = PyRedisHandler.from_settings(host=host, port=port)
        yield handler
        handler.close()


@pytest.fixture(scope="module")
def real_postgres_handler():
    """Create a SQLAlchemyHandler backed by a real PostgreSQL container."""
    try:
        from testcontainers.postgres import PostgresContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[postgres] not installed")

    from madsci.common.db_handlers.postgres_handler import (  # noqa: PLC0415
        SQLAlchemyHandler,
    )

    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url()
        handler = SQLAlchemyHandler.from_url(url)
        yield handler
        handler.close()


@pytest.fixture(scope="module")
def real_minio_handler():
    """Create a RealMinioHandler backed by a real MinIO container."""
    try:
        from testcontainers.minio import MinioContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[minio] not installed")

    from madsci.common.db_handlers.minio_handler import (  # noqa: PLC0415
        RealMinioHandler,
    )
    from minio import Minio  # noqa: PLC0415

    with MinioContainer() as minio_container:
        config = minio_container.get_config()
        client = Minio(
            endpoint=config["endpoint"],
            access_key=config["access_key"],
            secret_key=config["secret_key"],
            secure=False,
        )
        handler = RealMinioHandler(client)
        yield handler
        handler.close()
