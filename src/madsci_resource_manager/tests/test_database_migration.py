"""Pytest unit tests for the MADSci database migration tools."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.resource_manager.database_version_checker import DatabaseVersionChecker
from madsci.resource_manager.migration_tool import (
    DatabaseMigrationSettings,
    DatabaseMigrator,
    main,
)
from madsci.resource_manager.resource_tables import (
    ResourceTable,
    SchemaVersionTable,
    create_session,
)
from pytest_mock_resources import PostgresConfig, create_postgres_fixture
from sqlalchemy import Engine
from sqlmodel import Session as SQLModelSession


@pytest.fixture(scope="session")
def pmr_postgres_config() -> PostgresConfig:
    """Configure the Postgres fixture"""
    return PostgresConfig(image="postgres:17")


# Create a Postgres fixture
postgres_engine = create_postgres_fixture(ResourceTable)


@pytest.fixture
def session(postgres_engine: Engine) -> SQLModelSession:
    """Session fixture"""
    return create_session(postgres_engine)


@pytest.fixture
def temp_alembic_dir():
    """Create temporary alembic directory structure for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create alembic directory structure
        alembic_dir = temp_path / "alembic"
        alembic_dir.mkdir()
        versions_dir = alembic_dir / "versions"
        versions_dir.mkdir()

        # Create alembic.ini file
        alembic_ini = temp_path / "alembic.ini"
        alembic_ini.write_text("[alembic]\nscript_location = alembic\n")

        # Change to temp directory for testing
        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            yield temp_path
        finally:
            os.chdir(original_cwd)


def test_version_mismatch_detection(postgres_engine: Engine, session: SQLModelSession):
    """Test that version mismatch can be detected"""
    # Create version table with different version using the test engine
    SchemaVersionTable.metadata.create_all(postgres_engine)
    version_entry = SchemaVersionTable(version="1.0.0", migration_notes="Old version")
    session.add(version_entry)
    session.commit()

    # Create version checker and patch its engine to use the test engine
    version_checker = DatabaseVersionChecker(
        "postgresql://test:test@localhost:5432/test"
    )
    version_checker.engine = postgres_engine

    with patch("importlib.metadata.version", return_value="2.0.0"):
        needs_migration, madsci_version, db_version = (
            version_checker.is_migration_needed()
        )

        assert needs_migration is True
        assert madsci_version == "2.0.0"
        assert db_version == "1.0.0"


@patch("madsci.resource_manager.migration_tool.DatabaseMigrator")
@patch("sys.argv", ["migration_tool.py", "--target_version", "1.0.0"])
def test_with_target_version(mock_migrator_class):
    """Test main function with target version argument"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(
        os.environ, {"RESOURCES_DB_URL": "postgresql://test:test@localhost:5432/test"}
    ):
        main()

    # Verify run_migration was called with target version
    mock_migrator.run_migration.assert_called_once_with("1.0.0")


@patch("madsci.resource_manager.migration_tool.DatabaseMigrator")
@patch("sys.argv", ["migration_tool.py", "--backup_only", "true"])
def test_backup_only(mock_migrator_class):
    """Test main function with backup only option"""
    mock_migrator = Mock()
    mock_migrator.backup_tool.create_backup.return_value = Path("/test/backup.sql")
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(
        os.environ, {"RESOURCES_DB_URL": "postgresql://test:test@localhost:5432/test"}
    ):
        main()

    # Verify only backup was called, not migration (now uses backup_tool)
    mock_migrator.backup_tool.create_backup.assert_called_once()
    mock_migrator.run_migration.assert_not_called()


@patch("madsci.resource_manager.migration_tool.DatabaseMigrator")
@patch("sys.argv", ["migration_tool.py", "--restore_from", "/test/backup.sql"])
def test_restore_from(mock_migrator_class):
    """Test main function with restore from option"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(
        os.environ, {"RESOURCES_DB_URL": "postgresql://test:test@localhost:5432/test"}
    ):
        main()

    # Verify restore was called with correct path (now uses backup_tool)
    mock_migrator.backup_tool.restore_from_backup.assert_called_once_with(
        Path("/test/backup.sql")
    )
    mock_migrator.run_migration.assert_not_called()


@patch("madsci.resource_manager.migration_tool.DatabaseMigrator")
@patch("sys.argv", ["migration_tool.py", "--generate_migration", "Test migration"])
def test_generate_migration(mock_migrator_class):
    """Test main function with generate migration option"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(
        os.environ, {"RESOURCES_DB_URL": "postgresql://test:test@localhost:5432/test"}
    ):
        main()

    # Verify generate_migration was called with message
    mock_migrator.generate_migration.assert_called_once_with("Test migration")
    mock_migrator.run_migration.assert_not_called()


@patch("madsci.resource_manager.migration_tool.PostgreSQLBackupTool")
@patch("sys.argv", ["test"])
def test_backup_creation(mock_backup_tool_class, temp_alembic_dir: Path):
    """Test database backup creation using backup tool composition"""
    mock_backup_tool = Mock()
    mock_backup_path = Path("/mock/backup/madsci_backup_20241124_120000.dump")
    mock_backup_tool.create_backup.return_value = mock_backup_path
    mock_backup_tool_class.return_value = mock_backup_tool

    test_url = "postgresql://test:test@localhost:5432/test"
    settings = DatabaseMigrationSettings(db_url=test_url)

    with patch.object(
        DatabaseMigrator, "_get_package_root", return_value=temp_alembic_dir
    ):
        migrator = DatabaseMigrator(settings)
        backup_path = migrator.backup_tool.create_backup()

        # Verify backup tool was created with correct settings
        mock_backup_tool_class.assert_called_once()

        # Verify backup method was called on the tool
        mock_backup_tool.create_backup.assert_called_once()

        # Verify path returned correctly
        assert backup_path == mock_backup_path


@patch("madsci.resource_manager.migration_tool.command")
@patch("sys.argv", ["test"])
def test_migration_file_generation(mock_command, temp_alembic_dir: Path):
    """Test Alembic migration file generation"""
    test_url = "postgresql://test:test@localhost:5432/test"
    settings = DatabaseMigrationSettings(db_url=test_url)

    with patch.object(
        DatabaseMigrator, "_get_package_root", return_value=temp_alembic_dir
    ):
        migrator = DatabaseMigrator(settings)
        migrator.generate_migration("Test migration")

        # Verify Alembic revision command was called
        mock_command.revision.assert_called_once()
        _, kwargs = mock_command.revision.call_args
        assert kwargs["message"] == "Test migration"
        assert kwargs["autogenerate"] is True


@patch("sys.argv", ["test"])
def test_migration_file_post_processing(temp_alembic_dir: Path):
    """Test post-processing of migration files for type conversions"""
    test_url = "postgresql://test:test@localhost:5432/test"
    settings = DatabaseMigrationSettings(db_url=test_url)

    with patch.object(
        DatabaseMigrator, "_get_package_root", return_value=temp_alembic_dir
    ):
        migrator = DatabaseMigrator(settings)

        # Create test migration file with type conversion
        migration_file = temp_alembic_dir / "test_migration.py"
        migration_content = """
def upgrade():
    op.alter_column('test_table', 'test_column',
                   existing_type=sa.VARCHAR(),
                   type_=sa.Float(),
                   existing_nullable=True)
"""
        migration_file.write_text(migration_content)

        # Post-process the file
        migrator._post_process_migration_file(migration_file)

        # Verify safe type conversion was added
        processed_content = migration_file.read_text()
        assert "op.execute" in processed_content
        assert "ALTER TABLE test_table" in processed_content
        assert "USING CASE" in processed_content
