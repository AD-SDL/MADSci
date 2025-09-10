"""Pytest unit tests for the MADSci database migration tools."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.resource_manager.database_version_checker import DatabaseVersionChecker
from madsci.resource_manager.migration_tool import DatabaseMigrator, main
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
@patch("sys.argv", ["migration_tool.py", "--target-version", "1.0.0"])
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
@patch("sys.argv", ["migration_tool.py", "--backup-only"])
def test_backup_only(mock_migrator_class):
    """Test main function with backup only option"""
    mock_migrator = Mock()
    mock_migrator.create_backup.return_value = Path("/tmp/backup.sql")  # noqa
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(
        os.environ, {"RESOURCES_DB_URL": "postgresql://test:test@localhost:5432/test"}
    ):
        main()

    # Verify only backup was called, not migration
    mock_migrator.create_backup.assert_called_once()
    mock_migrator.run_migration.assert_not_called()


@patch("madsci.resource_manager.migration_tool.DatabaseMigrator")
@patch("sys.argv", ["migration_tool.py", "--restore-from", "/tmp/backup.sql"])  # noqa
def test_restore_from(mock_migrator_class):
    """Test main function with restore from option"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(
        os.environ, {"RESOURCES_DB_URL": "postgresql://test:test@localhost:5432/test"}
    ):
        main()

    # Verify restore was called with correct path
    mock_migrator.restore_from_backup.assert_called_once_with(Path("/tmp/backup.sql"))  # noqa
    mock_migrator.run_migration.assert_not_called()


@patch("madsci.resource_manager.migration_tool.DatabaseMigrator")
@patch("sys.argv", ["migration_tool.py", "--generate-migration", "Test migration"])
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


@patch("subprocess.run")
def test_backup_creation(mock_subprocess, temp_alembic_dir: Path):
    """Test database backup creation"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result

    test_url = "postgresql://test:test@localhost:5432/test"

    with patch.object(
        DatabaseMigrator, "_get_package_root", return_value=temp_alembic_dir
    ):
        migrator = DatabaseMigrator(test_url)
        backup_path = migrator.create_backup()

        # Verify backup path is correct format
        assert backup_path.name.startswith("madsci_backup_")
        assert backup_path.suffix == ".sql"

        # Verify pg_dump was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "pg_dump" in call_args


@patch("madsci.resource_manager.migration_tool.command")
def test_migration_file_generation(mock_command, temp_alembic_dir: Path):
    """Test Alembic migration file generation"""
    test_url = "postgresql://test:test@localhost:5432/test"

    with patch.object(
        DatabaseMigrator, "_get_package_root", return_value=temp_alembic_dir
    ):
        migrator = DatabaseMigrator(test_url)
        migrator.generate_migration("Test migration")

        # Verify Alembic revision command was called
        mock_command.revision.assert_called_once()
        args, kwargs = mock_command.revision.call_args
        assert kwargs["message"] == "Test migration"
        assert kwargs["autogenerate"] is True


def test_migration_file_post_processing(temp_alembic_dir: Path):
    """Test post-processing of migration files for type conversions"""
    test_url = "postgresql://test:test@localhost:5432/test"

    with patch.object(
        DatabaseMigrator, "_get_package_root", return_value=temp_alembic_dir
    ):
        migrator = DatabaseMigrator(test_url)

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
