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
    from testcontainers.core.wait_strategies import PortWaitStrategy  # noqa: PLC0415

    try:
        with MongoDbContainer("mongo:7") as mongo:
            # MongoDbContainer._connect() only checks container logs, not host
            # port reachability. Wait for host-side port forwarding (can lag on
            # macOS/Rancher Desktop VM networking).
            PortWaitStrategy(27017).wait_until_ready(mongo)
            url = mongo.get_connection_url()
            handler = PyMongoHandler.from_url(url, "test_db")
            if not handler.ping():
                handler.close()
                pytest.skip("MongoDB container started but connection failed")
            yield handler
            handler.close()
    except Exception as e:
        pytest.skip(f"Could not start MongoDB container (Docker unavailable?): {e}")


@pytest.fixture(scope="module")
def real_redis_handler():
    """Create a PyRedisHandler backed by a real Redis container."""
    try:
        from testcontainers.redis import RedisContainer  # noqa: PLC0415
    except ImportError:
        pytest.skip("testcontainers[redis] not installed")

    from madsci.common.db_handlers.redis_handler import PyRedisHandler  # noqa: PLC0415

    try:
        with RedisContainer("redis:7") as redis_container:
            host = redis_container.get_container_host_ip()
            port = int(redis_container.get_exposed_port(6379))
            handler = PyRedisHandler.from_settings(host=host, port=port)
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
            # PostgresContainer._connect() uses ExecWaitStrategy (psql inside
            # container) which doesn't verify host-side port forwarding. Wait
            # for the mapped port to be reachable from the host (can lag ~1-2s
            # on macOS/Rancher Desktop VM networking).
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

    try:
        with MinioContainer() as minio_container:
            config = minio_container.get_config()
            client = Minio(
                endpoint=config["endpoint"],
                access_key=config["access_key"],
                secret_key=config["secret_key"],
                secure=False,
            )
            handler = RealMinioHandler(client)
            if not handler.ping():
                handler.close()
                pytest.skip("MinIO container started but connection failed")
            yield handler
            handler.close()
    except Exception as e:
        pytest.skip(f"Could not start MinIO container (Docker unavailable?): {e}")
