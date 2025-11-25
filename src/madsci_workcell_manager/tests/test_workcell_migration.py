"""Pytest unit tests for the MADSci Workcell Manager MongoDB migration tools."""

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
def temp_workcell_schema():
    """Create temporary workcell manager schema for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create workcell manager schema
        workcell_manager_dir = temp_path / "madsci" / "workcell_manager"
        workcell_manager_dir.mkdir(parents=True)
        workcell_schema = {
            "database": "madsci_workcells",
            "schema_version": "1.0.0",
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
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
            )

            db_version = checker.get_database_version()
            assert db_version == SemanticVersion(0, 0, 0)

            needs_migration, _, _ = checker.is_migration_needed()
            assert needs_migration is True
        finally:
            schema_file.unlink()


def test_workcell_version_checker_auto_initializes_fresh_database():
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

        schema_file = Path("workcell_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
            )

            # This should auto-initialize without raising an error
            checker.validate_or_fail()

            # Verify that create_schema_versions_collection was called
            mock_collection.create_index.assert_called()
            mock_collection.insert_one.assert_called()
        finally:
            schema_file.unlink()


def test_workcell_version_checker_still_requires_migration_for_existing_db():
    """Test that version checker still requires manual migration for existing databases without version tracking"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_db.list_collection_names.return_value = [
            "archived_workflows"
        ]  # Existing collections but no schema_versions

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        schema_file = Path("workcell_schema.json")
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
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
        "madsci_workcells",
        "--backup_only",
        "true",
    ],
)
def test_workcell_backup_only_command(mock_migrator_class):
    """Test backup only command for workcells database"""
    mock_migrator = Mock()
    backup_dir = Path(tempfile.gettempdir()) / "madsci_workcells_backup"
    mock_migrator.backup_tool.create_backup.return_value = backup_dir
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_backup_command"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "workcell_manager"
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
    mock_migrator.backup_tool.create_backup.assert_called_once()
    mock_migrator.run_migration.assert_not_called()


@patch("subprocess.run")
def test_workcell_backup_creation(mock_subprocess):
    """Test workcells database backup creation using mongodump"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result

    schema_file = Path("workcell_schema.json")
    schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_workcells",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        # Mock the post-backup processing to bypass filesystem checks
        with patch.object(migrator.backup_tool, "_post_backup_processing"):
            backup_path = migrator.backup_tool.create_backup()

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
        "schema_version": "1.0.0",
        "collections": {
            "archived_workflows": {"indexes": []},
            "schema_versions": {"indexes": []},
        },
    }
    schema_file.write_text(json.dumps(schema_content))

    try:
        settings = MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_workcells",
            schema_file=str(schema_file),
        )
        migrator = MongoDBMigrator(settings)

        # Access the database from the migrator instance, not the mock client
        migrator.database.list_collection_names.return_value = []

        migrator._ensure_collection_exists("archived_workflows")

        # Verify archived workflows collection creation was called
        migrator.database.create_collection.assert_called_with("archived_workflows")
    finally:
        schema_file.unlink()


@patch("madsci.common.mongodb_migration_tool.MongoDBMigrator")
@patch(
    "sys.argv",
    [
        "migration_tool.py",
        "--database",
        "madsci_workcells",
        "--check_version",
        "true",
    ],
)
def test_workcell_check_version_command(mock_migrator_class):
    """Test check version command for workcells database"""
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
        schema_dir = temp_dir / "madsci" / "workcell_manager"
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


def test_workcell_version_mismatch_detection():
    """Test detection of version mismatches in workcells database (major/minor versions)"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock existing version tracking with different major/minor version
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
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
            )

            # Schema version is 1.0.0 (minor version difference from DB 0.9.0)
            needs_migration, _, db_version = checker.is_migration_needed()
            assert needs_migration is True
            assert db_version == "0.9.0"
        finally:
            schema_file.unlink()


def test_workcell_patch_version_differences():
    """Test that patch version differences trigger migration in workcells database (schema versions must match exactly)"""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        # Mock existing version tracking with same major.minor but different patch
        mock_collection.find_one.return_value = {"version": "1.0.0"}
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
        schema_file.write_text(json.dumps({"schema_version": "1.0.1"}))

        try:
            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "madsci_workcells", str(schema_file)
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
        "madsci_workcells",
        "--restore_from",
        "workcells_backup",
    ],
)
def test_workcell_restore_command(mock_migrator_class):
    """Test restore command for workcells database"""
    mock_migrator = Mock()
    mock_migrator_class.return_value = mock_migrator

    with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017"}):
        # Create temp schema structure for auto-detection
        temp_dir = Path(tempfile.gettempdir()) / "test_restore"
        temp_dir.mkdir(exist_ok=True)
        schema_dir = temp_dir / "madsci" / "workcell_manager"
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
    mock_migrator.backup_tool.restore_from_backup.assert_called_once_with(
        Path("workcells_backup")
    )
    mock_migrator.run_migration.assert_not_called()


def test_workcell_schema_file_detection():
    """Test automatic detection of workcell manager schema file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create workcell manager schema directory
        workcell_manager_dir = temp_path / "madsci" / "workcell_manager"
        workcell_manager_dir.mkdir(parents=True)
        schema_file = workcell_manager_dir / "schema.json"
        schema_file.write_text(json.dumps({"schema_version": "1.0.0"}))

        original_cwd = Path.cwd()
        os.chdir(temp_path)

        try:
            settings = MongoDBMigrationSettings(database="madsci_workcells")
            detected_path = settings.get_effective_schema_file_path()
            assert detected_path.name == "schema.json"
            assert "workcell_manager" in str(detected_path)
        finally:
            os.chdir(original_cwd)
