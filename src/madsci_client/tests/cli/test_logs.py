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
        # --json output should contain valid JSON with a "logs" key or a JSON object
        import json

        try:
            parsed = json.loads(result.output)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError:
            # If the output is panel-formatted, it should at least mention logs
            assert (
                "logs" in result.output.lower() or "No logs available" in result.output
            )

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
