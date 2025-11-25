"""Comprehensive tests for PostgreSQL backup CLI interface."""

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner
from madsci.common.backup_tools.postgres_cli import (
    main_postgres_backup,
    postgres_backup,
)


class TestPostgreSQLBackupCLI:
    """Test PostgreSQL backup CLI interface."""

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
    def cli_runner(self) -> CliRunner:
        """Click CLI runner for testing."""
        return CliRunner()

    def test_postgres_backup_group_help(self, cli_runner: CliRunner):
        """Test postgres_backup group shows help."""
        result = cli_runner.invoke(postgres_backup, ["--help"])
        assert result.exit_code == 0
        assert "PostgreSQL backup management commands" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_create_backup(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup creation command."""
        # Setup mock
        mock_tool = MagicMock()
        mock_backup_path = temp_dir / "test_backup.dump"
        mock_tool.create_backup.return_value = mock_backup_path
        mock_tool_class.return_value = mock_tool

        # Test backup creation
        result = cli_runner.invoke(
            postgres_backup,
            ["--db-url", test_db_url, "--backup-dir", str(temp_dir), "create"],
        )

        assert result.exit_code == 0
        assert "Backup created successfully" in result.output
        assert str(mock_backup_path) in result.output

        # Verify tool was created with correct settings
        mock_tool_class.assert_called_once()
        settings = mock_tool_class.call_args[0][0]
        assert settings.db_url == test_db_url
        assert settings.backup_dir == temp_dir

        # Verify backup creation was called
        mock_tool.create_backup.assert_called_once_with(None)

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_create_backup_with_name_suffix(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup creation with custom name suffix."""
        # Setup mock
        mock_tool = MagicMock()
        mock_backup_path = temp_dir / "test_backup_pre_migration.dump"
        mock_tool.create_backup.return_value = mock_backup_path
        mock_tool_class.return_value = mock_tool

        # Test backup creation with suffix
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "--backup-dir",
                str(temp_dir),
                "create",
                "--name-suffix",
                "pre_migration",
            ],
        )

        assert result.exit_code == 0
        assert "Backup created successfully" in result.output

        # Verify backup creation was called with suffix
        mock_tool.create_backup.assert_called_once_with("pre_migration")

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_create_backup_no_validate(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup creation with validation disabled."""
        # Setup mock
        mock_tool = MagicMock()
        mock_backup_path = temp_dir / "test_backup.dump"
        mock_tool.create_backup.return_value = mock_backup_path
        mock_tool_class.return_value = mock_tool

        # Test backup creation with validation disabled
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "--backup-dir",
                str(temp_dir),
                "create",
                "--no-validate",
            ],
        )

        assert result.exit_code == 0

        # Verify tool was created with validation disabled
        settings = mock_tool_class.call_args[0][0]
        assert settings.validate_integrity is False

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_create_backup_different_format(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup creation with different format."""
        # Setup mock
        mock_tool = MagicMock()
        mock_backup_path = temp_dir / "test_backup.sql"
        mock_tool.create_backup.return_value = mock_backup_path
        mock_tool_class.return_value = mock_tool

        # Test backup creation with plain format
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "--backup-dir",
                str(temp_dir),
                "--format",
                "plain",
                "create",
            ],
        )

        assert result.exit_code == 0

        # Verify tool was created with plain format
        settings = mock_tool_class.call_args[0][0]
        assert settings.backup_format == "plain"

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_create_backup_failure(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup creation failure handling."""
        # Setup mock to raise exception
        mock_tool = MagicMock()
        mock_tool.create_backup.side_effect = Exception("Backup failed")
        mock_tool_class.return_value = mock_tool

        # Test backup creation failure
        result = cli_runner.invoke(
            postgres_backup,
            ["--db-url", test_db_url, "--backup-dir", str(temp_dir), "create"],
        )

        assert result.exit_code == 1
        assert "Backup failed: Backup failed" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_list_backups(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup listing command."""
        # Setup mock
        mock_tool = MagicMock()
        mock_backup_info = MagicMock()
        mock_backup_info.backup_path = temp_dir / "backup1.dump"
        mock_backup_info.created_at.strftime.return_value = "2024-01-01 12:00:00"
        mock_backup_info.backup_size = 1024
        mock_tool.list_available_backups.return_value = [mock_backup_info]
        mock_tool_class.return_value = mock_tool

        # Test backup listing
        result = cli_runner.invoke(
            postgres_backup,
            ["--db-url", test_db_url, "--backup-dir", str(temp_dir), "list"],
        )

        assert result.exit_code == 0
        assert "backup1.dump" in result.output
        assert "2024-01-01 12:00:00" in result.output
        assert "1024" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_list_backups_empty(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup listing with no backups."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool.list_available_backups.return_value = []
        mock_tool_class.return_value = mock_tool

        # Test backup listing
        result = cli_runner.invoke(
            postgres_backup,
            ["--db-url", test_db_url, "--backup-dir", str(temp_dir), "list"],
        )

        assert result.exit_code == 0
        assert "No backups found" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_restore_backup(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup restoration command."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup restoration
        result = cli_runner.invoke(
            postgres_backup, ["--db-url", test_db_url, "restore", str(backup_path)]
        )

        assert result.exit_code == 0
        assert "Backup restored successfully" in result.output

        # Verify restore was called
        mock_tool.restore_from_backup.assert_called_once_with(backup_path, None)

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_restore_backup_to_different_database(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup restoration to different database."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup restoration to different database
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "restore",
                str(backup_path),
                "--target-db",
                "different_db",
            ],
        )

        assert result.exit_code == 0
        assert "Backup restored successfully" in result.output

        # Verify restore was called with target database
        mock_tool.restore_from_backup.assert_called_once_with(
            backup_path, "different_db"
        )

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_restore_backup_failure(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup restoration failure handling."""
        # Setup mock to raise exception
        mock_tool = MagicMock()
        mock_tool.restore_from_backup.side_effect = Exception("Restore failed")
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup restoration failure
        result = cli_runner.invoke(
            postgres_backup, ["--db-url", test_db_url, "restore", str(backup_path)]
        )

        assert result.exit_code == 1
        assert "Restore failed: Restore failed" in result.output

    def test_cli_restore_nonexistent_backup(
        self, cli_runner: CliRunner, temp_dir: Path, test_db_url: str
    ):
        """Test CLI restore with nonexistent backup file."""
        backup_path = temp_dir / "nonexistent_backup.dump"

        # Test restore with nonexistent file
        result = cli_runner.invoke(
            postgres_backup, ["--db-url", test_db_url, "restore", str(backup_path)]
        )

        assert result.exit_code == 1
        assert "Backup file does not exist" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_validate_backup(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup validation command."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool.validate_backup_integrity.return_value = True
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup validation
        result = cli_runner.invoke(
            postgres_backup, ["--db-url", test_db_url, "validate", str(backup_path)]
        )

        assert result.exit_code == 0
        assert "Backup is valid" in result.output

        # Verify validation was called
        mock_tool.validate_backup_integrity.assert_called_once_with(backup_path)

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_validate_backup_invalid(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup validation with invalid backup."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool.validate_backup_integrity.return_value = False
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup validation
        result = cli_runner.invoke(
            postgres_backup, ["--db-url", test_db_url, "validate", str(backup_path)]
        )

        assert result.exit_code == 1
        assert "Backup is invalid" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_delete_backup(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup deletion command."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup deletion with confirmation
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "delete",
                str(backup_path),
                "--confirm",  # Skip confirmation prompt
            ],
        )

        assert result.exit_code == 0
        assert "Backup deleted successfully" in result.output

        # Verify deletion was called
        mock_tool.delete_backup.assert_called_once_with(backup_path)

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_delete_backup_failure(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI backup deletion failure handling."""
        # Setup mock to raise exception
        mock_tool = MagicMock()
        mock_tool.delete_backup.side_effect = Exception("Delete failed")
        mock_tool_class.return_value = mock_tool

        backup_path = temp_dir / "test_backup.dump"
        backup_path.write_text("backup content")

        # Test backup deletion failure with confirmation
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "delete",
                str(backup_path),
                "--confirm",  # Skip confirmation prompt
            ],
        )

        assert result.exit_code == 1
        assert "Delete failed: Delete failed" in result.output

    def test_cli_missing_db_url(self, cli_runner: CliRunner):
        """Test CLI error handling for missing database URL."""
        result = cli_runner.invoke(postgres_backup, ["create"])

        assert result.exit_code != 0
        assert "Missing option '--db-url'" in result.output

    def test_cli_invalid_format(self, cli_runner: CliRunner, test_db_url: str):
        """Test CLI error handling for invalid backup format."""
        result = cli_runner.invoke(
            postgres_backup,
            ["--db-url", test_db_url, "--format", "invalid_format", "create"],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--format'" in result.output

    @patch("madsci.common.backup_tools.postgres_cli.PostgreSQLBackupTool")
    def test_cli_with_configuration_options(
        self,
        mock_tool_class: Mock,
        cli_runner: CliRunner,
        temp_dir: Path,
        test_db_url: str,
    ):
        """Test CLI with various configuration options."""
        # Setup mock
        mock_tool = MagicMock()
        mock_backup_path = temp_dir / "test_backup.dump"
        mock_tool.create_backup.return_value = mock_backup_path
        mock_tool_class.return_value = mock_tool

        # Test with all configuration options
        result = cli_runner.invoke(
            postgres_backup,
            [
                "--db-url",
                test_db_url,
                "--backup-dir",
                str(temp_dir),
                "--format",
                "tar",
                "--max-backups",
                "15",
                "--no-compression",
                "create",
            ],
        )

        assert result.exit_code == 0

        # Verify settings were applied
        settings = mock_tool_class.call_args[0][0]
        assert settings.db_url == test_db_url
        assert settings.backup_dir == temp_dir
        assert settings.backup_format == "tar"
        assert settings.max_backups == 15
        assert settings.compression is False

    def test_main_postgres_backup_function(self):
        """Test main entry point function."""
        # Test that main function exists and is callable
        assert callable(main_postgres_backup)

        # Test with help argument (shouldn't crash)
        with patch("sys.argv", ["madsci-postgres-backup", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main_postgres_backup()
            assert exc_info.value.code == 0

    def test_cli_environment_variable_handling(self, cli_runner: CliRunner):
        """Test CLI handles environment variables correctly."""
        with patch.dict("os.environ", {"PGPASSWORD": "secret"}, clear=False):
            result = cli_runner.invoke(
                postgres_backup,
                ["--db-url", "postgresql://user@localhost/db", "create"],
            )
            # Should not leak environment variables in error messages
            assert "secret" not in result.output
