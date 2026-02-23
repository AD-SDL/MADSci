"""Tests for the madsci completion command."""

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestCompletionCommand:
    """Tests for the completion command."""

    def test_completion_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["completion", "--help"])
        assert result.exit_code == 0
        assert "Generate shell completion script" in result.output

    def test_completion_requires_shell(self) -> None:
        """Test that a shell argument is required."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["completion"])
        assert result.exit_code != 0

    def test_completion_invalid_shell(self) -> None:
        """Test error for unsupported shell."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["completion", "powershell"])
        assert result.exit_code != 0

    def test_completion_bash(self) -> None:
        """Test bash completion script generation."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["completion", "bash"])
        assert result.exit_code == 0
        assert "_madsci_completion" in result.output
        assert "_MADSCI_COMPLETE" in result.output

    def test_completion_zsh(self) -> None:
        """Test zsh completion script generation."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "compdef" in result.output
        assert "madsci" in result.output

    def test_completion_fish(self) -> None:
        """Test fish completion script generation."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["completion", "fish"])
        assert result.exit_code == 0
        assert "complete" in result.output
        assert "madsci" in result.output
