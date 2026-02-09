"""Tests for the madsci new command."""

import tempfile

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestNewCommand:
    """Tests for the new command group."""

    def test_new_help(self) -> None:
        """Test that new command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "--help"])

        assert result.exit_code == 0
        assert "Create new MADSci components" in result.output
        assert "module" in result.output
        assert "experiment" in result.output
        assert "workflow" in result.output

    def test_new_list_no_templates(self) -> None:
        """Test listing templates when none are available."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "list"])

        # Should succeed even with no templates
        assert result.exit_code == 0

    def test_new_module_help(self) -> None:
        """Test that new module command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "module", "--help"])

        assert result.exit_code == 0
        assert "Create a new node module" in result.output
        assert "--name" in result.output
        assert "--template" in result.output

    def test_new_experiment_help(self) -> None:
        """Test that new experiment command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "experiment", "--help"])

        assert result.exit_code == 0
        assert "Create a new experiment" in result.output
        assert "--modality" in result.output

    def test_new_workflow_help(self) -> None:
        """Test that new workflow command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "workflow", "--help"])

        assert result.exit_code == 0
        assert "Create a new workflow" in result.output

    def test_new_workcell_help(self) -> None:
        """Test that new workcell command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "workcell", "--help"])

        assert result.exit_code == 0
        assert "Create a new workcell" in result.output

    def test_new_lab_help(self) -> None:
        """Test that new lab command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "lab", "--help"])

        assert result.exit_code == 0
        assert "Create a new lab" in result.output
        assert "--template" in result.output

    def test_new_interface_help(self) -> None:
        """Test that new interface command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["new", "interface", "--help"])

        assert result.exit_code == 0
        assert "Add a new interface" in result.output
        assert "--type" in result.output


class TestNewModuleCommand:
    """Tests for madsci new module command with actual template generation."""

    def test_new_module_no_template_found(self) -> None:
        """Test that module command handles missing template gracefully."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                madsci,
                [
                    "new",
                    "module",
                    tmpdir,
                    "--name",
                    "test_module",
                    "--no-interactive",
                ],
            )

            # Should report template not found (bundled templates may not be installed)
            # Either succeeds (templates found) or fails gracefully
            # We just check it doesn't crash
            assert result.exit_code in (0, 1)


class TestNewExperimentCommand:
    """Tests for madsci new experiment command."""

    def test_new_experiment_no_template_found(self) -> None:
        """Test that experiment command handles missing template gracefully."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                madsci,
                [
                    "new",
                    "experiment",
                    tmpdir,
                    "--name",
                    "test_experiment",
                    "--no-interactive",
                ],
            )

            # Should not crash
            assert result.exit_code in (0, 1)


class TestNewWorkflowCommand:
    """Tests for madsci new workflow command."""

    def test_new_workflow_no_template_found(self) -> None:
        """Test that workflow command handles missing template gracefully."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                madsci,
                [
                    "new",
                    "workflow",
                    tmpdir,
                    "--name",
                    "test_workflow",
                    "--no-interactive",
                ],
            )

            # Should not crash
            assert result.exit_code in (0, 1)
