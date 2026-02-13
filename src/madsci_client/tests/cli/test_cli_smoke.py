"""Smoke tests for all CLI commands.

Runs ``--help`` for every registered command to catch import errors
and broken lazy loading without needing running services.
"""

import pytest
from click.testing import CliRunner
from madsci.client.cli import _LAZY_COMMANDS, madsci

ALL_COMMANDS = sorted(_LAZY_COMMANDS.keys())


@pytest.mark.parametrize("cmd", ALL_COMMANDS)
def test_command_help(cmd: str) -> None:
    """Every CLI command should load and print help without errors."""
    runner = CliRunner()
    result = runner.invoke(madsci, [cmd, "--help"])
    assert result.exit_code == 0, (
        f"'{cmd} --help' failed (exit {result.exit_code}):\n{result.output}"
    )
