"""Test MongoDB backup CLI interface."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from madsci.common.backup_tools.base_backup import BackupInfo
from madsci.common.backup_tools.cli import mongodb_backup


class TestMongoDBBackupCLI:
    """Test MongoDB backup CLI interface."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def cli_runner(self):
        """Create Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_backup_tool(self, temp_backup_dir):
        """Create mock backup tool for CLI testing."""
        mock_tool = Mock()
        mock_tool.create_backup.return_value = temp_backup_dir / "test_backup"
        mock_tool.list_available_backups.return_value = []
        mock_tool.validate_backup_integrity.return_value = True
        mock_tool.restore_from_backup.return_value = None
        mock_tool.delete_backup.return_value = None
        return mock_tool

    def test_cli_create_backup(self, cli_runner, temp_backup_dir, mock_backup_tool):
        """Test CLI backup creation command."""

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.return_value = Path(
                str(temp_backup_dir / "test_backup")
            )

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "--backup-dir",
                    str(temp_backup_dir),
                    "create",
                ],
            )

            assert result.exit_code == 0
            assert "Backup created successfully" in result.output
            mock_backup_tool.create_backup.assert_called_once_with(None)

    def test_cli_create_backup_with_name_suffix(self, cli_runner, mock_backup_tool):
        """Test CLI backup creation with custom name suffix."""

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "create",
                    "--name-suffix",
                    "pre_migration",
                ],
            )

            assert result.exit_code == 0
            mock_backup_tool.create_backup.assert_called_once_with("pre_migration")

    def test_cli_create_backup_no_validation(self, cli_runner, mock_backup_tool):
        """Test CLI backup creation with validation disabled."""

        with (
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupTool"
            ) as mock_tool_class,
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupSettings"
            ) as mock_settings,
        ):
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "create",
                    "--no-validate",
                ],
            )

            assert result.exit_code == 0
            # Verify settings were created with validation disabled
            mock_settings.assert_called_once()
            call_kwargs = mock_settings.call_args.kwargs
            assert call_kwargs["validate_integrity"] is False

    def test_cli_create_backup_specific_collections(self, cli_runner, mock_backup_tool):
        """Test CLI backup creation for specific collections."""

        with (
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupTool"
            ) as mock_tool_class,
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupSettings"
            ) as mock_settings,
        ):
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "create",
                    "--collections",
                    "collection1,collection2",
                ],
            )

            assert result.exit_code == 0
            # Verify collections were passed to settings
            mock_settings.assert_called_once()
            call_kwargs = mock_settings.call_args.kwargs
            assert call_kwargs["collections"] == ["collection1", "collection2"]

    def test_cli_list_backups(self, cli_runner, temp_backup_dir, mock_backup_tool):
        """Test CLI backup listing command."""
        # Create mock backup info (use larger size to see in MB)
        mock_backup_info = BackupInfo(
            backup_path=temp_backup_dir / "test_backup",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            database_version="1.0.0",
            backup_size=2097152,  # 2 MB in bytes
            checksum="test_checksum",
            backup_type="mongodb",
            is_valid=True,
        )

        mock_backup_tool.list_available_backups.return_value = [mock_backup_info]

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "list",
                ],
            )

            assert result.exit_code == 0
            assert "test_backup" in result.output
            assert "2024-01-01 12:00:00" in result.output
            assert "2.0 MB" in result.output  # 2097152 bytes displayed as 2.0 MB
            mock_backup_tool.list_available_backups.assert_called_once()

    def test_cli_list_backups_empty(self, cli_runner, mock_backup_tool):
        """Test CLI backup listing with no backups."""

        mock_backup_tool.list_available_backups.return_value = []

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "list",
                ],
            )

            assert result.exit_code == 0
            assert "No backups found" in result.output

    def test_cli_restore_backup(self, cli_runner, temp_backup_dir, mock_backup_tool):
        """Test CLI backup restoration command."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "restore",
                    str(backup_path),
                ],
            )

            assert result.exit_code == 0
            assert "Restore completed successfully" in result.output
            mock_backup_tool.restore_from_backup.assert_called_once_with(
                backup_path, None
            )

    def test_cli_restore_to_different_database(
        self, cli_runner, temp_backup_dir, mock_backup_tool
    ):
        """Test CLI restore to different target database."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "restore",
                    str(backup_path),
                    "--target-database",
                    "target_db",
                ],
            )

            assert result.exit_code == 0
            mock_backup_tool.restore_from_backup.assert_called_once_with(
                backup_path, "target_db"
            )

    def test_cli_validate_backup(self, cli_runner, temp_backup_dir, mock_backup_tool):
        """Test CLI backup validation command."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool
            mock_backup_tool.validate_backup_integrity.return_value = True

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "validate",
                    str(backup_path),
                ],
            )

            assert result.exit_code == 0
            assert "Backup validation successful" in result.output
            mock_backup_tool.validate_backup_integrity.assert_called_once_with(
                backup_path
            )

    def test_cli_validate_backup_failure(
        self, cli_runner, temp_backup_dir, mock_backup_tool
    ):
        """Test CLI backup validation failure."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool
            mock_backup_tool.validate_backup_integrity.return_value = False

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "validate",
                    str(backup_path),
                ],
            )

            assert result.exit_code == 1
            assert "Backup validation failed" in result.output

    def test_cli_delete_backup(self, cli_runner, temp_backup_dir, mock_backup_tool):
        """Test CLI backup deletion command."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            # Provide 'y' input to confirm deletion
            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "delete",
                    str(backup_path),
                ],
                input="y\n",
            )

            assert result.exit_code == 0
            assert "Backup deleted successfully" in result.output
            mock_backup_tool.delete_backup.assert_called_once_with(backup_path)

    def test_cli_delete_backup_cancelled(
        self, cli_runner, temp_backup_dir, mock_backup_tool
    ):
        """Test CLI backup deletion cancelled by user."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            # Provide 'n' input to cancel deletion
            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "delete",
                    str(backup_path),
                ],
                input="n\n",
            )

            assert result.exit_code == 0
            assert "Deletion cancelled" in result.output
            mock_backup_tool.delete_backup.assert_not_called()

    def test_cli_delete_backup_force(
        self, cli_runner, temp_backup_dir, mock_backup_tool
    ):
        """Test CLI backup deletion with force flag."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "delete",
                    str(backup_path),
                    "--force",
                ],
            )

            assert result.exit_code == 0
            assert "Backup deleted successfully" in result.output
            mock_backup_tool.delete_backup.assert_called_once_with(backup_path)

    def test_cli_error_handling_create_failure(self, cli_runner, mock_backup_tool):
        """Test CLI error handling for backup creation failure."""

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool
            mock_backup_tool.create_backup.side_effect = RuntimeError("Backup failed")

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "create",
                ],
            )

            assert result.exit_code == 1
            assert "Backup failed" in result.output

    def test_cli_error_handling_restore_failure(
        self, cli_runner, temp_backup_dir, mock_backup_tool
    ):
        """Test CLI error handling for restore failure."""

        backup_path = temp_backup_dir / "test_backup"
        backup_path.mkdir()

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool
            mock_backup_tool.restore_from_backup.side_effect = RuntimeError(
                "Restore failed"
            )

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "restore",
                    str(backup_path),
                ],
            )

            assert result.exit_code == 1
            assert "Restore failed" in result.output

    def test_cli_invalid_backup_path(self, cli_runner, mock_backup_tool):
        """Test CLI with non-existent backup path."""

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "restore",
                    "/non/existent/path",
                ],
            )

            assert result.exit_code == 1
            assert "Backup path does not exist" in result.output

    def test_cli_configuration_file_support(
        self, cli_runner, temp_backup_dir, mock_backup_tool
    ):
        """Test CLI supports configuration files."""

        # Create config file
        config_file = temp_backup_dir / "config.json"
        config_data = {
            "mongo_db_url": "mongodb://localhost:27017/",
            "database": "test_db",
            "backup_dir": str(temp_backup_dir),
            "max_backups": 5,
        }
        config_file.write_text(json.dumps(config_data))

        with (
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupTool"
            ) as mock_tool_class,
            patch("madsci.common.backup_tools.cli.MongoDBBackupSettings"),
        ):
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup, ["--config-file", str(config_file), "create"]
            )

            assert result.exit_code == 0

    def test_cli_help_commands(self, cli_runner):
        """Test CLI help commands work correctly."""

        # Test main help
        result = cli_runner.invoke(mongodb_backup, ["--help"])
        assert result.exit_code == 0
        assert "MongoDB backup management commands" in result.output

        # Test create help (provide required parent options)
        result = cli_runner.invoke(
            mongodb_backup,
            [
                "--mongo-url",
                "mongodb://localhost:27017/",
                "--database",
                "test_db",
                "create",
                "--help",
            ],
        )
        assert result.exit_code == 0
        assert "Create a new MongoDB backup" in result.output

        # Test restore help (provide required parent options)
        result = cli_runner.invoke(
            mongodb_backup,
            [
                "--mongo-url",
                "mongodb://localhost:27017/",
                "--database",
                "test_db",
                "restore",
                "--help",
            ],
        )
        assert result.exit_code == 0
        assert "Restore from MongoDB backup" in result.output

    def test_cli_missing_required_options(self, cli_runner):
        """Test CLI with missing required options."""

        # Test create without required options
        result = cli_runner.invoke(mongodb_backup, ["create"])
        assert result.exit_code != 0
        assert "MongoDB URL is required" in result.output

    def test_cli_verbose_output(self, cli_runner, mock_backup_tool):
        """Test CLI verbose output option."""

        with patch(
            "madsci.common.backup_tools.cli.MongoDBBackupTool"
        ) as mock_tool_class:
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "--verbose",
                    "create",
                ],
            )

            assert result.exit_code == 0

    def test_cli_compression_option(self, cli_runner, mock_backup_tool):
        """Test CLI compression option."""

        with (
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupTool"
            ) as mock_tool_class,
            patch(
                "madsci.common.backup_tools.cli.MongoDBBackupSettings"
            ) as mock_settings,
        ):
            mock_tool_class.return_value = mock_backup_tool

            result = cli_runner.invoke(
                mongodb_backup,
                [
                    "--mongo-url",
                    "mongodb://localhost:27017/",
                    "--database",
                    "test_db",
                    "create",
                    "--no-compression",
                ],
            )

            assert result.exit_code == 0
            # Verify compression was disabled
            mock_settings.assert_called_once()
            call_kwargs = mock_settings.call_args.kwargs
            assert call_kwargs["compression"] is False
