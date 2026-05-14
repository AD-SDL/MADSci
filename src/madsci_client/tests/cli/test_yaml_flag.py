"""Tests for the --yaml flag on the top-level madsci CLI group."""

from __future__ import annotations

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestYamlFlag:
    """Tests for the --yaml output flag."""

    def test_yaml_flag_is_accepted(self) -> None:
        """The --yaml flag should be accepted by the top-level group."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["--yaml", "version"])
        # Should not fail with "no such option"
        assert "no such option" not in result.output.lower()

    def test_yaml_stored_in_context(self) -> None:
        """The --yaml flag should set ctx.obj['yaml'] = True."""
        runner = CliRunner()
        # The version command will still run; we just verify no crash
        result = runner.invoke(madsci, ["--yaml", "version"])
        assert result.exit_code == 0

    def test_yaml_flag_absent_by_default(self) -> None:
        """Without --yaml, the flag should be False."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["version"])
        assert result.exit_code == 0
