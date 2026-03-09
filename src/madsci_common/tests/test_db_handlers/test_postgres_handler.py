"""Tests for PostgresHandler implementations."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.postgres_handler import PostgresHandler, SQLiteHandler
from sqlalchemy import Column, Integer, MetaData, String, Table, text

# ---------------------------------------------------------------------------
# Parametrized fixture
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["sqlite"],
)
def postgres_handler(request, sqlite_handler):
    """Provide a PostgresHandler implementation for testing."""
    if request.param == "sqlite":
        return sqlite_handler
    raise ValueError(f"Unknown handler type: {request.param}")


# ---------------------------------------------------------------------------
# Test metadata for table creation
# ---------------------------------------------------------------------------

test_metadata = MetaData()

test_table = Table(
    "test_items",
    test_metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("value", Integer),
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPostgresHandlerInterface:
    """Tests that verify any PostgresHandler implementation behaves correctly."""

    def test_is_postgres_handler(self, postgres_handler):
        """Handler must implement PostgresHandler ABC."""
        assert isinstance(postgres_handler, PostgresHandler)

    def test_ping(self, postgres_handler):
        """Handler should respond to ping."""
        assert postgres_handler.ping() is True

    def test_get_engine(self, postgres_handler):
        """get_engine should return a SQLAlchemy Engine."""
        engine = postgres_handler.get_engine()
        assert engine is not None

    def test_create_all_tables(self, postgres_handler):
        """create_all_tables should create tables from metadata."""
        # Use a fresh metadata to avoid conflicts
        md = MetaData()
        Table(
            "handler_test_table",
            md,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )

        postgres_handler.create_all_tables(md)

        # Verify table exists by inserting and querying
        engine = postgres_handler.get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO handler_test_table (id, name) VALUES (1, 'test')")
            )
            conn.commit()

            result = conn.execute(
                text("SELECT name FROM handler_test_table WHERE id = 1")
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "test"

    def test_create_all_tables_idempotent(self, postgres_handler):
        """create_all_tables should be safe to call multiple times."""
        md = MetaData()
        Table(
            "idempotent_test",
            md,
            Column("id", Integer, primary_key=True),
        )

        postgres_handler.create_all_tables(md)
        postgres_handler.create_all_tables(md)  # Should not raise

    def test_execute_query(self, postgres_handler):
        """Should be able to execute SQL queries via the engine."""
        engine = postgres_handler.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1


class TestSQLiteHandler:
    """Tests specific to the SQLiteHandler."""

    def test_default_inmemory(self):
        """Default should be in-memory SQLite."""
        handler = SQLiteHandler()
        assert handler.ping() is True
        handler.close()

    def test_file_based(self, tmp_path):
        """Should support file-based SQLite."""
        db_path = tmp_path / "test.db"
        handler = SQLiteHandler(f"sqlite:///{db_path}")
        assert handler.ping() is True
        handler.close()


# ---------------------------------------------------------------------------
# Integration tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPostgresHandlerIntegration:
    """Tests that run against a real PostgreSQL container."""

    @pytest.fixture(autouse=True)
    def _setup(self, real_postgres_handler):
        self.handler = real_postgres_handler

    def test_ping(self):
        """Real PostgreSQL should respond to ping."""
        assert self.handler.ping() is True

    def test_create_and_query(self):
        """Should create tables and run queries against real PostgreSQL."""
        md = MetaData()
        Table(
            "pg_integration_test",
            md,
            Column("id", Integer, primary_key=True),
            Column("data", String(100)),
        )

        self.handler.create_all_tables(md)

        engine = self.handler.get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO pg_integration_test (id, data) VALUES (1, 'hello')")
            )
            conn.commit()

            result = conn.execute(
                text("SELECT data FROM pg_integration_test WHERE id = 1")
            )
            assert result.fetchone()[0] == "hello"
