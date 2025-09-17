"""Pytest unit tests for the MADSci Workcell Manager MongoDB migration tools."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.common.mongodb_migration_tool import (
    MongoDBMigrator,
    main,
    resolve_schema_file_path,
)
from madsci.common.mongodb_version_checker import MongoDBVersionChecker


@pytest.fixture
def temp_workcell_schema():
    """Create temporary workcell manager schema for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create workcell manager schema
        workcell_manager_dir = temp_path / "madsci" / "workcell_manager"
        workcell_manager_dir.mkdir(parents=True)
        workcell_schema = {
            "database": "madsci_workcells",
            "version": "1.0.0",
            "description": "Schema definition for MADSci Workcell Manager MongoDB",
            "collections": {
                "archived_workflows": {
                    "description": "Main archived workflows collection",
                    "indexes": [],
                },
                "schema_versions": {
                    "description": "Version tracking",
                    "indexes": [
                        {
                            "keys": [["version", 1]],
                            "name": "version_unique",
                            "unique": True,
                        }
                    ],
                },
            },
        }
        (workcell_manager_dir / "schema.json").write_text(json.dumps(workcell_schema))

        # Change to temp directory
        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            yield workcell_manager_dir / "schema.json"
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def mock_mongo_client_workcells():
    """Mock MongoDB client for workcells database"""
    with patch("madsci.common.mongodb_migration_tool.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Setup mock for workcells database - fix the dictionary access
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        mock_db.list_collection_names.return_value = ["archived_workflows"]
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_db.create_collection = Mock()

        yield mock_client


def test_workcell_version_checker_detects_missing_version_tracking():
    """Test that version checker detects workcells database without version tracking"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_db.list_collection_names.return_value = [
            "archived_workflows"
        ]  # No schema_versions

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("workcell_schema.json")
        schema_file.write_text(json.dumps({"version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
            )

            db_version = checker.get_database_version()
            assert db_version == "NO_VERSION_TRACKING"

            needs_migration, _, _ = checker.is_migration_needed()
            assert needs_migration is True
        finally:
            schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.resolve_schema_file_path")
@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv", ["migration_tool.py", "--database", "madsci_workcells", "--backup-only"]
)
def test_workcell_backup_only_command(mock_migrator_class, mock_resolve_schema):
    """Test backup only command for workcells database"""
    # Mock the schema file resolution
    mock_resolve_schema.return_value = Path("fake_schema.json")

    mock_migrator = Mock()
    backup_dir = Path(tempfile.gettempdir()) / "madsci_workcells_backup"
    mock_migrator.create_backup.return_value = backup_dir
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        main()

    # Verify only backup was called
    mock_migrator.create_backup.assert_called_once()
    mock_migrator.run_migration.assert_not_called()


@patch("subprocess.run")
def test_workcell_backup_creation(mock_subprocess):
    """Test workcells database backup creation using mongodump"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result

    schema_file = Path("workcell_schema.json")
    schema_file.write_text(json.dumps({"version": "1.0.0"}))

    try:
        migrator = MongoDBMigrator(
            "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
        )

        backup_path = migrator.create_backup()

        # Verify backup path format
        assert "madsci_workcells_backup_" in backup_path.name

        # Verify mongodump was called with workcells database
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "mongodump" in call_args
        assert "--db" in call_args
        assert "madsci_workcells" in call_args
    finally:
        schema_file.unlink()


def test_workcell_collection_creation(mock_mongo_client_workcells):  # noqa
    """Test archived workflows collection creation during migration"""
    schema_file = Path("workcell_schema.json")
    schema_content = {
        "version": "1.0.0",
        "collections": {
            "archived_workflows": {"indexes": []},
            "schema_versions": {"indexes": []},
        },
    }
    schema_file.write_text(json.dumps(schema_content))

    try:
        migrator = MongoDBMigrator(
            "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
        )

        # Access the database from the migrator instance, not the mock client
        migrator.database.list_collection_names.return_value = []

        migrator._ensure_collection_exists("archived_workflows")

        # Verify archived workflows collection creation was called
        migrator.database.create_collection.assert_called_with("archived_workflows")
    finally:
        schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.resolve_schema_file_path")
@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    ["migration_tool.py", "--database", "madsci_workcells", "--check-version"],
)
def test_workcell_check_version_command(mock_migrator_class, mock_resolve_schema):
    """Test check version command for workcells database"""
    # Mock the schema file resolution
    mock_resolve_schema.return_value = Path("fake_schema.json")

    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    # Mock version checker
    with patch(
        "madsci.common.mongodb_migration_tool.MongoDBVersionChecker"
    ) as mock_checker_class:
        mock_checker = Mock()
        mock_checker.is_migration_needed.return_value = (False, "1.0.0", "1.0.0")
        mock_checker_class.return_value = mock_checker

        with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
            main()

        # Verify version check was called
        mock_checker.is_migration_needed.assert_called_once()
        mock_migrator.run_migration.assert_not_called()


def test_workcell_version_mismatch_detection():
    """Test detection of version mismatches in workcells database"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock existing version tracking with different version
        mock_collection.find_one.return_value = {"version": "0.9.0"}
        mock_db.list_collection_names.return_value = [
            "archived_workflows",
            "schema_versions",
        ]

        # Fix the dictionary access
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("workcell_schema.json")
        schema_file.write_text(json.dumps({"version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
            )

            needs_migration, _, db_version = checker.is_migration_needed()
            assert needs_migration is True
            assert db_version == "0.9.0"
        finally:
            schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.resolve_schema_file_path")
@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    [
        "migration_tool.py",
        "--database",
        "madsci_workcells",
        "--restore-from",
        "workcells_backup",
    ],
)
def test_workcell_restore_command(mock_migrator_class, mock_resolve_schema):
    """Test restore command for workcells database"""
    # Mock the schema file resolution
    mock_resolve_schema.return_value = Path("fake_schema.json")

    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        main()

    # Verify restore was called with correct path
    mock_migrator.restore_from_backup.assert_called_once_with(Path("workcells_backup"))
    mock_migrator.run_migration.assert_not_called()


def test_workcell_schema_file_detection():
    """Test automatic detection of workcell manager schema file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create schema directory using the generic path structure that resolve_schema_file_path expects
        # The function looks for: madsci/madsci_workcells/schema.json for unknown database names
        workcell_schema_dir = temp_path / "madsci" / "madsci_workcells"
        workcell_schema_dir.mkdir(parents=True)
        schema_file = workcell_schema_dir / "schema.json"
        schema_file.write_text(json.dumps({"version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            detected_path = resolve_schema_file_path("madsci_workcells")
            assert detected_path.name == "schema.json"
            assert "madsci_workcells" in str(detected_path)
        finally:
            os.chdir(original_cwd)
