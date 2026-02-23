"""Tests for the madsci start command."""

from unittest.mock import MagicMock, patch

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
                madsci, ["start", "-d", "--no-wait", "--config", str(compose_file)]
            )
            assert result.exit_code == 0
            assert "Starting services" in result.output

    def test_start_wait_flag_recognized(self) -> None:
        """Test that --wait/--no-wait flags are recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "--no-wait", "--help"])
        assert result.exit_code == 0

    def test_start_wait_timeout_option(self) -> None:
        """Test that --wait-timeout is recognized."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "--wait-timeout", "30", "--help"])
        assert result.exit_code == 0

    def test_start_detach_triggers_health_poll(self, tmp_path) -> None:
        """Test that -d without --no-wait triggers health polling."""
        compose_file = tmp_path / "compose.yaml"
        compose_file.write_text("services: {}")

        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch("madsci.client.cli.commands.start.subprocess.run") as mock_run,
            patch("madsci.client.cli.commands.start._wait_for_health") as mock_health,
        ):
            mock_run.return_value = type("Result", (), {"returncode": 0})()

            result = runner.invoke(
                madsci, ["start", "-d", "--config", str(compose_file)]
            )
            assert result.exit_code == 0
            mock_health.assert_called_once()

    def test_start_no_wait_skips_health_poll(self, tmp_path) -> None:
        """Test that --no-wait skips health polling."""
        compose_file = tmp_path / "compose.yaml"
        compose_file.write_text("services: {}")

        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch("madsci.client.cli.commands.start.subprocess.run") as mock_run,
            patch("madsci.client.cli.commands.start._wait_for_health") as mock_health,
        ):
            mock_run.return_value = type("Result", (), {"returncode": 0})()

            result = runner.invoke(
                madsci, ["start", "-d", "--no-wait", "--config", str(compose_file)]
            )
            assert result.exit_code == 0
            mock_health.assert_not_called()

    def test_start_manager_help(self) -> None:
        """Test start manager subcommand help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "manager", "--help"])
        assert result.exit_code == 0
        assert "Start a single manager" in result.output

    def test_start_node_help(self) -> None:
        """Test start node subcommand help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "node", "--help"])
        assert result.exit_code == 0
        assert "Start a node module" in result.output

    def test_start_manager_invalid_name(self) -> None:
        """Test start manager with invalid name."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["start", "manager", "nonexistent"])
        assert result.exit_code != 0

    def test_start_manager_already_running(self) -> None:
        """Test error when manager is already running."""
        runner = CliRunner()
        with patch(
            "madsci.client.cli.commands.start._read_pid",
            return_value=12345,
        ):
            result = runner.invoke(madsci, ["start", "manager", "event"])
        assert result.exit_code != 0
        assert "already running" in result.output

    def test_wait_for_health_all_healthy(self) -> None:
        """Test _wait_for_health reports success when all services are healthy."""
        from madsci.client.cli.commands.status import ServiceInfo, ServiceStatus

        mock_console = MagicMock()

        def mock_check(name, url, timeout=5.0):  # noqa: ARG001
            return ServiceInfo(name=name, url=url, status=ServiceStatus.HEALTHY)

        with (
            patch(
                "madsci.client.cli.commands.status.check_service_health",
                side_effect=mock_check,
            ),
            patch("rich.live.Live"),
        ):
            from madsci.client.cli.commands.start import _wait_for_health

            _wait_for_health(mock_console, timeout=5)

        # Should print success message
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("healthy" in c.lower() for c in calls)
