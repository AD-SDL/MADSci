"""Tests for the madsci stop command."""

import signal
from unittest.mock import patch

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

    def test_stop_manager_help(self) -> None:
        """Test stop manager subcommand help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["stop", "manager", "--help"])
        assert result.exit_code == 0
        assert "Stop a background manager" in result.output

    def test_stop_node_help(self) -> None:
        """Test stop node subcommand help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["stop", "node", "--help"])
        assert result.exit_code == 0
        assert "Stop a background node" in result.output

    def test_stop_manager_not_running(self) -> None:
        """Test error when trying to stop a manager that isn't running."""
        runner = CliRunner()
        with patch(
            "madsci.client.cli.commands.start._read_pid",
            return_value=None,
        ):
            result = runner.invoke(madsci, ["stop", "manager", "event"])
        assert result.exit_code != 0
        assert "No running manager" in result.output

    def test_stop_node_not_running(self) -> None:
        """Test error when trying to stop a node that isn't running."""
        runner = CliRunner()
        with patch(
            "madsci.client.cli.commands.start._read_pid",
            return_value=None,
        ):
            result = runner.invoke(madsci, ["stop", "node", "my_node"])
        assert result.exit_code != 0
        assert "No running node" in result.output

    def test_stop_manager_sends_sigterm(self) -> None:
        """Test that stop manager sends SIGTERM, waits, and removes PID file."""
        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start._read_pid",
                return_value=12345,
            ),
            patch("madsci.client.cli.commands.stop.os.kill") as mock_kill,
            patch(
                "madsci.client.cli.commands.stop._wait_for_exit",
                return_value=True,
            ),
            patch("madsci.client.cli.commands.start._remove_pid") as mock_remove,
        ):
            result = runner.invoke(madsci, ["stop", "manager", "event"])
            assert result.exit_code == 0
            assert "Stopped event manager" in result.output
            mock_kill.assert_called_once_with(12345, signal.SIGTERM)
            mock_remove.assert_called_once_with("manager-event")

    def test_stop_manager_escalates_to_sigkill(self) -> None:
        """Test that stop manager sends SIGKILL when process doesn't exit."""
        runner = CliRunner()
        with (
            patch(
                "madsci.client.cli.commands.start._read_pid",
                return_value=12345,
            ),
            patch("madsci.client.cli.commands.stop.os.kill") as mock_kill,
            patch(
                "madsci.client.cli.commands.stop._wait_for_exit",
                return_value=False,
            ),
            patch("madsci.client.cli.commands.start._remove_pid") as mock_remove,
        ):
            result = runner.invoke(madsci, ["stop", "manager", "event"])
            assert result.exit_code == 0
            assert "SIGKILL" in result.output
            # Should have been called twice: SIGTERM then SIGKILL
            assert mock_kill.call_count == 2
            mock_kill.assert_any_call(12345, signal.SIGTERM)
            mock_kill.assert_any_call(12345, signal.SIGKILL)
            mock_remove.assert_called_once_with("manager-event")
