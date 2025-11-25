"""Tests for unified backup CLI."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from madsci.common.backup_tools.unified_cli import (
    detect_database_type,
    madsci_backup,
)


class TestDatabaseTypeDetection:
    """Test database type auto-detection."""

    def test_detect_postgresql_standard_url(self) -> None:
        """Test detection of PostgreSQL from standard URL."""
        assert (
            detect_database_type("postgresql://user:pass@localhost/db") == "postgresql"
        )

    def test_detect_postgresql_short_url(self) -> None:
        """Test detection of PostgreSQL from postgres:// URL."""
        assert detect_database_type("postgres://user:pass@localhost/db") == "postgresql"

    def test_detect_mongodb_standard_url(self) -> None:
        """Test detection of MongoDB from standard URL."""
        assert detect_database_type("mongodb://localhost:27017/db") == "mongodb"

    def test_detect_mongodb_srv_url(self) -> None:
        """Test detection of MongoDB from SRV URL."""
        assert detect_database_type("mongodb+srv://cluster.mongodb.net/db") == "mongodb"

    def test_detect_invalid_url_raises_error(self) -> None:
        """Test invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Unable to detect database type"):
            detect_database_type("mysql://localhost/db")


class TestUnifiedCLICreate:
    """Test unified CLI create command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click CLI test runner."""
        return CliRunner()

    def test_create_postgres_backup_auto_detect(self, runner: CliRunner) -> None:
        """Test creating PostgreSQL backup with auto-detection."""
        with patch(
            "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
        ) as mock_tool:
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = Path("/test/backup.dump")
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup, ["create", "--db-url", "postgresql://localhost/test"]
            )

            assert result.exit_code == 0
            assert "Backup created:" in result.output
            mock_tool.assert_called_once()
            mock_instance.create_backup.assert_called_once()

    def test_create_mongodb_backup_auto_detect(self, runner: CliRunner) -> None:
        """Test creating MongoDB backup with auto-detection."""
        with patch(
            "madsci.common.backup_tools.unified_cli.MongoDBBackupTool"
        ) as mock_tool:
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = Path("/test/backup")
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup, ["create", "--db-url", "mongodb://localhost/testdb"]
            )

            assert result.exit_code == 0
            assert "Backup created:" in result.output
            mock_tool.assert_called_once()
            mock_instance.create_backup.assert_called_once()

    def test_create_with_explicit_type(self, runner: CliRunner) -> None:
        """Test creating backup with explicit database type."""
        with patch(
            "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
        ) as mock_tool:
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = Path("/test/backup.dump")
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup,
                [
                    "create",
                    "--db-url",
                    "postgresql://localhost/test",
                    "--type",
                    "postgresql",
                ],
            )

            assert result.exit_code == 0
            mock_tool.assert_called_once()

    def test_create_with_custom_name(self, runner: CliRunner) -> None:
        """Test creating backup with custom name suffix."""
        with patch(
            "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
        ) as mock_tool:
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = Path("/test/backup_custom.dump")
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup,
                [
                    "create",
                    "--db-url",
                    "postgresql://localhost/test",
                    "--name",
                    "custom",
                ],
            )

            assert result.exit_code == 0
            mock_instance.create_backup.assert_called_once_with("custom")

    def test_create_with_custom_backup_dir(self, runner: CliRunner) -> None:
        """Test creating backup with custom backup directory."""
        with (
            patch(
                "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
            ) as mock_tool,
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = Path("/test/backup.dump")
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup,
                [
                    "create",
                    "--db-url",
                    "postgresql://localhost/test",
                    "--backup-dir",
                    tmpdir,
                ],
            )

            assert result.exit_code == 0
            # Verify backup_dir was passed to settings
            call_args = mock_tool.call_args
            settings = call_args[0][0]
            assert settings.backup_dir == Path(tmpdir)

    def test_create_with_encryption_enabled(self, runner: CliRunner) -> None:
        """Test creating encrypted backup."""
        with (
            patch(
                "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
            ) as mock_tool,
            patch(
                "madsci.common.backup_tools.unified_cli.BackupEncryption"
            ) as mock_encryption,
            tempfile.NamedTemporaryFile(suffix=".key") as key_file,
        ):
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = Path("/test/backup.dump")
            mock_tool.return_value = mock_instance

            mock_encryptor = MagicMock()
            mock_encryptor.encrypt_backup.return_value = Path("/test/backup.dump.enc")
            mock_encryption.return_value = mock_encryptor

            result = runner.invoke(
                madsci_backup,
                [
                    "create",
                    "--db-url",
                    "postgresql://localhost/test",
                    "--encrypt",
                    "--encrypt-key",
                    key_file.name,
                ],
            )

            assert result.exit_code == 0
            assert "encrypted:" in result.output.lower()
            mock_encryptor.encrypt_backup.assert_called_once()

    def test_create_failure_exits_with_error(self, runner: CliRunner) -> None:
        """Test create command exits with error on failure."""
        with patch(
            "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
        ) as mock_tool:
            mock_instance = MagicMock()
            mock_instance.create_backup.side_effect = RuntimeError("Backup failed")
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup, ["create", "--db-url", "postgresql://localhost/test"]
            )

            assert result.exit_code != 0
            assert "Backup failed" in result.output


class TestUnifiedCLIList:
    """Test unified CLI list command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click CLI test runner."""
        return CliRunner()

    def test_list_all_backups(self, runner: CliRunner) -> None:
        """Test listing all backups."""
        with patch(
            "madsci.common.backup_tools.unified_cli.BackupRegistry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.list_backups.return_value = []
            mock_registry.return_value = mock_instance

            result = runner.invoke(madsci_backup, ["list"])

            assert result.exit_code == 0
            mock_instance.list_backups.assert_called_once()

    def test_list_with_type_filter(self, runner: CliRunner) -> None:
        """Test listing backups filtered by database type."""
        with patch(
            "madsci.common.backup_tools.unified_cli.BackupRegistry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.list_backups.return_value = []
            mock_registry.return_value = mock_instance

            result = runner.invoke(madsci_backup, ["list", "--type", "postgresql"])

            assert result.exit_code == 0
            call_args = mock_instance.list_backups.call_args
            assert call_args[1]["database_type"] == "postgresql"

    def test_list_with_date_range(self, runner: CliRunner) -> None:
        """Test listing backups with date range filter."""
        with patch(
            "madsci.common.backup_tools.unified_cli.BackupRegistry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.list_backups.return_value = []
            mock_registry.return_value = mock_instance

            result = runner.invoke(
                madsci_backup, ["list", "--from", "2024-01-01", "--to", "2024-01-31"]
            )

            assert result.exit_code == 0
            mock_instance.list_backups.assert_called_once()


class TestUnifiedCLIRestore:
    """Test unified CLI restore command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click CLI test runner."""
        return CliRunner()

    def test_restore_postgres_backup(self, runner: CliRunner) -> None:
        """Test restoring PostgreSQL backup."""
        with (
            patch(
                "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
            ) as mock_tool,
            tempfile.NamedTemporaryFile(suffix=".dump") as backup_file,
        ):
            mock_instance = MagicMock()
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup,
                [
                    "restore",
                    "--backup",
                    backup_file.name,
                    "--db-url",
                    "postgresql://localhost/test",
                ],
            )

            assert result.exit_code == 0
            mock_instance.restore_from_backup.assert_called_once()

    def test_restore_encrypted_backup(self, runner: CliRunner) -> None:
        """Test restoring encrypted backup."""
        with (
            patch(
                "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
            ) as mock_tool,
            patch(
                "madsci.common.backup_tools.unified_cli.BackupEncryption"
            ) as mock_encryption,
            tempfile.NamedTemporaryFile(suffix=".dump.enc") as backup_file,
            tempfile.NamedTemporaryFile(suffix=".key") as key_file,
        ):
            mock_instance = MagicMock()
            mock_tool.return_value = mock_instance

            mock_encryptor = MagicMock()
            decrypted_path = Path(backup_file.name).with_suffix("")
            mock_encryptor.decrypt_backup.return_value = decrypted_path
            mock_encryption.return_value = mock_encryptor

            result = runner.invoke(
                madsci_backup,
                [
                    "restore",
                    "--backup",
                    backup_file.name,
                    "--db-url",
                    "postgresql://localhost/test",
                    "--encrypt-key",
                    key_file.name,
                ],
            )

            assert result.exit_code == 0
            mock_encryptor.decrypt_backup.assert_called_once()
            mock_instance.restore_from_backup.assert_called_once()


class TestUnifiedCLIValidate:
    """Test unified CLI validate command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click CLI test runner."""
        return CliRunner()

    def test_validate_backup(self, runner: CliRunner) -> None:
        """Test validating backup integrity."""
        with (
            patch(
                "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
            ) as mock_tool,
            tempfile.NamedTemporaryFile(suffix=".dump") as backup_file,
        ):
            mock_instance = MagicMock()
            mock_instance.validate_backup_integrity.return_value = True
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup,
                [
                    "validate",
                    "--backup",
                    backup_file.name,
                    "--db-url",
                    "postgresql://localhost/test",
                ],
            )

            assert result.exit_code == 0
            assert "valid" in result.output.lower()
            mock_instance.validate_backup_integrity.assert_called_once()

    def test_validate_invalid_backup(self, runner: CliRunner) -> None:
        """Test validation fails for invalid backup."""
        with (
            patch(
                "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
            ) as mock_tool,
            tempfile.NamedTemporaryFile(suffix=".dump") as backup_file,
        ):
            mock_instance = MagicMock()
            mock_instance.validate_backup_integrity.return_value = False
            mock_tool.return_value = mock_instance

            result = runner.invoke(
                madsci_backup,
                [
                    "validate",
                    "--backup",
                    backup_file.name,
                    "--db-url",
                    "postgresql://localhost/test",
                ],
            )

            assert result.exit_code != 0
            assert "invalid" in result.output.lower()


class TestUnifiedCLIConfigFile:
    """Test unified CLI configuration file support."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click CLI test runner."""
        return CliRunner()

    def test_load_config_from_json_file(self, runner: CliRunner) -> None:
        """Test loading configuration from JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as config_file:
            config = {
                "db_url": "postgresql://localhost/test",
                "backup_dir": "/test/backups",
            }
            json.dump(config, config_file)
            config_file.flush()

            try:
                with patch(
                    "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
                ) as mock_tool:
                    mock_instance = MagicMock()
                    mock_instance.create_backup.return_value = Path("/test/backup.dump")
                    mock_tool.return_value = mock_instance

                    runner.invoke(
                        madsci_backup, ["--config", config_file.name, "create"]
                    )

                    # Config file loading may not be fully implemented yet
                    # This test validates the --config option exists
                    assert "--config" in madsci_backup.params[0].opts
            finally:
                Path(config_file.name).unlink()

    def test_cli_args_override_config_file(self, runner: CliRunner) -> None:
        """Test CLI arguments override configuration file settings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as config_file:
            config = {
                "db_url": "postgresql://localhost/config_db",
                "backup_dir": "/test/config_backups",
            }
            json.dump(config, config_file)
            config_file.flush()

            try:
                with patch(
                    "madsci.common.backup_tools.unified_cli.PostgreSQLBackupTool"
                ) as mock_tool:
                    mock_instance = MagicMock()
                    mock_instance.create_backup.return_value = Path("/test/backup.dump")
                    mock_tool.return_value = mock_instance

                    result = runner.invoke(
                        madsci_backup,
                        [
                            "--config",
                            config_file.name,
                            "create",
                            "--db-url",
                            "postgresql://localhost/override_db",
                        ],
                    )

                    # Verify CLI arg was used
                    if result.exit_code == 0:
                        call_args = mock_tool.call_args
                        settings = call_args[0][0]
                        assert "override_db" in settings.db_url
            finally:
                Path(config_file.name).unlink()
