"""Automated Tests for the MADSci cli's lab commands."""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner
from madsci.client.cli import root_cli
from madsci.common.types.lab_types import LabDefinition


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for creating a CliRunner instance."""
    return CliRunner()


@pytest.fixture
def temp_lab_file(tmp_path: Path) -> Path:
    """Fixture for creating a temporary lab definition file."""
    lab_file = tmp_path / "test_lab.lab.yaml"
    lab_definition = LabDefinition(
        name="test_lab",
        description="A test lab",
    )
    lab_definition.to_yaml(lab_file)
    return lab_file


def test_lab_create(runner: CliRunner, tmp_path: Path) -> None:
    """Test creating a new lab definition."""
    result = runner.invoke(
        root_cli,
        [
            "lab",
            "create",
            "--name",
            "test_lab",
            "--description",
            "A test lab",
            "--path",
            str(tmp_path / "test_lab.lab.yaml"),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "test_lab.lab.yaml").exists()


def test_lab_list(runner: CliRunner, temp_lab_file: Path) -> None:
    """Test listing all lab definitions."""
    os.chdir(temp_lab_file.parent)
    result = runner.invoke(root_cli, ["lab", "list"])
    assert result.exit_code == 0
    assert "test_lab" in result.output


def test_lab_info(runner: CliRunner, temp_lab_file: Path) -> None:
    """Test getting information about a specific lab definition."""
    os.chdir(temp_lab_file.parent)
    result = runner.invoke(root_cli, ["lab", "--path", str(temp_lab_file), "info"])
    assert result.exit_code == 0
    assert "test_lab" in result.output


def test_lab_delete(runner: CliRunner, temp_lab_file: Path) -> None:
    """Test deleting a lab definition."""
    os.chdir(temp_lab_file.parent)
    result = runner.invoke(
        root_cli, ["lab", "--path", str(temp_lab_file), "delete", "--yes"]
    )
    assert result.exit_code == 0
    assert not temp_lab_file.exists()


def test_lab_validate(runner: CliRunner, temp_lab_file: Path) -> None:
    """Test validating a lab definition file."""
    os.chdir(temp_lab_file.parent)
    result = runner.invoke(root_cli, ["lab", "--path", str(temp_lab_file), "validate"])
    assert result.exit_code == 0
    assert "test_lab" in result.output


def test_lab_commands(runner: CliRunner, temp_lab_file: Path) -> None:
    """Test adding a command to a lab definition."""
    os.chdir(temp_lab_file.parent)
    # * Test creating a new command
    result = runner.invoke(
        root_cli,
        [
            "lab",
            "--path",
            str(temp_lab_file),
            "add-command",
            "--name",
            "test_command",
            "--command",
            'echo "Hello, World!"',
        ],
    )
    assert result.exit_code == 0
    # * Test deleting the command
    result = runner.invoke(
        root_cli,
        [
            "lab",
            "--path",
            str(temp_lab_file),
            "delete-command",
            "test_command",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "Deleted command" in result.output
