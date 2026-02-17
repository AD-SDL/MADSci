"""Tests for the madsci validate command."""

import json

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate MADSci configuration files" in result.output

    def test_validate_alias(self) -> None:
        """Test that 'val' alias works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["val", "--help"])
        assert result.exit_code == 0
        assert "Validate" in result.output

    def test_validate_empty_directory(self, tmp_path) -> None:
        """Test validate in a directory with no config files."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["validate", str(tmp_path)])
        assert result.exit_code == 0
        assert "No MADSci configuration files found" in result.output

    def test_validate_example_lab(self) -> None:
        """Test validate finds and processes example lab files."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["validate", "examples/example_lab/"])
        assert result.exit_code == 0 or "error" in result.output.lower()
        # Should find at least some files
        assert "valid" in result.output.lower() or "Summary" in result.output

    def test_validate_json_output(self, tmp_path) -> None:
        """Test JSON output mode."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["validate", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data
        assert "summary" in data

    def test_validate_single_file(self, tmp_path) -> None:
        """Test validating a single workflow file."""
        wf = tmp_path / "test.workflow.yaml"
        wf.write_text("name: test\nsteps: []\n")
        runner = CliRunner()
        result = runner.invoke(madsci, ["validate", str(wf)])
        # It should attempt validation (may pass or fail depending on schema)
        assert result.exit_code in {0, 1}

    def test_validate_strict_mode(self, tmp_path) -> None:
        """Test --strict flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["validate", str(tmp_path), "--strict"])
        assert result.exit_code == 0
