"""Tests for the madsci add command."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.client.cli.commands.add import (
    _detect_conflicts,
    _execute_backups,
    detect_module_description,
    detect_module_name,
)
from madsci.common.types.template_types import GeneratedProject


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

    def test_detect_strips_only_first_matching_suffix(self, tmp_path: Path) -> None:
        """Should only strip the first matching suffix, not chain-strip."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my_module_node"\n')

        name = detect_module_name(tmp_path)
        assert name == "my_module"


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


class TestDetectConflicts:
    """Tests for the _detect_conflicts function."""

    @staticmethod
    def _make_dry_result(tmp_path: Path, filenames: list[str]) -> GeneratedProject:
        """Create a GeneratedProject with the given filenames."""
        return GeneratedProject(
            template_name="test",
            template_version="1.0.0",
            output_directory=tmp_path,
            files_created=[tmp_path / f for f in filenames],
        )

    def test_no_conflicts_when_files_dont_exist(self, tmp_path: Path) -> None:
        """Non-existing files produce no conflicts."""
        dry_result = self._make_dry_result(tmp_path, ["new_file.txt"])
        skipped, will_backup, will_overwrite = _detect_conflicts(dry_result, "skip")
        assert skipped == []
        assert will_backup == []
        assert will_overwrite == []

    def test_skip_conflict(self, tmp_path: Path) -> None:
        """Existing files are added to skipped when on_conflict='skip'."""
        existing = tmp_path / "existing.txt"
        existing.write_text("content")
        dry_result = self._make_dry_result(tmp_path, ["existing.txt", "new.txt"])

        skipped, will_backup, will_overwrite = _detect_conflicts(dry_result, "skip")
        assert skipped == [existing]
        assert will_backup == []
        assert will_overwrite == []

    def test_backup_conflict(self, tmp_path: Path) -> None:
        """Existing files get backup paths when on_conflict='backup'."""
        existing = tmp_path / "existing.txt"
        existing.write_text("content")
        dry_result = self._make_dry_result(tmp_path, ["existing.txt"])

        skipped, will_backup, will_overwrite = _detect_conflicts(dry_result, "backup")
        assert skipped == []
        assert len(will_backup) == 1
        assert will_backup[0][0] == existing
        assert will_backup[0][1] == existing.with_suffix(".txt.bak")
        assert will_overwrite == []

    def test_overwrite_conflict(self, tmp_path: Path) -> None:
        """Existing files are listed as overwrite targets when on_conflict='overwrite'."""
        existing = tmp_path / "existing.txt"
        existing.write_text("content")
        dry_result = self._make_dry_result(tmp_path, ["existing.txt"])

        skipped, will_backup, will_overwrite = _detect_conflicts(
            dry_result, "overwrite"
        )
        assert skipped == []
        assert will_backup == []
        assert will_overwrite == [existing]


class TestExecuteBackups:
    """Tests for the _execute_backups function."""

    def test_creates_backup_copies(self, tmp_path: Path) -> None:
        """Backup files are created with original content preserved."""
        original = tmp_path / "file.txt"
        original.write_text("original content")
        backup = tmp_path / "file.txt.bak"

        _execute_backups([(original, backup)])
        assert backup.exists()
        assert backup.read_text() == "original content"

    def test_creates_multiple_backups(self, tmp_path: Path) -> None:
        """Multiple backups are created correctly."""
        file_a = tmp_path / "a.txt"
        file_a.write_text("content a")
        file_b = tmp_path / "b.txt"
        file_b.write_text("content b")

        _execute_backups(
            [
                (file_a, tmp_path / "a.txt.bak"),
                (file_b, tmp_path / "b.txt.bak"),
            ]
        )
        assert (tmp_path / "a.txt.bak").read_text() == "content a"
        assert (tmp_path / "b.txt.bak").read_text() == "content b"


class TestRenderAddonEndToEnd:
    """End-to-end tests for addon rendering via CLI."""

    def test_addon_gitignore_renders(self, tmp_path: Path) -> None:
        """The gitignore addon should create a .gitignore file."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test_device_module"\n')

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["add", "--dir", str(tmp_path), "--no-interactive", "gitignore"],
        )

        assert result.exit_code == 0, result.output
        assert (tmp_path / ".gitignore").exists()
        assert "Added" in result.output
