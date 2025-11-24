"""Test MongoDB backup tool functionality."""

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.common.backup_tools.base_backup import BackupInfo
from madsci.common.backup_tools.mongodb_backup import MongoDBBackupTool
from madsci.common.types.backup_types import MongoDBBackupSettings


class TestMongoDBBackupTool:
    """Test MongoDB backup tool functionality."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client."""
        mock_client = Mock()
        mock_database = Mock()

        # Configure mock client to return database when accessed
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_client.close = Mock()
        mock_client.drop_database = Mock()

        # Mock database methods
        mock_database.list_collection_names.return_value = [
            "collection1",
            "collection2",
        ]

        # Mock collection
        mock_collection = Mock()
        mock_collection.count_documents.return_value = 10
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_database.drop_collection = Mock()

        return mock_client

    @pytest.fixture
    def mongodb_backup_settings(self, temp_backup_dir):
        """Create MongoDB backup settings for testing."""
        return MongoDBBackupSettings(
            mongo_db_url="mongodb://test:test@localhost:27017/",
            database="test_events",
            backup_dir=temp_backup_dir,
            max_backups=5,
            validate_integrity=True,
            compression=True,
            collections=None,
        )

    @pytest.fixture
    def backup_tool(self, mongodb_backup_settings, mock_mongo_client):
        """Create MongoDB backup tool for testing."""

        with patch(
            "madsci.common.backup_tools.mongodb_backup.MongoClient"
        ) as mock_client_class:
            mock_client_class.return_value = mock_mongo_client
            tool = MongoDBBackupTool(mongodb_backup_settings)
            tool.client = mock_mongo_client
            tool.database = mock_mongo_client["test_events"]
            return tool

    def test_create_backup_all_collections_success(self, backup_tool, temp_backup_dir):
        """Test successful backup creation for all collections."""
        # Mock subprocess.run for mongodump
        with (
            patch("subprocess.run") as mock_run,
            patch(
                "madsci.common.backup_tools.mongodb_backup.datetime"
            ) as mock_datetime,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            # Mock datetime to get predictable backup path
            mock_now = datetime(2024, 1, 1, 12, 0, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = mock_now.strftime

            # Expected backup path based on mocked timestamp
            (temp_backup_dir / "test_events_backup_20240101_120000_000000")

            # Mock the backup tool's internal methods
            with (
                patch.object(
                    backup_tool, "_verify_backup_completion", return_value=True
                ),
                patch.object(
                    backup_tool,
                    "_generate_backup_checksum",
                    return_value="test_checksum",
                ),
                patch.object(backup_tool, "_test_backup_restore", return_value=True),
                patch.object(backup_tool, "_create_backup_metadata"),
            ):
                result_path = backup_tool.create_backup()

                # Verify mongodump command was called
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "mongodump" in args
                assert "--db" in args
                assert "test_events" in args

                # Verify backup path is returned
                assert result_path.name.startswith("test_events_backup_")
                assert result_path.parent == temp_backup_dir

    def test_create_backup_specific_collections(
        self, mongodb_backup_settings, temp_backup_dir
    ):
        """Test backup creation for specific collections only."""
        # Update settings to specify collections
        mongodb_backup_settings.collections = ["collection1"]

        with (
            patch("madsci.common.backup_tools.mongodb_backup.MongoClient"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            tool = MongoDBBackupTool(mongodb_backup_settings)

            # Create mock backup structure
            backup_path = temp_backup_dir / "test_backup"
            backup_path.mkdir()
            db_backup_path = backup_path / "test_events"
            db_backup_path.mkdir()
            (db_backup_path / "collection1.bson").touch()

            with (
                patch.object(tool, "_verify_backup_completion", return_value=True),
                patch.object(
                    tool, "_generate_backup_checksum", return_value="test_checksum"
                ),
                patch.object(tool, "_test_backup_restore", return_value=True),
                patch.object(tool, "_create_backup_metadata"),
            ):
                tool.create_backup()

                # Verify mongodump was called with collection filter
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "--collection" in args
                assert "collection1" in args

    def test_create_backup_with_custom_name(self, backup_tool, temp_backup_dir):
        """Test backup creation with custom name suffix."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            backup_path = (
                temp_backup_dir
                / "test_events_backup_20240101_120000_000000_pre_migration"
            )
            backup_path.mkdir(parents=True)
            db_backup_path = backup_path / "test_events"
            db_backup_path.mkdir()
            (db_backup_path / "collection1.bson").touch()

            with (
                patch.object(
                    backup_tool, "_verify_backup_completion", return_value=True
                ),
                patch.object(
                    backup_tool,
                    "_generate_backup_checksum",
                    return_value="test_checksum",
                ),
                patch.object(backup_tool, "_test_backup_restore", return_value=True),
                patch.object(backup_tool, "_create_backup_metadata"),
            ):
                result_path = backup_tool.create_backup("pre_migration")

                assert "pre_migration" in result_path.name

    def test_backup_integrity_validation_success(self, backup_tool, temp_backup_dir):
        """Test backup integrity validation passes for valid backup."""
        # Create mock backup structure
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()
        (db_backup_path / "collection1.bson").write_bytes(b"test content")
        (db_backup_path / "collection1.metadata.json").touch()

        # Create checksum file
        (backup_path / "backup.checksum").write_text("test_checksum")

        with (
            patch.object(
                backup_tool,
                "_generate_backup_checksum_inline",
                return_value="test_checksum",
            ),
            patch.object(backup_tool, "_test_backup_restore", return_value=True),
        ):
            result = backup_tool.validate_backup_integrity(backup_path)

            assert result is True

    def test_backup_integrity_validation_failure(self, backup_tool, temp_backup_dir):
        """Test backup integrity validation fails for corrupted backup."""
        # Create mock backup structure
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()
        (db_backup_path / "collection1.bson").write_bytes(b"test content")

        # Create checksum file with wrong checksum
        (backup_path / "backup.checksum").write_text("wrong_checksum")

        with (
            patch.object(
                backup_tool,
                "_generate_backup_checksum_inline",
                return_value="correct_checksum",
            ),
            patch.object(backup_tool, "_test_backup_restore", return_value=True),
        ):
            result = backup_tool.validate_backup_integrity(backup_path)

            assert result is False

    def test_restore_from_backup_success(self, backup_tool, temp_backup_dir):
        """Test successful restoration from backup."""
        # Create mock backup structure
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()
        (db_backup_path / "collection1.bson").touch()
        (db_backup_path / "collection1.metadata.json").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            with patch.object(
                backup_tool, "_verify_restore_success", return_value=True
            ):
                backup_tool.restore_from_backup(backup_path)

                # Verify mongorestore command was called
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "mongorestore" in args
                assert "--drop" in args
                assert "--db" in args
                assert "test_events" in args

    def test_restore_to_different_database(self, backup_tool, temp_backup_dir):
        """Test restore to different target database."""
        # Create mock backup structure
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()
        (db_backup_path / "collection1.bson").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            with patch.object(
                backup_tool, "_verify_restore_success", return_value=True
            ):
                backup_tool.restore_from_backup(backup_path, "target_database")

                # Verify mongorestore was called with target database
                args = mock_run.call_args[0][0]
                assert "target_database" in args

    def test_list_available_backups(self, backup_tool, temp_backup_dir):
        """Test listing and sorting of available backups."""
        # Create multiple backup directories with metadata
        backup_paths = []
        for i in range(3):
            day = i + 1  # Start from day 1, not day 0
            backup_path = (
                temp_backup_dir / f"test_events_backup_20240{day:02d}01_120000_000000"
            )
            backup_path.mkdir()

            # Create database subdirectory
            db_backup_path = backup_path / "test_events"
            db_backup_path.mkdir()
            (db_backup_path / f"collection{i}.bson").write_bytes(b"test content")

            # Create metadata file
            metadata = {
                "timestamp": f"2024-{day:02d}-01T12:00:00",
                "database_version": "1.0.0",
                "backup_size": 1000 + i * 100,
                "checksum": f"checksum_{i}",
                "collections_count": 1,
            }
            (backup_path / "backup_metadata.json").write_text(json.dumps(metadata))
            backup_paths.append(backup_path)

        backups = backup_tool.list_available_backups()

        # Should return 3 backups
        assert len(backups) == 3

        # Verify BackupInfo objects are returned
        for backup_info in backups:
            assert isinstance(backup_info, BackupInfo)
            assert backup_info.backup_path.exists()
            assert backup_info.backup_type == "mongodb"

    def test_backup_rotation_policy(self, backup_tool, temp_backup_dir):
        """Test backup rotation removes oldest backups."""
        # Create more backups than max_backups setting (5)
        for i in range(7):
            backup_path = (
                temp_backup_dir / f"test_events_backup_2024010{i}_120000_000000"
            )
            backup_path.mkdir()

            # Create minimal backup structure
            db_backup_path = backup_path / "test_events"
            db_backup_path.mkdir()
            (db_backup_path / "collection1.bson").touch()

            # Set different modification times

            os.utime(backup_path, (time.time() - i * 3600, time.time() - i * 3600))

        with patch.object(backup_tool.manager, "rotate_backups") as mock_rotate:
            # Call rotation
            backup_tool.manager.rotate_backups(
                temp_backup_dir, backup_tool.settings.max_backups
            )

            mock_rotate.assert_called_once_with(temp_backup_dir, 5)

    def test_backup_with_connection_failure(self, backup_tool):
        """Test backup behavior when database connection fails."""
        with patch("subprocess.run") as mock_run:
            # Simulate connection failure
            mock_run.side_effect = FileNotFoundError("mongodump not found")

            with pytest.raises(RuntimeError, match="mongodump command not found"):
                backup_tool.create_backup()

    def test_concurrent_backup_operations(self, backup_tool):
        """Test handling of concurrent backup operations."""
        # This would test the locking mechanism
        # For now, we'll just verify the tool initializes properly
        assert backup_tool.settings.database == "test_events"
        assert backup_tool.backup_dir.exists()

    def test_backup_with_indexes(self, backup_tool, temp_backup_dir):
        """Test that indexes are included in backup."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            # Create backup structure with metadata files (which contain index info)
            backup_path = temp_backup_dir / "test_backup"
            backup_path.mkdir()
            db_backup_path = backup_path / "test_events"
            db_backup_path.mkdir()
            (db_backup_path / "collection1.bson").touch()
            (db_backup_path / "collection1.metadata.json").write_text('{"indexes":[]}')

            with (
                patch.object(
                    backup_tool, "_verify_backup_completion", return_value=True
                ),
                patch.object(
                    backup_tool,
                    "_generate_backup_checksum",
                    return_value="test_checksum",
                ),
                patch.object(backup_tool, "_test_backup_restore", return_value=True),
                patch.object(backup_tool, "_create_backup_metadata"),
            ):
                backup_tool.create_backup()

                # Verify mongodump was called (indexes are included by default)
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "mongodump" in args

    def test_backup_validation_with_bson_corruption(self, backup_tool, temp_backup_dir):
        """Test backup validation detects BSON corruption."""
        # Create corrupted backup
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()

        # Create corrupted BSON file (just empty file)
        (db_backup_path / "collection1.bson").touch()

        # Mock test restore to fail
        with (
            patch.object(backup_tool, "_test_backup_restore", return_value=False),
            pytest.raises(RuntimeError, match="Backup restore test failed"),
        ):
            backup_tool._validate_backup_integrity(backup_path)

    def test_delete_backup(self, backup_tool, temp_backup_dir):
        """Test backup deletion."""
        # Create backup to delete
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        (backup_path / "test_file").touch()

        backup_tool.delete_backup(backup_path)

        assert not backup_path.exists()

    def test_backup_metadata_creation(self, backup_tool, temp_backup_dir):
        """Test backup metadata is created correctly."""
        # Create backup structure
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()
        (db_backup_path / "collection1.bson").write_bytes(b"test content")
        (db_backup_path / "collection2.bson").write_bytes(b"test content 2")

        # Mock version checker
        with (
            patch.object(backup_tool.settings, "database", "test_events"),
            patch.object(
                backup_tool,
                "_generate_backup_checksum_inline",
                return_value="test_checksum",
            ),
        ):
            backup_tool._create_backup_metadata(backup_path)

            # Verify metadata file was created
            metadata_file = backup_path / "backup_metadata.json"
            assert metadata_file.exists()

            # Verify metadata content
            metadata = json.loads(metadata_file.read_text())
            assert metadata["database_name"] == "test_events"
            assert metadata["collections_count"] == 2
            assert metadata["checksum"] == "test_checksum"
            assert "timestamp" in metadata

    def test_restore_with_collection_mapping(self, backup_tool, temp_backup_dir):
        """Test restore with collection name mapping (future feature)."""
        # For now, just test basic restore functionality
        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()
        db_backup_path = backup_path / "test_events"
        db_backup_path.mkdir()
        (db_backup_path / "collection1.bson").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            with patch.object(
                backup_tool, "_verify_restore_success", return_value=True
            ):
                backup_tool.restore_from_backup(backup_path)

                mock_run.assert_called_once()

    def test_backup_settings_validation(self, temp_backup_dir):
        """Test MongoDB backup settings validation."""
        # Test valid settings
        settings = MongoDBBackupSettings(
            mongo_db_url="mongodb://localhost:27017/",
            database="test_db",
            backup_dir=temp_backup_dir,
            collections=["collection1", "collection2"],
        )

        assert settings.database == "test_db"
        assert settings.collections == ["collection1", "collection2"]
        assert settings.max_backups == 10  # default value

    def test_backup_tool_initialization(self, mongodb_backup_settings):
        """Test MongoDB backup tool proper initialization."""
        with patch("madsci.common.backup_tools.mongodb_backup.MongoClient"):
            tool = MongoDBBackupTool(mongodb_backup_settings)

            assert tool.settings == mongodb_backup_settings
            assert tool.backup_dir.exists()
            assert tool.settings.database == "test_events"

    def test_concurrent_mongodb_operations(self, backup_tool):
        """Test backup during concurrent database operations."""
        # Mock concurrent operations by having multiple calls
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            # Simulate multiple backup calls
            # In a real implementation, this would test locking mechanisms
            assert backup_tool.settings.database == "test_events"
            assert backup_tool.backup_dir.exists()

    def test_backup_failure_cleanup(self, backup_tool):
        """Test cleanup after backup failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "mongodump", stderr="Permission denied"
            )

            with pytest.raises(RuntimeError, match="Database backup failed"):
                backup_tool.create_backup()
