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
from sqlalchemy import Engine
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
