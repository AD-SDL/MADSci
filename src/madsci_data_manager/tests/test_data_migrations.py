"""Pytest unit tests for the MADSci Data Manager MongoDB migration tools."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.common.mongodb_migration_tool import (
    MongoDBMigrationSettings,
    MongoDBMigrator,
    main,
)
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from pydantic_extra_types.semantic_version import SemanticVersion


@pytest.fixture
def temp_data_schema():
    """Create temporary data manager schema for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create data manager schema
        data_manager_dir = temp_path / "madsci" / "data_manager"
        data_manager_dir.mkdir(parents=True)
        data_schema = {
            "database": "madsci_data",
            "schema_version": "1.0.0",
            "description": "Schema definition for MADSci Data Manager MongoDB",
            "collections": {
                "datapoints": {
                    "description": "Main datapoints collection",
                    "indexes": [
                        {
                            "keys": [["datapoint_id", 1]],
                            "name": "datapoint_id_1",
                            "background": True,
                            "unique": True,
                        }
                    ],
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
        (data_manager_dir / "schema.json").write_text(json.dumps(data_schema))

        # Change to temp directory
        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            yield data_manager_dir / "schema.json"
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def mock_mongo_client_data():
    """Mock MongoDB client for data database"""
    with patch("madsci.common.mongodb_migration_tool.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Setup mock for data database - fix the dictionary access
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        mock_db.list_collection_names.return_value = ["datapoints"]
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_db.create_collection = Mock()

        yield mock_client


def test_data_version_checker_detects_missing_version_tracking():
    """Test that version checker detects data database without version tracking"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_db.list_collection_names.return_value = [
            "datapoints"
        ]  # No schema_versions

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("data_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_data", str(schema_file)
            )

            db_version = checker.get_database_version()
            assert db_version == SemanticVersion(0, 0, 0)

            needs_migration, _, _ = checker.is_migration_needed()
            assert needs_migration is True
        finally:
            schema_file.unlink()


def test_data_version_checker_auto_initializes_fresh_database():
    """Test that version checker auto-initializes completely fresh databases"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock a completely fresh database (no collections)
        mock_db.list_collection_names.return_value = []

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        # Mock the schema_versions collection
        mock_db.__getitem__ = Mock(return_value=mock_collection)

        # Mock find_one to return None (no existing version record)
        mock_collection.find_one.return_value = None

        schema_file = Path("data_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_data", str(schema_file)
            )

            # This should auto-initialize without raising an error
            checker.validate_or_fail()

            # Verify that create_schema_versions_collection was called
            mock_collection.create_index.assert_called()
            mock_collection.insert_one.assert_called()
        finally:
            schema_file.unlink()


def test_data_version_checker_still_requires_migration_for_existing_db():
    """Test that version checker still requires manual migration for existing databases without version tracking"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_db.list_collection_names.return_value = [
            "datapoints"
        ]  # Existing collections but no schema_versions

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("data_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_data", str(schema_file)
            )

            # This should still raise an error requiring manual migration
            with pytest.raises(
                RuntimeError, match="needs version tracking initialization"
            ):
                checker.validate_or_fail()
        finally:
            schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    [
        "migration_tool.py",
        "--database",
        "madsci_data",
        "--backup_only",
        "true",
    ],
)
def test_data_backup_only_command(mock_migrator_class):
    """Test backup only command for data database"""
    mock_migrator = Mock()
    backup_dir = Path(tempfile.gettempdir()) / "madsci_data_backup"
    mock_migrator.create_backup.return_value = backup_dir
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_data_backup_command"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "data_manager"
        schema_dir.mkdir(parents=True, exist_ok=True)
        temp_schema = schema_dir / "schema.json"
        temp_schema.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_dir)

        try:
            main()
        finally:
            os.chdir(original_cwd)

    # Verify only backup was called (now using backup_tool)
    mock_migrator.backup_tool.create_backup.assert_called_once()
    mock_migrator.run_migration.assert_not_called()


@patch("subprocess.run")
def test_data_backup_creation(mock_subprocess):
    """Test data database backup creation using mongodump"""

    def mock_mongodump(*args, **_kwargs):
        """Mock mongodump by creating expected directory structure."""
        # Extract backup path from mongodump command
        cmd = args[0]
        out_index = cmd.index("--out") + 1
        backup_path = Path(cmd[out_index])
        db_name = cmd[cmd.index("--db") + 1]

        # Create the directory structure that mongodump would create
        db_backup_path = backup_path / db_name
        db_backup_path.mkdir(parents=True, exist_ok=True)

        # Create a mock collection file
        (db_backup_path / "datapoints.bson").touch()
        (db_backup_path / "datapoints.metadata.json").touch()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        return mock_result

    mock_subprocess.side_effect = mock_mongodump

    schema_file = Path("data_schema.json")
    schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_data",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        # Use backup tool composition for backup creation
        with patch.object(migrator.backup_tool, "_post_backup_processing"):
            backup_path = migrator.backup_tool.create_backup()

        # Verify backup path format
        assert "madsci_data_backup_" in backup_path.name

        # Verify mongodump was called with data database
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "mongodump" in call_args
        assert "--db" in call_args
        assert "madsci_data" in call_args
    finally:
        schema_file.unlink()


def test_data_collection_creation(mock_mongo_client_data):  # noqa
    """Test datapoints collection creation during migration"""
    schema_file = Path("data_schema.json")
    schema_content = {
        "schema_version": "1.0.0",
        "collections": {
            "datapoints": {"indexes": []},
            "schema_versions": {"indexes": []},
        },
    }
    schema_file.write_text(json.dumps(schema_content))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_data",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        # Access the database from the migrator instance, not the mock client
        migrator.database.list_collection_names.return_value = []

        migrator._ensure_collection_exists("datapoints")

        # Verify datapoints collection creation was called
        migrator.database.create_collection.assert_called_with("datapoints")
    finally:
        schema_file.unlink()


def test_data_index_creation(mock_mongo_client_data):  # noqa
    """Test datapoint_id unique index creation during migration"""
    schema_file = Path("data_schema.json")
    schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_data",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        # Mock collection with proper list_indexes return
        mock_collection = Mock()
        mock_collection.list_indexes.return_value = [{"name": "_id_"}]
        migrator.database.__getitem__.return_value = mock_collection

        # Test datapoint_id unique index creation
        indexes = [
            {
                "keys": [["datapoint_id", 1]],
                "name": "datapoint_id_1",
                "unique": True,
                "background": True,
            }
        ]

        migrator._ensure_indexes_exist("datapoints", indexes)

        # Verify unique index creation was called
        mock_collection.create_index.assert_called_once()
        call_args = mock_collection.create_index.call_args
        assert call_args[0][0] == [("datapoint_id", 1)]
        assert call_args[1]["unique"] is True
        assert call_args[1]["background"] is True
    finally:
        schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    [
        "migration_tool.py",
        "--database",
        "madsci_data",
        "--check_version",
        "true",
    ],
)
def test_data_check_version_command(mock_migrator_class):
    """Test check version command for data database"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    # Mock version checker
    mock_version_checker = Mock()
    mock_version_checker.is_migration_needed.return_value = (False, "1.0.0", "1.0.0")
    mock_migrator.version_checker = mock_version_checker

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_data_check_version"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "data_manager"
        schema_dir.mkdir(parents=True, exist_ok=True)
        temp_schema = schema_dir / "schema.json"
        temp_schema.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_dir)

        try:
            main()
        finally:
            os.chdir(original_cwd)

    # Verify version check was called
    mock_version_checker.is_migration_needed.assert_called_once()
    mock_migrator.run_migration.assert_not_called()


def test_data_version_mismatch_detection():
    """Test detection of version mismatches in data database"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock existing version tracking with different version
        mock_collection.find_one.return_value = {"version": "0.9.0"}
        mock_db.list_collection_names.return_value = ["datapoints", "schema_versions"]

        # Fix the dictionary access
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("data_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_data", str(schema_file)
            )

            needs_migration, _, db_version = checker.is_migration_needed()
            assert needs_migration is True
            assert db_version == "0.9.0"
        finally:
            schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    [
        "migration_tool.py",
        "--database",
        "madsci_data",
        "--restore_from",
        "data_backup",
    ],
)
def test_data_restore_command(mock_migrator_class):
    """Test restore command for data database"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_data_restore"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "data_manager"
        schema_dir.mkdir(parents=True, exist_ok=True)
        temp_schema = schema_dir / "schema.json"
        temp_schema.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_dir)

        try:
            main()
        finally:
            os.chdir(original_cwd)

    # Verify restore was called with correct path (now using backup_tool)
    mock_migrator.backup_tool.restore_from_backup.assert_called_once_with(
        Path("data_backup")
    )
    mock_migrator.run_migration.assert_not_called()


def test_data_schema_file_detection():
    """Test automatic detection of data manager schema file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create data manager schema directory
        data_manager_dir = temp_path / "madsci" / "data_manager"
        data_manager_dir.mkdir(parents=True)
        schema_file = data_manager_dir / "schema.json"
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            settings = MongoDBMigrationSettings(database="madsci_data")
            detected_path = settings.get_effective_schema_file_path()
            assert detected_path.name == "schema.json"
            assert "data_manager" in str(detected_path)
        finally:
            os.chdir(original_cwd)
