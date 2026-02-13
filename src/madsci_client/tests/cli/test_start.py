"""Tests for the madsci start command."""

from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestStartCommand:
    """Tests for the start command."""

    def test_start_help(self) -> None:
        """Test that --help works."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start MADSci lab services" in result.output

    def test_start_no_docker(self) -> None:
        """Test friendly error when docker is not installed."""
        runner = CliRunner()
        with patch("madsci.client.cli.commands.start.shutil.which", return_value=None):
            result = runner.invoke(madsci, ["start"])
        assert result.exit_code != 0
        assert "Docker is not installed" in result.output

    def test_start_docker_not_running(self) -> None:
        """Test friendly error when docker is installed but not running."""
        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch(
                "madsci.client.cli.commands.start.subprocess.run",
                side_effect=lambda _cmd, **_kw: type(
                    "Result",
                    (),
                    {"returncode": 1, "stdout": "", "stderr": "daemon not running"},
                )(),
            ),
        ):
            result = runner.invoke(madsci, ["start"])
        assert result.exit_code != 0
        assert "not running" in result.output

    def test_start_no_compose_file(self, tmp_path, monkeypatch) -> None:
        """Test friendly error when no compose file exists."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch(
                "madsci.client.cli.commands.start.subprocess.run",
                return_value=type("Result", (), {"returncode": 0})(),
            ),
        ):
            result = runner.invoke(madsci, ["start"])
        assert result.exit_code != 0
        assert "No Docker Compose file found" in result.output

    def test_start_detach_flag(self) -> None:
        """Test that -d flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "-d", "--help"])
        assert result.exit_code == 0

    def test_start_build_flag(self) -> None:
        """Test that --build flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "--build", "--help"])
        assert result.exit_code == 0

    def test_start_services_option(self) -> None:
        """Test that --services is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "--services", "foo", "--help"])
        assert result.exit_code == 0

    def test_start_with_config_path(self, tmp_path) -> None:
        """Test start accepts --config pointing to a compose file."""
        compose_file = tmp_path / "compose.yaml"
        compose_file.write_text("services: {}")

        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch("madsci.client.cli.commands.start.subprocess.run") as mock_run,
        ):
            # First call is _check_docker (docker info), second is docker compose up
            mock_run.return_value = type("Result", (), {"returncode": 0})()

            result = runner.invoke(
                madsci, ["start", "-d", "--config", str(compose_file)]
            )
            assert result.exit_code == 0
            assert "Starting services" in result.output
