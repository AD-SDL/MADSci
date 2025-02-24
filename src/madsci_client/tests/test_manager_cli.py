"""Automated Tests for the MADSci cli's manager commands."""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner
from madsci.client.cli import root_cli
from madsci.common.types.lab_types import ManagerDefinition, ManagerType


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for creating a CliRunner instance."""
    return CliRunner()


@pytest.fixture
def temp_manager_file(tmp_path: Path) -> Path:
    """Fixture for creating a temporary manager definition file."""
    manager_file = tmp_path / "test_manager.manager.yaml"
    manager_definition = ManagerDefinition(
        name="test_manager",
        description="A test manager",
        manager_type=ManagerType.EVENT_MANAGER,
    )
    manager_definition.to_yaml(manager_file)
    return manager_file


def test_manager_add(runner: CliRunner, tmp_path: Path) -> None:
    """Test adding a new manager definition."""
    result = runner.invoke(
        root_cli,
        [
            "manager",
            "add",
            "--name",
            "test_manager",
            "--description",
            "A test manager",
            "--manager_type",
            "event_manager",
            "--path",
            str(tmp_path / "test_manager.manager.yaml"),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "test_manager.manager.yaml").exists()


def test_manager_list(runner: CliRunner, temp_manager_file: Path) -> None:
    """Test listing all manager definitions."""
    os.chdir(temp_manager_file.parent)
    result = runner.invoke(root_cli, ["manager", "list"])
    assert result.exit_code == 0
    assert "test_manager" in result.output


def test_manager_info(runner: CliRunner, temp_manager_file: Path) -> None:
    """Test getting information about a specific manager definition."""
    os.chdir(temp_manager_file.parent)
    result = runner.invoke(
        root_cli, ["manager", "--path", str(temp_manager_file), "info"]
    )
    assert result.exit_code == 0
    assert "test_manager" in result.output


def test_manager_delete(runner: CliRunner, temp_manager_file: Path) -> None:
    """Test deleting a manager definition."""
    os.chdir(temp_manager_file.parent)
    result = runner.invoke(
        root_cli, ["manager", "--path", str(temp_manager_file), "delete", "--yes"]
    )
    assert result.exit_code == 0
    assert not temp_manager_file.exists()


def test_manager_validate(runner: CliRunner, temp_manager_file: Path) -> None:
    """Test validating a manager definition file."""
    os.chdir(temp_manager_file.parent)
    result = runner.invoke(
        root_cli, ["manager", "--path", str(temp_manager_file), "validate"]
    )
    assert result.exit_code == 0
    assert "test_manager" in result.output
