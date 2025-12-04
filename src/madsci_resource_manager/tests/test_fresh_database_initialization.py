"""Test fresh database initialization functionality."""

import pytest
from madsci.common.types.resource_types.definitions import (
    ResourceManagerDefinition,
    ResourceManagerSettings,
)
from madsci.resource_manager.database_version_checker import DatabaseVersionChecker
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.resource_server import ResourceManager
from madsci.resource_manager.resource_tables import create_session
from pytest_mock_resources import PostgresConfig, create_postgres_fixture
from sqlalchemy import Engine, inspect, text
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def pmr_postgres_config() -> PostgresConfig:
    """Configure the Postgres fixture"""
    return PostgresConfig(image="postgres:17")


# Create a fresh Postgres fixture for fresh database tests (no tables created by default)
fresh_postgres_engine = create_postgres_fixture()


def test_resource_manager_with_external_interface_skips_validation(
    fresh_postgres_engine: Engine,
) -> None:
    """Test that providing external resource interface skips validation (existing test pattern)."""

    # Create external interface (this is the existing test pattern that works)
    def sessionmaker():
        return create_session(fresh_postgres_engine)

    external_interface = ResourceInterface(
        engine=fresh_postgres_engine, sessionmaker=sessionmaker
    )

    # Create resource manager with external interface
    settings = ResourceManagerSettings(db_url="dummy://url")  # Should be ignored
    definition = ResourceManagerDefinition(
        name="Test External Interface Resource Manager"
    )

    # This should work even with fresh database because external interface skips validation
    manager = ResourceManager(
        settings=settings, definition=definition, resource_interface=external_interface
    )

    # Verify it can serve requests
    app = manager.create_server()
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200


def test_version_checker_fresh_database(fresh_postgres_engine: Engine) -> None:
    """Test version checker behavior with fresh database."""
    version_checker = DatabaseVersionChecker(str(fresh_postgres_engine.url))

    # Fresh database should have no version
    db_version = version_checker.get_database_version()
    assert db_version is None, "Fresh database should have no version"

    # Should indicate migration is needed
    needs_migration, madsci_version, db_version = version_checker.is_migration_needed()
    assert needs_migration, "Fresh database should need migration"
    assert madsci_version is not None, "MADSci version should be available"
    assert db_version is None, "Database version should be None for fresh database"


def test_auto_initialization_methods_exist():
    """Test that the auto-initialization methods exist and are callable."""
    # Just verify the methods exist without actually running them on a database
    assert hasattr(ResourceManager, "_is_fresh_database")
    assert hasattr(ResourceManager, "_auto_initialize_fresh_database")
    assert callable(ResourceManager._is_fresh_database)
    assert callable(ResourceManager._auto_initialize_fresh_database)


def test_fresh_database_detection(fresh_postgres_engine: Engine) -> None:
    """Test that is_fresh_database correctly detects fresh databases."""
    version_checker = DatabaseVersionChecker(str(fresh_postgres_engine.url))
    version_checker.engine = fresh_postgres_engine

    # Fresh database should be detected as fresh
    assert version_checker.is_fresh_database() is True, (
        "Fresh database should be detected as fresh"
    )


def test_fresh_database_auto_initialization(fresh_postgres_engine: Engine) -> None:
    """Test that validate_or_fail auto-initializes fresh databases."""
    # Create a version checker that uses the existing engine directly
    version_checker = DatabaseVersionChecker(str(fresh_postgres_engine.url))
    # Replace the engine with the fresh one to avoid connection issues
    version_checker.engine = fresh_postgres_engine

    # This should auto-initialize without raising an error
    version_checker.validate_or_fail()

    # After auto-initialization, version should be tracked
    assert version_checker.is_version_tracked() is True, (
        "Version tracking should be enabled after auto-initialization"
    )

    # Should have a database version now
    db_version = version_checker.get_database_version()
    assert db_version is not None, (
        "Database should have a version after auto-initialization"
    )

    # Should match current MADSci version (accepting that it might be 0.0.0 in test)
    madsci_version = version_checker.get_current_madsci_version()
    # Using major.minor comparison like the PostgreSQL implementation does
    assert version_checker.versions_match(db_version, madsci_version), (
        "Database version should match MADSci version after auto-initialization"
    )


def test_fresh_database_auto_init_does_not_require_migration_after(
    fresh_postgres_engine: Engine,
) -> None:
    """Test that after auto-initialization, no further migration is needed."""
    version_checker = DatabaseVersionChecker(str(fresh_postgres_engine.url))
    version_checker.engine = fresh_postgres_engine

    # Auto-initialize
    version_checker.validate_or_fail()

    # Should not need migration after auto-initialization
    needs_migration, madsci_version, db_version = version_checker.is_migration_needed()
    assert needs_migration is False, (
        "Should not need migration after auto-initialization"
    )
    assert madsci_version is not None, "MADSci version should be available"
    assert db_version is not None, (
        "Database version should be available after auto-initialization"
    )


def test_fresh_database_auto_init_creates_version_table(
    fresh_postgres_engine: Engine,
) -> None:
    """Test that auto-initialization creates the schema version table."""
    version_checker = DatabaseVersionChecker(str(fresh_postgres_engine.url))
    version_checker.engine = fresh_postgres_engine

    # Initially no schema version table
    inspector = inspect(fresh_postgres_engine)
    initial_tables = inspector.get_table_names()
    assert "madsci_schema_version" not in initial_tables, (
        "Schema version table should not exist initially"
    )

    # Auto-initialize
    version_checker.validate_or_fail()

    # Schema version table should now exist
    inspector = inspect(fresh_postgres_engine)
    final_tables = inspector.get_table_names()
    assert "madsci_schema_version" in final_tables, (
        "Schema version table should exist after auto-initialization"
    )


def test_existing_database_without_version_tracking_still_requires_migration(
    fresh_postgres_engine: Engine,
) -> None:
    """Test that existing databases without version tracking still require migration."""
    version_checker = DatabaseVersionChecker(str(fresh_postgres_engine.url))
    version_checker.engine = fresh_postgres_engine

    # Create a resource-related table to make it not fresh
    with fresh_postgres_engine.connect() as conn:
        conn.execute(text("CREATE TABLE resource (id VARCHAR(26) PRIMARY KEY)"))
        conn.commit()

    # Should no longer be detected as fresh
    assert version_checker.is_fresh_database() is False, (
        "Database with existing resource tables should not be detected as fresh"
    )

    # Should require migration for existing database without version tracking
    with pytest.raises(RuntimeError, match="Database schema version mismatch"):
        version_checker.validate_or_fail()
