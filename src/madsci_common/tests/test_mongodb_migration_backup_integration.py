"""Tests for MongoDB migration tools with backup tool composition.

This test module defines the expected behavior for MongoDB migration tools that use
backup tool composition instead of embedded backup functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.common.mongodb_migration_tool import (
    MongoDBMigrator,
)
from madsci.common.types.mongodb_migration_types import MongoDBMigrationSettings


class TestMongoDBMigrationBackupIntegration:
    """Test MongoDB migration tools with backup tool composition."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def migration_settings(self, temp_backup_dir):
        """Create MongoDB migration settings for testing."""
        return MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_events",
            backup_dir=temp_backup_dir,
            target_version="1.0.0",
        )

    @pytest.fixture
    def mock_backup_tool(self):
        """Create mock MongoDB backup tool for testing."""
        backup_tool = Mock()
        backup_tool.create_backup.return_value = Path("/mock/backup/path")
        backup_tool.restore_from_backup.return_value = None
        backup_tool.validate_backup_integrity.return_value = True
        backup_tool.list_available_backups.return_value = []
        return backup_tool

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger for testing."""
        return Mock()

    def test_migration_uses_backup_tool(self, migration_settings, mock_logger):
        """Test MongoDB migration tool delegates backup operations correctly."""
        # Mock schema file path to avoid auto-detection issues
        with patch(
            "madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings.get_effective_schema_file_path",
            return_value=Path("/mock/schema.json"),
        ):
            with patch(
                "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
            ) as mock_backup_class:
                mock_backup_tool = Mock()
                mock_backup_class.return_value = mock_backup_tool
                mock_backup_tool.create_backup.return_value = Path("/mock/backup/path")

                with (
                    patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                    patch("madsci.common.mongodb_migration_tool.MongoClient"),
                    patch.object(MongoDBMigrator, "apply_schema_migrations"),
                ):
                    migrator = MongoDBMigrator(migration_settings, mock_logger)
                    migrator.version_checker.record_version = Mock()
                    migrator.version_checker.get_expected_schema_version = Mock(
                        return_value="1.0.0"
                    )
                    migrator.version_checker.get_database_version = Mock(
                        return_value="0.9.0"
                    )
                    migrator.run_migration("1.0.0")

            # Verify backup tool was created with correct settings
            mock_backup_class.assert_called_once()
            created_settings = mock_backup_class.call_args[0][0]
            assert str(created_settings.backup_dir) == str(
                migration_settings.backup_dir
            )
            assert str(created_settings.mongo_db_url) == str(
                migration_settings.mongo_db_url
            )
            assert created_settings.database == migration_settings.database

            # Verify backup was created before migration
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")

    def test_migration_backup_failure_handling(self, migration_settings, mock_logger):
        """Test MongoDB migration handles backup tool failures gracefully."""
        with patch(
            "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            # Simulate backup failure
            mock_backup_tool.create_backup.side_effect = RuntimeError("Backup failed")

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
            ):
                migrator = MongoDBMigrator(migration_settings, mock_logger)

                # Migration should fail when backup fails
                with pytest.raises(RuntimeError, match="Backup failed"):
                    migrator.run_migration("1.0.0")

    def test_migration_with_custom_backup_settings(
        self, migration_settings, mock_logger, temp_backup_dir
    ):
        """Test MongoDB migration with custom backup configurations."""
        # Modify settings for custom backup configuration
        custom_backup_path = temp_backup_dir / "custom" / "backup" / "dir"
        migration_settings.backup_dir = custom_backup_path
        migration_settings.database = "madsci_events"  # Use supported database name

        with (
            patch(
                "madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings.get_effective_schema_file_path",
                return_value=Path("/mock/schema.json"),
            ),
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
            ) as mock_backup_class,
        ):
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
            ):
                MongoDBMigrator(migration_settings, mock_logger)

            # Verify backup tool was created with custom settings
            mock_backup_class.assert_called_once()
            created_settings = mock_backup_class.call_args[0][0]
            assert str(created_settings.backup_dir) == str(
                migration_settings.backup_dir
            )
            assert created_settings.database == "madsci_events"

    def test_migration_preserves_backup_metadata(self, migration_settings, mock_logger):
        """Test MongoDB migration preserves all backup metadata."""
        mock_backup_path = Path("/mock/backup/events_backup_20240101_120000")

        with patch(
            "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.return_value = mock_backup_path

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
                patch.object(MongoDBMigrator, "apply_schema_migrations"),
            ):
                migrator = MongoDBMigrator(migration_settings, mock_logger)
                migrator.version_checker.record_version = Mock()
                migrator.version_checker.get_expected_schema_version = Mock(
                    return_value="1.0.0"
                )
                migrator.version_checker.get_database_version = Mock(
                    return_value="0.9.0"
                )
                migrator.run_migration("1.0.0")

            # Verify backup tool preserved metadata by creating backup with suffix
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")

    def test_migration_failure_triggers_restore(self, migration_settings, mock_logger):
        """Test failed MongoDB migration triggers backup tool restore."""
        mock_backup_path = Path("/mock/backup/events_backup_20240101_120000")

        with patch(
            "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.return_value = mock_backup_path

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
                patch.object(MongoDBMigrator, "apply_schema_migrations") as mock_apply,
            ):
                # Simulate migration failure
                mock_apply.side_effect = RuntimeError("Migration failed")

                migrator = MongoDBMigrator(migration_settings, mock_logger)
                migrator.version_checker.get_expected_schema_version = Mock(
                    return_value="1.0.0"
                )
                migrator.version_checker.get_database_version = Mock(
                    return_value="0.9.0"
                )

                # Migration should fail and trigger restore
                with pytest.raises(RuntimeError, match="Migration failed"):
                    migrator.run_migration("1.0.0")

            # Verify backup was created and restore was attempted
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")
            mock_backup_tool.restore_from_backup.assert_called_once_with(
                mock_backup_path
            )

    def test_backup_tool_configuration_consistency(
        self, migration_settings, mock_logger
    ):
        """Test MongoDB backup tool is configured consistently with migration settings."""
        with (
            patch(
                "madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings.get_effective_schema_file_path",
                return_value=Path("/mock/schema.json"),
            ),
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
            ) as mock_backup_class,
        ):
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
            ):
                MongoDBMigrator(migration_settings, mock_logger)

            # Verify backup tool configuration
            mock_backup_class.assert_called_once()
            backup_settings = mock_backup_class.call_args[0][0]

            # Check key configuration parameters
            assert str(backup_settings.mongo_db_url) == str(
                migration_settings.mongo_db_url
            )
            assert backup_settings.database == migration_settings.database
            assert str(backup_settings.backup_dir) == str(migration_settings.backup_dir)
            assert backup_settings.max_backups == 10  # Migration-specific default
            assert (
                backup_settings.validate_integrity is True
            )  # Always validate for migrations

    def test_backup_tool_logger_integration(self, migration_settings, mock_logger):
        """Test MongoDB backup tool receives logger from migration tool."""
        with patch(
            "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
            ):
                MongoDBMigrator(migration_settings, mock_logger)

            # Verify backup tool was passed the logger
            mock_backup_class.assert_called_once()
            _, logger_arg = mock_backup_class.call_args
            assert logger_arg.get("logger") == mock_logger

    def test_collection_specific_backup_settings(self, migration_settings, mock_logger):
        """Test MongoDB backup tool handles collection-specific settings."""
        # Test that backup tool correctly handles None collections (default case)

        with (
            patch(
                "madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings.get_effective_schema_file_path",
                return_value=Path("/mock/schema.json"),
            ),
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBBackupTool"
            ) as mock_backup_class,
        ):
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with (
                patch("madsci.common.mongodb_migration_tool.MongoDBVersionChecker"),
                patch("madsci.common.mongodb_migration_tool.MongoClient"),
            ):
                MongoDBMigrator(migration_settings, mock_logger)

            # Verify backup tool configuration
            mock_backup_class.assert_called_once()
            backup_settings = mock_backup_class.call_args[0][0]
            # Default case should have no specific collections (None)
            assert backup_settings.collections is None


class TestMongoDBMigrator:
    """Updated MongoDB migration tests using backup tool mocks."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def migration_settings(self, temp_backup_dir):
        """Create MongoDB migration settings for testing."""
        return MongoDBMigrationSettings(
            mongo_db_url="mongodb://localhost:27017",
            database="madsci_events",
            backup_dir=temp_backup_dir,
            target_version="1.0.0",
        )

    @pytest.fixture
    def mock_backup_tool(self):
        """Create comprehensive mock MongoDB backup tool for testing."""
        backup_tool = Mock()
        backup_tool.create_backup.return_value = Path("/mock/backup/path")
        backup_tool.restore_from_backup.return_value = None
        backup_tool.validate_backup_integrity.return_value = True
        backup_tool.list_available_backups.return_value = []
        backup_tool.delete_backup.return_value = None
        return backup_tool

    def test_run_migration_with_backup_tool(self, migration_settings, mock_backup_tool):
        """Test MongoDB migration workflow with mocked backup tool."""
        with (
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBBackupTool",
                return_value=mock_backup_tool,
            ),
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBVersionChecker"
            ) as mock_version_checker_class,
            patch("madsci.common.mongodb_migration_tool.MongoClient"),
            patch.object(MongoDBMigrator, "apply_schema_migrations"),
        ):
            mock_version_checker = Mock()
            mock_version_checker_class.return_value = mock_version_checker
            mock_version_checker.record_version = Mock()
            mock_version_checker.get_expected_schema_version.return_value = "1.0.0"
            mock_version_checker.get_database_version.return_value = "0.9.0"

            migrator = MongoDBMigrator(migration_settings)
            migrator.run_migration("1.0.0")

        # Verify backup tool interaction
        mock_backup_tool.create_backup.assert_called_once_with("pre_migration")
        mock_version_checker.record_version.assert_called_once()

    def test_migration_failure_triggers_restore(
        self, migration_settings, mock_backup_tool
    ):
        """Test failed MongoDB migration triggers backup tool restore."""
        mock_backup_path = Path("/mock/backup/events_backup_20240101_120000")
        mock_backup_tool.create_backup.return_value = mock_backup_path

        with (
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBBackupTool",
                return_value=mock_backup_tool,
            ),
            patch(
                "madsci.common.mongodb_migration_tool.MongoDBVersionChecker"
            ) as mock_version_checker_class,
            patch("madsci.common.mongodb_migration_tool.MongoClient"),
            patch.object(MongoDBMigrator, "apply_schema_migrations") as mock_apply,
        ):
            mock_version_checker = Mock()
            mock_version_checker_class.return_value = mock_version_checker
            mock_version_checker.get_expected_schema_version.return_value = "1.0.0"
            mock_version_checker.get_database_version.return_value = "0.9.0"

            # Simulate migration failure
            mock_apply.side_effect = RuntimeError("Migration failed")

            migrator = MongoDBMigrator(migration_settings)

            # Migration should fail and trigger restore
            with pytest.raises(RuntimeError, match="Migration failed"):
                migrator.run_migration("1.0.0")

        # Verify restore was called with correct backup path
        mock_backup_tool.restore_from_backup.assert_called_once_with(mock_backup_path)
