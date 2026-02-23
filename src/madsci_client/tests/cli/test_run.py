"""Tests for the madsci run command."""

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestRunCommand:
    """Tests for the run command."""

    def test_run_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "--help"])
        assert result.exit_code == 0
        assert "Run workflows or experiments" in result.output

    def test_run_workflow_help(self) -> None:
        """Test run workflow --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "workflow", "--help"])
        assert result.exit_code == 0
        assert "Submit a workflow" in result.output

    def test_run_experiment_help(self) -> None:
        """Test run experiment --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "experiment", "--help"])
        assert result.exit_code == 0
        assert "Run an experiment script" in result.output

    def test_run_workflow_missing_path(self) -> None:
        """Test error when workflow path is missing."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "workflow"])
        assert result.exit_code != 0

    def test_run_experiment_missing_path(self) -> None:
        """Test error when experiment path is missing."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "experiment"])
        assert result.exit_code != 0

    def test_run_workflow_nonexistent_file(self) -> None:
        """Test error when workflow file doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "workflow", "/nonexistent/path.yaml"])
        assert result.exit_code != 0

    def test_run_experiment_nonexistent_file(self) -> None:
        """Test error when experiment file doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "experiment", "/nonexistent/path.py"])
        assert result.exit_code != 0

    def test_run_workflow_no_wait_flag(self) -> None:
        """Test that --no-wait flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["run", "workflow", "--no-wait", "--help"])
        assert result.exit_code == 0

    def test_run_workflow_workcell_option(self) -> None:
        """Test that --workcell option is recognized."""
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["run", "workflow", "--workcell", "http://localhost:8005/", "--help"],
        )
        assert result.exit_code == 0
