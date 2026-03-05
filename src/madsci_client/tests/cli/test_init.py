"""Tests for the madsci init command."""

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestInitCommand:
    """Tests for the init command."""

    def test_init_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize a new MADSci lab" in result.output

    def test_init_no_interactive(self, tmp_path) -> None:
        """Test non-interactive init with defaults."""
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["init", str(tmp_path), "--no-interactive"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "Next steps" in result.output
        # Verify the lab directory was created
        assert (tmp_path / "my_lab").exists()

    def test_init_with_name(self, tmp_path) -> None:
        """Test init with a custom lab name."""
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["init", str(tmp_path), "--name", "test_lab", "--no-interactive"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "test_lab" in result.output
        assert (tmp_path / "test_lab").exists()

    def test_init_interactive(self, tmp_path) -> None:
        """Test interactive init responds to prompts."""
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["init", str(tmp_path)],
            input="my_cool_lab\nA cool lab\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert (tmp_path / "my_cool_lab").exists()

    def test_init_template_option(self) -> None:
        """Test --template option is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["init", "--template", "minimal", "--help"])
        assert result.exit_code == 0
