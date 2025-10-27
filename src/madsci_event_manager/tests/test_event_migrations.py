"""Pytest unit tests for the MADSci Event Manager MongoDB migration tools."""

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
def temp_event_schema():
    """Create temporary event manager schema for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create event manager schema
        event_manager_dir = temp_path / "madsci" / "event_manager"
        event_manager_dir.mkdir(parents=True)
        event_schema = {
            "database": "madsci_events",
            "schema_version": "1.0.0",
            "description": "Schema definition for MADSci Event Manager MongoDB",
            "collections": {
                "events": {"description": "Main events collection", "indexes": []},
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
        (event_manager_dir / "schema.json").write_text(json.dumps(event_schema))

        # Change to temp directory
        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            yield event_manager_dir / "schema.json"
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def mock_mongo_client_events():
    """Mock MongoDB client for events database"""
    with patch("madsci.common.mongodb_migration_tool.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Setup mock for events database - fix the dictionary access
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        mock_db.list_collection_names.return_value = ["events"]
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_db.create_collection = Mock()

        yield mock_client


def test_event_version_checker_detects_missing_version_tracking():
    """Test that version checker detects events database without version tracking"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_db.list_collection_names.return_value = ["events"]  # No schema_versions

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("event_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_events", str(schema_file)
            )

            db_version = checker.get_database_version()
            assert db_version == SemanticVersion(0, 0, 0)

            needs_migration, _, _ = checker.is_migration_needed()
            assert needs_migration is True
        finally:
            schema_file.unlink()


def test_event_version_checker_auto_initializes_fresh_database():
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

        schema_file = Path("event_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_events", str(schema_file)
            )

            # This should auto-initialize without raising an error
            checker.validate_or_fail()

            # Verify that create_schema_versions_collection was called
            mock_collection.create_index.assert_called()
            mock_collection.insert_one.assert_called()
        finally:
            schema_file.unlink()


def test_event_version_checker_still_requires_migration_for_existing_db():
    """Test that version checker still requires manual migration for existing databases without version tracking"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_db.list_collection_names.return_value = [
            "events"
        ]  # Existing collections but no schema_versions

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("event_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_events", str(schema_file)
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
    ["migration_tool.py", "--database", "madsci_events", "--backup_only", "true"],
)
def test_event_backup_only_command(mock_migrator_class):
    """Test backup only command for events database"""
    # Create a temporary schema file for testing
    schema_file = Path("temp_schema.json")
    schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

    mock_migrator = Mock()
    backup_dir = Path(tempfile.gettempdir()) / "madsci_events_backup"
    mock_migrator.create_backup.return_value = backup_dir
    mock_migrator_class.return_value = mock_migrator

    try:
        with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
            # We need to create a temp schema structure for auto-detection
            temp_dir = Path(tempfile.gettempdir()) / "test_schema_detection"
            temp_dir.mkdir(exist_ok=True)
            schema_dir = temp_dir / "madsci" / "event_manager"
            schema_dir.mkdir(parents=True, exist_ok=True)
            temp_schema = schema_dir / "schema.json"
            temp_schema.write_text(json.dumps({"schema_version": "1.0.0"}))

            original_cwd = Path.cwd()
            os.chdir(temp_dir)

            try:
                main()
            finally:
                os.chdir(original_cwd)

        # Verify only backup was called
        mock_migrator.create_backup.assert_called_once()
        mock_migrator.run_migration.assert_not_called()
    finally:
        if schema_file.exists():
            schema_file.unlink()


@patch("subprocess.run")
@patch("sys.argv", ["test"])
def test_event_backup_creation(mock_subprocess):
    """Test events database backup creation using mongodump"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result

    schema_file = Path("event_schema.json")
    schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_events",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        backup_path = migrator.create_backup()

        # Verify backup path format
        assert "madsci_events_backup_" in backup_path.name

        # Verify mongodump was called with events database
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "mongodump" in call_args
        assert "--db" in call_args
        assert "madsci_events" in call_args
    finally:
        schema_file.unlink()


@patch("sys.argv", ["test"])
def test_event_collection_creation(mock_mongo_client_events):  # noqa
    """Test events collection creation during migration"""
    schema_file = Path("event_schema.json")
    schema_content = {
        "schema_version": "1.0.0",
        "collections": {"events": {"indexes": []}, "schema_versions": {"indexes": []}},
    }
    schema_file.write_text(json.dumps(schema_content))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_events",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        # Access the database from the migrator instance, not the mock client
        migrator.database.list_collection_names.return_value = []

        migrator._ensure_collection_exists("events")

        # Verify events collection creation was called
        migrator.database.create_collection.assert_called_with("events")
    finally:
        schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    ["migration_tool.py", "--database", "madsci_events", "--check_version", "true"],
)
def test_event_check_version_command(mock_migrator_class):
    """Test check version command for events database"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    # Mock version checker
    mock_version_checker = Mock()
    mock_version_checker.is_migration_needed.return_value = (False, "1.0.0", "1.0.0")
    mock_migrator.version_checker = mock_version_checker

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_check_version"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "event_manager"
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


def test_event_schema_version_mismatch_detection():
    """Test detection of schema version mismatches in events database (major/minor versions)"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock existing version tracking with different major/minor version
        mock_collection.find_one.return_value = {"version": "0.9.0"}
        mock_db.list_collection_names.return_value = ["events", "schema_versions"]

        # Fix the dictionary access
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("event_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_events", str(schema_file)
            )

            # Schema version is 1.0.0 (minor version difference from DB 0.9.0)
            needs_migration, _, db_version = checker.is_migration_needed()
            assert needs_migration is True
            assert db_version == "0.9.0"
        finally:
            schema_file.unlink()


def test_event_patch_version_differences():
    """Test that patch version differences trigger migration in events database (schema versions must match exactly)"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock existing version tracking with same major.minor but different patch
        mock_collection.find_one.return_value = {"version": "1.0.0"}
        mock_db.list_collection_names.return_value = ["events", "schema_versions"]

        # Fix the dictionary access
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("event_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.1"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_events", str(schema_file)
            )

            # Schema version is 1.0.1 (patch version difference from DB 1.0.0)
            needs_migration, _, db_version = checker.is_migration_needed()
            assert needs_migration is True  # Should need migration since 1.0.1 != 1.0.0
            assert db_version == SemanticVersion.parse("1.0.0")
        finally:
            schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    [
        "migration_tool.py",
        "--database",
        "madsci_events",
        "--restore_from",
        "events_backup",
    ],
)
def test_event_restore_command(mock_migrator_class):
    """Test restore command for events database"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_restore"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "event_manager"
        schema_dir.mkdir(parents=True, exist_ok=True)
        temp_schema = schema_dir / "schema.json"
        temp_schema.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_dir)

        try:
            main()
        finally:
            os.chdir(original_cwd)

    # Verify restore was called with correct path
    mock_migrator.restore_from_backup.assert_called_once_with(Path("events_backup"))
    mock_migrator.run_migration.assert_not_called()


@patch("sys.argv", ["test"])
def test_event_schema_file_detection():
    """Test automatic detection of event manager schema file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create event manager schema directory
        event_manager_dir = temp_path / "madsci" / "event_manager"
        event_manager_dir.mkdir(parents=True)
        schema_file = event_manager_dir / "schema.json"
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            settings = MongoDBMigrationSettings(database="madsci_events")
            detected_path = settings.get_effective_schema_file_path()
            assert detected_path.name == "schema.json"
            assert "event_manager" in str(detected_path)
        finally:
            os.chdir(original_cwd)
