"""Tests for the madsci stop command."""

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestStopCommand:
    """Tests for the stop command."""

    def test_stop_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["stop", "--help"])
        assert result.exit_code == 0
        assert "Stop MADSci lab services" in result.output

    def test_stop_remove_flag(self) -> None:
        """Test --remove flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["stop", "--remove", "--help"])
        assert result.exit_code == 0

    def test_stop_volumes_flag(self) -> None:
        """Test --volumes flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["stop", "--volumes", "--help"])
        assert result.exit_code == 0

    def test_stop_no_compose_file(self, tmp_path, monkeypatch) -> None:
        """Test friendly error when no compose file exists."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(madsci, ["stop"])
        assert result.exit_code != 0
        assert "No Docker Compose file found" in result.output

    def test_stop_volumes_confirmation_abort(self, tmp_path) -> None:
        """Test --volumes asks for confirmation and can be aborted."""
        compose_file = tmp_path / "compose.yaml"
        compose_file.write_text("services: {}")

        runner = CliRunner()
        # Answer 'n' to the confirmation prompt
        result = runner.invoke(
            madsci,
            ["stop", "--volumes", "--config", str(compose_file)],
            input="n\n",
        )
        assert "Aborted" in result.output
