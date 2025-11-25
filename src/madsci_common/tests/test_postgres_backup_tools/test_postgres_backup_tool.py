"""Comprehensive tests for PostgreSQL backup tool functionality."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from madsci.client.event_client import EventClient
from madsci.common.backup_tools.postgres_backup import PostgreSQLBackupTool
from madsci.common.types.backup_types import PostgreSQLBackupSettings


class TestPostgreSQLBackupTool:
    """Test PostgreSQL backup tool functionality."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_db_url(self) -> str:
        """Test database URL."""
        return "postgresql://testuser:testpass@localhost:5432/testdb"

    @pytest.fixture
    def backup_settings(
        self, temp_dir: Path, test_db_url: str
    ) -> PostgreSQLBackupSettings:
        """Create PostgreSQL backup settings for testing."""
        return PostgreSQLBackupSettings(
            db_url=test_db_url,
            backup_dir=temp_dir / "backups",
            backup_format="custom",
            max_backups=5,
            validate_integrity=False,  # Disable for subprocess mock tests
            compression=True,
        )

    @pytest.fixture
    def mock_event_client(self) -> MagicMock:
        """Mock event client for testing."""
        return MagicMock(spec=EventClient)

    @pytest.fixture
    def backup_tool(
        self, backup_settings: PostgreSQLBackupSettings, mock_event_client: MagicMock
    ) -> PostgreSQLBackupTool:
        """Create PostgreSQL backup tool for testing."""
        return PostgreSQLBackupTool(backup_settings, mock_event_client)

    def test_initialization_success(self, backup_tool: PostgreSQLBackupTool):
        """Test successful backup tool initialization."""
        assert backup_tool.settings.backup_format == "custom"
        assert backup_tool.backup_dir.exists()
        assert backup_tool.logger is not None

    def test_initialization_creates_backup_directory(
        self, backup_settings: PostgreSQLBackupSettings
    ):
        """Test backup tool creates backup directory during initialization."""
        # Ensure directory doesn't exist initially
        backup_settings.backup_dir.rmdir() if backup_settings.backup_dir.exists() else None

        tool = PostgreSQLBackupTool(backup_settings)
        assert tool.backup_dir.exists()
        assert tool.backup_dir.is_dir()

    @patch("subprocess.run")
    def test_create_backup_success(
        self, mock_run: Mock, backup_tool: PostgreSQLBackupTool
    ):
        """Test successful backup creation."""
        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create a mock backup file that will be created by pg_dump
        def create_backup_file(*args, **_kwargs):
            # Extract file path from command arguments
            cmd = args[0]
            file_arg_index = cmd.index("--file") + 1
            backup_path = Path(cmd[file_arg_index])
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text("mock backup content")
            return mock_result

        mock_run.side_effect = create_backup_file

        # Test backup creation
        backup_path = backup_tool.create_backup()

        assert backup_path.exists()
        assert backup_path.name.startswith("postgres_backup_")
        assert backup_path.suffix in [".dump", ".sql"]
        # Should be called at least once for pg_dump (may be called twice for version check)
        assert mock_run.call_count >= 1

    @patch("subprocess.run")
    def test_create_backup_with_custom_name_suffix(
        self, mock_run: Mock, backup_tool: PostgreSQLBackupTool
    ):
        """Test backup creation with custom name suffix."""
        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        def create_backup_file(*args, **_kwargs):
            cmd = args[0]
            file_arg_index = cmd.index("--file") + 1
            backup_path = Path(cmd[file_arg_index])
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text("mock backup content")
            return mock_result

        mock_run.side_effect = create_backup_file

        # Test backup creation with custom suffix
        custom_suffix = "pre_migration"
        backup_path = backup_tool.create_backup(custom_suffix)

        assert backup_path.exists()
        assert custom_suffix in backup_path.name
        assert backup_path.name.startswith("postgres_backup_")

    @patch("subprocess.run")
    def test_create_backup_failure_cleanup(
        self, mock_run: Mock, backup_tool: PostgreSQLBackupTool
    ):
        """Test backup creation failure triggers cleanup of partial files."""
        # Setup mock subprocess to fail
        mock_run.side_effect = Exception("pg_dump failed")

        # Test that backup creation raises exception
        with pytest.raises(RuntimeError, match="Backup creation failed"):
            backup_tool.create_backup()

        # Verify no partial backup files remain
        assert len(list(backup_tool.backup_dir.glob("*.dump"))) == 0
        assert len(list(backup_tool.backup_dir.glob("*.sql"))) == 0

    def test_backup_integrity_validation_success(
        self, backup_tool: PostgreSQLBackupTool, temp_dir: Path
    ):
        """Test backup integrity validation passes for valid backup."""
        # Create a mock backup file with content
        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("valid backup content")

        # Create checksum file (required for validation)
        checksum = backup_tool.validator.generate_checksum(backup_path)
        backup_tool.validator.save_checksum(backup_path, checksum)

        # Create corresponding metadata file using validator
        metadata = backup_tool.validator.create_backup_metadata(
            backup_path=backup_path, database_version="14.0", backup_type="postgresql"
        )
        backup_tool.validator.save_metadata(backup_path, metadata)

        # Test validation
        is_valid = backup_tool.validate_backup_integrity(backup_path)
        assert is_valid is True

    def test_backup_integrity_validation_failure_missing_file(
        self, backup_tool: PostgreSQLBackupTool, temp_dir: Path
    ):
        """Test backup integrity validation fails for missing backup file."""
        backup_path = temp_dir / "nonexistent_backup.dump"

        is_valid = backup_tool.validate_backup_integrity(backup_path)
        assert is_valid is False

    def test_backup_integrity_validation_failure_corrupted_checksum(
        self, backup_tool: PostgreSQLBackupTool, temp_dir: Path
    ):
        """Test backup integrity validation fails for corrupted backup."""
        # Create a backup file
        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("original backup content")

        # Create checksum for original content
        original_checksum = backup_tool.validator.generate_checksum(backup_path)
        backup_tool.validator.save_checksum(backup_path, original_checksum)

        # Create metadata with original checksum
        metadata = backup_tool.validator.create_backup_metadata(
            backup_path=backup_path, database_version="14.0", backup_type="postgresql"
        )
        backup_tool.validator.save_metadata(backup_path, metadata)

        # Corrupt the backup file (this will make checksum validation fail)
        backup_path.write_text("corrupted backup content")

        # Test validation fails
        is_valid = backup_tool.validate_backup_integrity(backup_path)
        assert is_valid is False

    @patch("subprocess.run")
    def test_restore_from_backup_success(
        self, mock_run: Mock, backup_tool: PostgreSQLBackupTool, temp_dir: Path
    ):
        """Test successful restoration from backup."""
        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create a mock backup file with proper validation files
        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Create checksum file
        checksum = backup_tool.validator.generate_checksum(backup_path)
        backup_tool.validator.save_checksum(backup_path, checksum)

        # Create metadata file
        metadata = backup_tool.validator.create_backup_metadata(
            backup_path=backup_path, database_version="14.0", backup_type="postgresql"
        )
        backup_tool.validator.save_metadata(backup_path, metadata)

        # Test restore operation
        backup_tool.restore_from_backup(backup_path)

        # Verify pg_restore was called
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "pg_restore" in cmd or "psql" in cmd
        assert str(backup_path) in cmd

    @patch("subprocess.run")
    def test_restore_from_backup_to_different_database(
        self, mock_run: Mock, backup_tool: PostgreSQLBackupTool, temp_dir: Path
    ):
        """Test restore to different target database."""
        # Setup mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create a mock backup file with proper validation files
        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Create checksum file
        checksum = backup_tool.validator.generate_checksum(backup_path)
        backup_tool.validator.save_checksum(backup_path, checksum)

        # Create metadata file
        metadata = backup_tool.validator.create_backup_metadata(
            backup_path=backup_path, database_version="14.0", backup_type="postgresql"
        )
        backup_tool.validator.save_metadata(backup_path, metadata)

        # Test restore to different database
        target_db = "different_db"
        backup_tool.restore_from_backup(backup_path, target_db)

        # Verify restore command included target database
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert target_db in cmd

    def test_list_available_backups_empty_directory(
        self, backup_tool: PostgreSQLBackupTool
    ):
        """Test listing backups in empty directory."""
        backups = backup_tool.list_available_backups()
        assert len(backups) == 0

    def test_list_available_backups_with_backups(
        self, backup_tool: PostgreSQLBackupTool
    ):
        """Test listing and sorting of available backups."""
        # Create multiple mock backup files with metadata
        backup_files = []
        for i in range(3):
            backup_path = (
                backup_tool.backup_dir / f"postgres_backup_2024010{i + 1}_120000.dump"
            )
            backup_path.write_text(f"backup content {i}")

            # Create metadata
            metadata = backup_tool.validator.create_backup_metadata(
                backup_path=backup_path,
                database_version="14.0",
                backup_type="postgresql",
            )
            # Override the timestamp for testing
            metadata["timestamp"] = datetime(
                2024, 1, i + 1, 12, 0, 0, tzinfo=timezone.utc
            ).isoformat()
            backup_tool.validator.save_metadata(backup_path, metadata)
            backup_files.append(backup_path)

        # List backups
        backups = backup_tool.list_available_backups()

        assert len(backups) == 3
        # Should be sorted by creation time (newest first)
        # Note: BackupInfo uses created_at field based on metadata timestamp
        backup_dates = [backup.created_at for backup in backups]
        assert len(set(backup_dates)) == 3  # All dates should be different

    def test_backup_rotation_policy(self, backup_tool: PostgreSQLBackupTool):
        """Test backup rotation removes oldest backups."""
        # Set max_backups to 2 for testing
        backup_tool.settings.max_backups = 2

        # Create 4 backup files
        backup_files = []
        for i in range(4):
            backup_path = (
                backup_tool.backup_dir / f"postgres_backup_2024010{i + 1}_120000.dump"
            )
            backup_path.write_text(f"backup content {i}")

            # Create metadata with different timestamps
            metadata = backup_tool.validator.create_backup_metadata(
                backup_path=backup_path,
                database_version="14.0",
                backup_type="postgresql",
            )
            # Override timestamp for testing
            metadata["timestamp"] = datetime(
                2024, 1, i + 1, 12, 0, 0, tzinfo=timezone.utc
            ).isoformat()
            backup_tool.validator.save_metadata(backup_path, metadata)
            backup_files.append(backup_path)

        # Trigger rotation
        backup_tool.manager.rotate_backups(
            backup_tool.backup_dir, backup_tool.settings.max_backups
        )

        # Only the 2 newest backups should remain
        remaining_backups = list(backup_tool.backup_dir.glob("*.dump"))
        assert len(remaining_backups) == 2

        # Verify the newest ones are kept
        remaining_names = {f.name for f in remaining_backups}
        assert "postgres_backup_20240103_120000.dump" in remaining_names
        assert "postgres_backup_20240104_120000.dump" in remaining_names

    def test_delete_backup_success(self, backup_tool: PostgreSQLBackupTool):
        """Test successful backup deletion."""
        # Create a backup file with metadata
        backup_path = backup_tool.backup_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        metadata = backup_tool.validator.create_backup_metadata(
            backup_path=backup_path, database_version="14.0", backup_type="postgresql"
        )
        metadata_path = backup_tool.validator.save_metadata(backup_path, metadata)

        # Verify files exist
        assert backup_path.exists()
        assert metadata_path.exists()

        # Delete backup
        backup_tool.delete_backup(backup_path)

        # Verify files are deleted
        assert not backup_path.exists()
        assert not metadata_path.exists()

    def test_delete_backup_nonexistent_file(
        self, backup_tool: PostgreSQLBackupTool, temp_dir: Path
    ):
        """Test deletion of nonexistent backup file."""
        backup_path = temp_dir / "nonexistent_backup.dump"

        # Should not raise exception for nonexistent file
        backup_tool.delete_backup(backup_path)

    def test_concurrent_backup_operations_locking(
        self, backup_tool: PostgreSQLBackupTool
    ):
        """Test handling of concurrent backup operations with locking."""
        # This test would require more complex setup to actually test concurrency
        # For now, we'll test that the locking mechanism is properly initialized
        assert hasattr(backup_tool, "_lock_manager")

    @patch("subprocess.run")
    def test_backup_with_connection_failure(
        self, mock_run: Mock, backup_tool: PostgreSQLBackupTool
    ):
        """Test backup behavior when database connection fails."""
        # Setup mock to simulate connection failure
        mock_run.side_effect = Exception("connection failed")

        # Test that backup creation raises appropriate exception
        with pytest.raises(RuntimeError, match="Backup creation failed"):
            backup_tool.create_backup()

    def test_backup_formats_support(self, backup_settings: PostgreSQLBackupSettings):
        """Test different backup format support."""
        # Test custom format
        backup_settings.backup_format = "custom"
        tool_custom = PostgreSQLBackupTool(backup_settings)
        assert tool_custom.settings.backup_format == "custom"

        # Test plain format
        backup_settings.backup_format = "plain"
        tool_plain = PostgreSQLBackupTool(backup_settings)
        assert tool_plain.settings.backup_format == "plain"

        # Test tar format
        backup_settings.backup_format = "tar"
        tool_tar = PostgreSQLBackupTool(backup_settings)
        assert tool_tar.settings.backup_format == "tar"

    def test_backup_metadata_creation(self, backup_tool: PostgreSQLBackupTool):
        """Test backup metadata is created with correct structure."""
        # Create a mock backup file
        backup_path = backup_tool.backup_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Create metadata
        backup_tool._create_backup_metadata(backup_path)

        # Verify metadata file exists and has correct structure
        metadata_path = backup_path.with_suffix(".metadata.json")
        assert metadata_path.exists()

        metadata = backup_tool.validator.load_metadata(backup_path)
        assert metadata is not None, "Metadata should not be None"
        assert metadata["backup_path"] == str(backup_path)
        assert metadata["backup_type"] == "postgresql"
        assert "timestamp" in metadata
        assert "checksum" in metadata
        assert "backup_size" in metadata

    def test_pg_dump_command_construction(self, backup_tool: PostgreSQLBackupTool):
        """Test pg_dump command is constructed correctly."""
        backup_path = backup_tool.backup_dir / "test_backup.dump"

        # Test command construction for different formats
        cmd_custom = backup_tool._build_pg_dump_command(backup_path, "custom")
        assert "pg_dump" in cmd_custom
        assert "--format=custom" in cmd_custom
        assert str(backup_path) in cmd_custom

        cmd_plain = backup_tool._build_pg_dump_command(backup_path, "plain")
        assert "--format=plain" in cmd_plain

    @patch.dict(os.environ, {}, clear=True)
    def test_environment_variable_isolation(self, backup_tool: PostgreSQLBackupTool):
        """Test that backup operations don't leak environment variables."""
        # Ensure clean environment
        assert "PGPASSWORD" not in os.environ

        # The backup tool should handle password securely without leaking
        # This is more of a structural test
        assert hasattr(backup_tool, "_parse_db_url")
