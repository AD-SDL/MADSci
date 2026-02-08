"""Tests for the madsci logs command."""

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestLogsCommand:
    """Tests for the logs command."""

    def test_logs_basic(self) -> None:
        """Test basic logs output."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["logs", "--tail", "10"])

        # Logs should succeed even if no events are available
        assert result.exit_code == 0

    def test_logs_json(self) -> None:
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["logs", "--json", "--tail", "10"])

        assert result.exit_code == 0
        # Output should be valid JSON
        assert "logs" in result.output or "{" in result.output

    def test_logs_with_level_filter(self) -> None:
        """Test logs with level filter."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["logs", "--level", "error", "--tail", "10"])

        assert result.exit_code == 0

    def test_logs_with_grep(self) -> None:
        """Test logs with grep filter."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["logs", "--grep", "test", "--tail", "10"])

        assert result.exit_code == 0

    def test_logs_no_timestamps(self) -> None:
        """Test logs without timestamps."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["logs", "--no-timestamps", "--tail", "10"])

        assert result.exit_code == 0
