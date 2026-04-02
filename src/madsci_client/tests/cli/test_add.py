"""Tests for the madsci add command."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.client.cli.commands.add import detect_module_description, detect_module_name


class TestAddCommandHelp:
    """Tests for the add command help and subcommand listing."""

    def test_add_help(self) -> None:
        """Test that add --help shows available subcommands."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["add", "--help"])

        assert result.exit_code == 0
        assert "Add components" in result.output

    def test_add_lists_all_subcommands(self) -> None:
        """Test that all subcommands are listed in help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["add", "--help"])

        assert result.exit_code == 0
        for subcmd in [
            "docs",
            "drivers",
            "notebooks",
            "gitignore",
            "compose",
            "dev-tools",
            "agent-config",
            "all",
        ]:
            assert subcmd in result.output, f"Subcommand '{subcmd}' not in help output"

    @pytest.mark.parametrize(
        "subcmd",
        [
            "docs",
            "drivers",
            "notebooks",
            "gitignore",
            "compose",
            "dev-tools",
            "agent-config",
            "all",
        ],
    )
    def test_subcommand_help(self, subcmd: str) -> None:
        """Each subcommand should have working --help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["add", subcmd, "--help"])

        assert result.exit_code == 0


class TestDetectModuleName:
    """Tests for the auto-detection of module name from pyproject.toml."""

    def test_detect_from_pyproject(self, tmp_path: Path) -> None:
        """Should extract module name from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my_robot-module"\n')

        name = detect_module_name(tmp_path)
        assert name == "my_robot"

    def test_detect_strips_underscore_module(self, tmp_path: Path) -> None:
        """Should strip _module suffix."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my_robot_module"\n')

        name = detect_module_name(tmp_path)
        assert name == "my_robot"

    def test_detect_normalizes_hyphens(self, tmp_path: Path) -> None:
        """Should convert hyphens to underscores."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my-cool-device"\n')

        name = detect_module_name(tmp_path)
        assert name == "my_cool_device"

    def test_detect_no_pyproject(self, tmp_path: Path) -> None:
        """Should return None when no pyproject.toml exists."""
        name = detect_module_name(tmp_path)
        assert name is None

    def test_detect_no_project_name(self, tmp_path: Path) -> None:
        """Should return None when pyproject.toml has no project.name."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 100\n")

        name = detect_module_name(tmp_path)
        assert name is None

    def test_detect_simple_name(self, tmp_path: Path) -> None:
        """Should handle name without -module suffix."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "platereader"\n')

        name = detect_module_name(tmp_path)
        assert name == "platereader"

    def test_detect_strips_node_suffix(self, tmp_path: Path) -> None:
        """Should strip -node and _node suffixes."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "platereader-node"\n')

        name = detect_module_name(tmp_path)
        assert name == "platereader"

    def test_detect_strips_underscore_node(self, tmp_path: Path) -> None:
        """Should strip _node suffix."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "platereader_node"\n')

        name = detect_module_name(tmp_path)
        assert name == "platereader"


class TestDetectModuleDescription:
    """Tests for the auto-detection of module description from pyproject.toml."""

    def test_detect_description(self, tmp_path: Path) -> None:
        """Should extract description from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "my_robot"\ndescription = "A robot arm controller"\n'
        )

        desc = detect_module_description(tmp_path)
        assert desc == "A robot arm controller"

    def test_detect_no_description(self, tmp_path: Path) -> None:
        """Should return None when no description field."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my_robot"\n')

        desc = detect_module_description(tmp_path)
        assert desc is None

    def test_detect_no_pyproject(self, tmp_path: Path) -> None:
        """Should return None when no pyproject.toml exists."""
        desc = detect_module_description(tmp_path)
        assert desc is None
