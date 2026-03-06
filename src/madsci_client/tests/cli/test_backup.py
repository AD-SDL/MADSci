"""Tests for the madsci backup command."""

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestBackupCommand:
    """Tests for the backup command."""

    def test_backup_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "--help"])
        assert result.exit_code == 0
        assert "Database backup management" in result.output

    def test_backup_create_help(self) -> None:
        """Test backup create --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "create", "--help"])
        assert result.exit_code == 0
        assert "Create a new database backup" in result.output

    def test_backup_restore_help(self) -> None:
        """Test backup restore --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "restore", "--help"])
        assert result.exit_code == 0

    def test_backup_validate_help(self) -> None:
        """Test backup validate --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "validate", "--help"])
        assert result.exit_code == 0

    def test_backup_create_requires_db_url(self) -> None:
        """Test that create requires --db-url."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "create"])
        assert result.exit_code != 0

    def test_backup_restore_requires_args(self) -> None:
        """Test that restore requires both --backup and --db-url."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "restore"])
        assert result.exit_code != 0

    def test_backup_subcommands_listed(self) -> None:
        """Test that all subcommands are listed in help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["backup", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "restore" in result.output
        assert "validate" in result.output
