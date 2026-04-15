"""Shared fixtures for database handler tests."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.cache_handler import InMemoryCacheHandler
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.db_handlers.object_storage_handler import (
    InMemoryObjectStorageHandler,
)
from madsci.common.db_handlers.postgres_handler import SQLiteHandler

# ---------------------------------------------------------------------------
# In-memory fixtures (always available, no Docker required)
# ---------------------------------------------------------------------------


@pytest.fixture()
def inmemory_document_handler():
    """Create an InMemoryDocumentStorageHandler for testing."""
    handler = InMemoryDocumentStorageHandler(database_name="test_db")
    yield handler
    handler.close()


@pytest.fixture()
def inmemory_cache_handler():
    """Create an InMemoryCacheHandler for testing."""
    handler = InMemoryCacheHandler()
    yield handler
    handler.close()


@pytest.fixture()
def sqlite_handler():
    """Create a SQLiteHandler with in-memory SQLite for testing."""
    handler = SQLiteHandler()
    yield handler
    handler.close()


@pytest.fixture()
def inmemory_object_storage_handler():
    """Create an InMemoryObjectStorageHandler for testing."""
    handler = InMemoryObjectStorageHandler()
    yield handler
    handler.close()


# ---------------------------------------------------------------------------
# Testcontainer fixtures (require Docker, marked as integration)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_document_handler():
    """Create a PyDocumentStorageHandler backed by a real MongoDB-compatible container."""
    try:
        from testcontainers.mongodb import MongoDbContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[mongodb] not installed")

    from madsci.common.db_handlers.document_storage_handler import (  # noqa: PLC0415
        PyDocumentStorageHandler,
    )
    from testcontainers.core.wait_strategies import PortWaitStrategy  # noqa: PLC0415

    try:
        with MongoDbContainer("mongo:7") as mongo:
            PortWaitStrategy(27017).wait_until_ready(mongo)
            url = mongo.get_connection_url()
            handler = PyDocumentStorageHandler.from_url(url, "test_db")
            if not handler.ping():
                handler.close()
                pytest.skip("MongoDB container started but connection failed")
            yield handler
            handler.close()
    except Exception as e:
        pytest.skip(f"Could not start MongoDB container (Docker unavailable?): {e}")


@pytest.fixture(scope="module")
def real_cache_handler():
    """Create a PyCacheHandler backed by a real Redis/Valkey container."""
    try:
        from testcontainers.redis import RedisContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[redis] not installed")

    from madsci.common.db_handlers.cache_handler import PyCacheHandler  # noqa: PLC0415

    try:
        with RedisContainer("redis:7") as redis_container:
            host = redis_container.get_container_host_ip()
            port = int(redis_container.get_exposed_port(6379))
            handler = PyCacheHandler.from_settings(host=host, port=port)
            if not handler.ping():
                handler.close()
                pytest.skip("Redis container started but connection failed")
            yield handler
            handler.close()
    except Exception as e:
        pytest.skip(f"Could not start Redis container (Docker unavailable?): {e}")


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
    from testcontainers.core.wait_strategies import PortWaitStrategy  # noqa: PLC0415

    try:
        with PostgresContainer("postgres:16") as pg:
            PortWaitStrategy(5432).wait_until_ready(pg)
            url = pg.get_connection_url()
            handler = SQLAlchemyHandler.from_url(url)
            if not handler.ping():
                handler.close()
                pytest.skip("PostgreSQL container started but connection failed")
            yield handler
            handler.close()
    except Exception as e:
        pytest.skip(f"Could not start PostgreSQL container (Docker unavailable?): {e}")


@pytest.fixture(scope="module")
def real_object_storage_handler():
    """Create a RealObjectStorageHandler backed by a real S3-compatible container."""
    try:
        from testcontainers.minio import MinioContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[minio] not installed")

    from madsci.common.db_handlers.object_storage_handler import (  # noqa: PLC0415
        RealObjectStorageHandler,
    )
    from minio import Minio  # noqa: PLC0415

    try:
        with MinioContainer() as minio_container:
            config = minio_container.get_config()
            client = Minio(
                endpoint=config["endpoint"],
                access_key=config["access_key"],
                secret_key=config["secret_key"],
                secure=False,
            )
            handler = RealObjectStorageHandler(client)
            if not handler.ping():
                handler.close()
                pytest.skip("S3 container started but connection failed")
            yield handler
            handler.close()
    except Exception as e:
        pytest.skip(
            f"Could not start S3-compatible container (Docker unavailable?): {e}"
        )
