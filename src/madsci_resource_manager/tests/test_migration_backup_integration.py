"""Tests for migration tools with backup tool composition.

This test module defines the expected behavior for migration tools that use
backup tool composition instead of embedded backup functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.resource_manager.migration_tool import (
    DatabaseMigrationSettings,
    DatabaseMigrator,
)


class TestMigrationBackupIntegration:
    """Test migration tools with backup tool composition."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def migration_settings(self, temp_backup_dir):
        """Create migration settings for testing."""
        return DatabaseMigrationSettings(
            db_url="postgresql://test:test@localhost:5432/test_resources",
            backup_dir=temp_backup_dir,
            target_version="1.0.0",
        )

    @pytest.fixture
    def mock_backup_tool(self):
        """Create mock backup tool for testing."""
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
        """Test migration tool delegates backup operations correctly."""
        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.return_value = Path("/mock/backup/path")

            with (
                patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"),
                patch.object(
                    DatabaseMigrator, "_is_fresh_database", return_value=False
                ),
                patch.object(DatabaseMigrator, "_acquire_migration_lock"),
                patch.object(DatabaseMigrator, "_release_migration_lock"),
                patch.object(DatabaseMigrator, "apply_schema_migrations"),
            ):
                migrator = DatabaseMigrator(migration_settings, mock_logger)
                migrator.version_checker.record_version = Mock()
                migrator.run_migration("1.0.0")

            # Verify backup tool was created with correct settings
            mock_backup_class.assert_called_once()
            created_settings = mock_backup_class.call_args[0][0]
            assert str(created_settings.backup_dir) == str(
                migration_settings.backup_dir
            )
            assert created_settings.db_url == migration_settings.get_effective_db_url()

            # Verify backup was created before migration
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")

    def test_migration_backup_failure_handling(self, migration_settings, mock_logger):
        """Test migration handles backup tool failures gracefully."""
        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            # Simulate backup failure
            mock_backup_tool.create_backup.side_effect = RuntimeError("Backup failed")

            with (
                patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"),
                patch.object(
                    DatabaseMigrator, "_is_fresh_database", return_value=False
                ),
                patch.object(DatabaseMigrator, "_acquire_migration_lock"),
                patch.object(DatabaseMigrator, "_release_migration_lock"),
            ):
                migrator = DatabaseMigrator(migration_settings, mock_logger)

                # Migration should fail when backup fails
                with pytest.raises(RuntimeError, match="Backup failed"):
                    migrator.run_migration("1.0.0")

    def test_migration_with_custom_backup_settings(
        self, migration_settings, mock_logger, temp_backup_dir
    ):
        """Test migration with custom backup configurations."""
        # Modify settings for custom backup configuration
        custom_backup_dir = temp_backup_dir / "custom" / "backup" / "dir"
        migration_settings.backup_dir = custom_backup_dir

        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"):
                DatabaseMigrator(migration_settings, mock_logger)

            # Verify backup tool was created with custom settings
            mock_backup_class.assert_called_once()
            created_settings = mock_backup_class.call_args[0][0]
            assert "custom/backup/dir" in str(created_settings.backup_dir)

    def test_migration_preserves_backup_metadata(self, migration_settings, mock_logger):
        """Test migration preserves all backup metadata."""
        mock_backup_path = Path("/mock/backup/test_backup.dump")

        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.return_value = mock_backup_path

            with (
                patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"),
                patch.object(
                    DatabaseMigrator, "_is_fresh_database", return_value=False
                ),
                patch.object(DatabaseMigrator, "_acquire_migration_lock"),
                patch.object(DatabaseMigrator, "_release_migration_lock"),
                patch.object(DatabaseMigrator, "apply_schema_migrations"),
            ):
                migrator = DatabaseMigrator(migration_settings, mock_logger)
                migrator.version_checker.record_version = Mock()
                migrator.run_migration("1.0.0")

            # Verify backup tool preserved metadata by creating backup with suffix
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")

    def test_migration_failure_triggers_restore(self, migration_settings, mock_logger):
        """Test failed migration triggers backup tool restore."""
        mock_backup_path = Path("/mock/backup/test_backup.dump")

        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.return_value = mock_backup_path

            with (
                patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"),
                patch.object(
                    DatabaseMigrator, "_is_fresh_database", return_value=False
                ),
                patch.object(DatabaseMigrator, "_acquire_migration_lock"),
                patch.object(DatabaseMigrator, "_release_migration_lock"),
                patch.object(DatabaseMigrator, "apply_schema_migrations") as mock_apply,
            ):
                # Simulate migration failure
                mock_apply.side_effect = RuntimeError("Migration failed")

                migrator = DatabaseMigrator(migration_settings, mock_logger)

                # Migration should fail and trigger restore
                with pytest.raises(RuntimeError, match="Migration failed"):
                    migrator.run_migration("1.0.0")

            # Verify backup was created and restore was attempted
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")
            mock_backup_tool.restore_from_backup.assert_called_once_with(
                mock_backup_path
            )

    def test_fresh_database_skips_backup(self, migration_settings, mock_logger):
        """Test fresh database initialization skips backup creation."""
        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with (
                patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"),
                patch.object(DatabaseMigrator, "_is_fresh_database", return_value=True),
                patch.object(DatabaseMigrator, "_acquire_migration_lock"),
                patch.object(DatabaseMigrator, "_release_migration_lock"),
                patch.object(DatabaseMigrator, "apply_schema_migrations"),
            ):
                migrator = DatabaseMigrator(migration_settings, mock_logger)
                migrator.version_checker.record_version = Mock()
                migrator.run_migration("1.0.0")

            # Verify backup tool was created but no backup was made
            mock_backup_class.assert_called_once()
            mock_backup_tool.create_backup.assert_not_called()

    def test_backup_tool_configuration_consistency(
        self, migration_settings, mock_logger
    ):
        """Test backup tool is configured consistently with migration settings."""
        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"):
                DatabaseMigrator(migration_settings, mock_logger)

            # Verify backup tool configuration
            mock_backup_class.assert_called_once()
            backup_settings = mock_backup_class.call_args[0][0]

            # Check key configuration parameters
            assert backup_settings.db_url == migration_settings.get_effective_db_url()
            assert backup_settings.backup_dir == migration_settings.backup_dir
            assert backup_settings.max_backups == 10  # Migration-specific default
            assert (
                backup_settings.validate_integrity is True
            )  # Always validate for migrations
            assert (
                backup_settings.backup_format == "custom"
            )  # Use custom format for faster restore

    def test_backup_tool_logger_integration(self, migration_settings, mock_logger):
        """Test backup tool receives logger from migration tool."""
        with patch(
            "madsci.resource_manager.migration_tool.PostgreSQLBackupTool"
        ) as mock_backup_class:
            mock_backup_tool = Mock()
            mock_backup_class.return_value = mock_backup_tool

            with patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"):
                DatabaseMigrator(migration_settings, mock_logger)

            # Verify backup tool was passed the logger
            mock_backup_class.assert_called_once()
            _, logger_arg = mock_backup_class.call_args
            assert logger_arg["logger"] == mock_logger


class TestDatabaseMigrator:
    """Updated migration tests using backup tool mocks."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def migration_settings(self, temp_backup_dir):
        """Create migration settings for testing."""
        return DatabaseMigrationSettings(
            db_url="postgresql://test:test@localhost:5432/test_resources",
            backup_dir=temp_backup_dir,
            target_version="1.0.0",
        )

    @pytest.fixture
    def mock_backup_tool(self):
        """Create comprehensive mock backup tool for testing."""
        backup_tool = Mock()
        backup_tool.create_backup.return_value = Path("/mock/backup/path")
        backup_tool.restore_from_backup.return_value = None
        backup_tool.validate_backup_integrity.return_value = True
        backup_tool.list_available_backups.return_value = []
        backup_tool.delete_backup.return_value = None
        return backup_tool

    def test_run_migration_with_backup_tool(self, migration_settings, mock_backup_tool):
        """Test migration workflow with mocked backup tool."""
        with (
            patch(
                "madsci.resource_manager.migration_tool.PostgreSQLBackupTool",
                return_value=mock_backup_tool,
            ),
            patch(
                "madsci.resource_manager.migration_tool.DatabaseVersionChecker"
            ) as mock_version_checker_class,
            patch.object(DatabaseMigrator, "_is_fresh_database", return_value=False),
            patch.object(DatabaseMigrator, "_acquire_migration_lock"),
            patch.object(DatabaseMigrator, "_release_migration_lock"),
            patch.object(DatabaseMigrator, "apply_schema_migrations"),
        ):
            mock_version_checker = Mock()
            mock_version_checker_class.return_value = mock_version_checker
            mock_version_checker.record_version = Mock()

            migrator = DatabaseMigrator(migration_settings)
            migrator.run_migration("1.0.0")

        # Verify backup tool interaction
        mock_backup_tool.create_backup.assert_called_once_with("pre_migration")
        mock_version_checker.record_version.assert_called_once()

    def test_migration_failure_triggers_restore(
        self, migration_settings, mock_backup_tool
    ):
        """Test failed migration triggers backup tool restore."""
        mock_backup_path = Path("/mock/backup/test_backup.dump")
        mock_backup_tool.create_backup.return_value = mock_backup_path

        with (
            patch(
                "madsci.resource_manager.migration_tool.PostgreSQLBackupTool",
                return_value=mock_backup_tool,
            ),
            patch("madsci.resource_manager.migration_tool.DatabaseVersionChecker"),
            patch.object(DatabaseMigrator, "_is_fresh_database", return_value=False),
            patch.object(DatabaseMigrator, "_acquire_migration_lock"),
            patch.object(DatabaseMigrator, "_release_migration_lock"),
            patch.object(DatabaseMigrator, "apply_schema_migrations") as mock_apply,
        ):
            # Simulate migration failure
            mock_apply.side_effect = RuntimeError("Migration failed")

            migrator = DatabaseMigrator(migration_settings)

            # Migration should fail and trigger restore
            with pytest.raises(RuntimeError, match="Migration failed"):
                migrator.run_migration("1.0.0")

        # Verify restore was called with correct backup path
        mock_backup_tool.restore_from_backup.assert_called_once_with(mock_backup_path)
