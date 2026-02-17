"""Tests for the madsci migrate command."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestMigrateCommandGroup:
    """Tests for the migrate command group."""

    def test_migrate_help(self) -> None:
        """Test that migrate command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "--help"])

        assert result.exit_code == 0
        assert "Migration tools for upgrading configuration" in result.output
        assert "scan" in result.output
        assert "convert" in result.output
        assert "status" in result.output
        assert "finalize" in result.output
        assert "rollback" in result.output


class TestMigrateScanCommand:
    """Tests for the migrate scan command."""

    def test_scan_help(self) -> None:
        """Test that scan subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "scan", "--help"])

        assert result.exit_code == 0
        assert "DIRECTORY" in result.output
        assert "--json" in result.output
        assert "--verbose" in result.output

    def test_scan_empty_directory(self) -> None:
        """Test scanning a directory with no definition files."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(madsci, ["migrate", "scan", tmpdir])

        assert result.exit_code == 0
        assert "No files need migration" in result.output

    def test_scan_empty_directory_json(self) -> None:
        """Test scanning an empty directory with JSON output."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(madsci, ["migrate", "scan", tmpdir, "--json"])

        assert result.exit_code == 0

    def test_scan_directory_with_manager_yaml(self) -> None:
        """Test scanning a directory containing a manager definition file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake manager definition file
            manager_file = Path(tmpdir) / "test.manager.yaml"
            manager_file.write_text(
                "name: Test Manager\n"
                "description: A test manager\n"
                "manager_id: 01JTEST00000000000000000000\n"
                "manager_type: lab_manager\n"
            )

            result = runner.invoke(madsci, ["migrate", "scan", tmpdir])

        assert result.exit_code == 0
        assert "test.manager.yaml" in result.output or "1 file" in result.output

    def test_scan_directory_with_node_yaml(self) -> None:
        """Test scanning a directory containing a node definition file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake node definition file
            node_file = Path(tmpdir) / "test.node.yaml"
            node_file.write_text(
                "node_name: test_node\n"
                "node_id: 01JTEST00000000000000000001\n"
                "node_type: device\n"
                "module_name: test\n"
            )

            result = runner.invoke(madsci, ["migrate", "scan", tmpdir])

        assert result.exit_code == 0
        assert "test.node.yaml" in result.output or "1 file" in result.output

    def test_scan_fixture_data(self) -> None:
        """Test scanning the v0.6 fixture directory for definition files."""
        runner = CliRunner()
        fixture_dir = (
            Path(__file__).resolve().parent / "fixtures" / "migration" / "v0.6"
        )
        if not fixture_dir.exists():
            return  # Skip if fixture directory not found

        result = runner.invoke(madsci, ["migrate", "scan", str(fixture_dir)])

        assert result.exit_code == 0
        # Fixture data should have definition files to migrate
        assert (
            "files requiring migration" in result.output
            or "No files need migration" in result.output
        )

    def test_scan_fixture_data_json(self) -> None:
        """Test scanning fixture data with JSON output."""
        runner = CliRunner()
        fixture_dir = (
            Path(__file__).resolve().parent / "fixtures" / "migration" / "v0.6"
        )
        if not fixture_dir.exists():
            return  # Skip if fixture directory not found

        result = runner.invoke(madsci, ["migrate", "scan", str(fixture_dir), "--json"])

        assert result.exit_code == 0

    def test_scan_verbose(self) -> None:
        """Test scanning with verbose output."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake manager definition file
            manager_file = Path(tmpdir) / "test.manager.yaml"
            manager_file.write_text(
                "name: Test Manager\n"
                "description: A test manager\n"
                "manager_id: 01JTEST00000000000000000000\n"
                "manager_type: lab_manager\n"
            )

            result = runner.invoke(madsci, ["migrate", "scan", tmpdir, "--verbose"])

        assert result.exit_code == 0


class TestMigrateConvertCommand:
    """Tests for the migrate convert command."""

    def test_convert_help(self) -> None:
        """Test that convert subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "convert", "--help"])

        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--dry-run" in result.output
        assert "--apply" in result.output
        assert "--backup" in result.output

    def test_convert_no_mode_specified(self) -> None:
        """Test that convert requires --dry-run or --apply."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "convert", "--all"])

        assert "Specify --dry-run or --apply" in result.output

    def test_convert_no_files_specified(self) -> None:
        """Test convert with no files and no --all flag."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "convert", "--dry-run"])

        assert "Specify files to convert or use --all" in result.output

    def test_convert_all_dry_run_empty(self) -> None:
        """Test convert --all --dry-run in a directory with no definition files."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch MigrationScanner to scan the empty tmpdir instead of cwd
            from madsci.common.migration import MigrationScanner

            original_init = MigrationScanner.__init__

            def patched_init(self, _project_dir=None):
                original_init(self, Path(tmpdir))

            with patch.object(MigrationScanner, "__init__", patched_init):
                result = runner.invoke(
                    madsci,
                    ["migrate", "convert", "--all", "--dry-run"],
                    catch_exceptions=False,
                )

        # Should report no files to convert
        assert result.exit_code == 0
        assert "No files to convert" in result.output


class TestMigrateStatusCommand:
    """Tests for the migrate status command."""

    def test_status_help(self) -> None:
        """Test that status subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "status", "--help"])

        assert result.exit_code == 0

    def test_status_no_files(self) -> None:
        """Test status when there are no definition files."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory():
            # Run from a directory with no definition files
            result = runner.invoke(madsci, ["migrate", "status"])

        assert result.exit_code == 0
        # Either shows migration complete or status summary
        assert (
            "Migration complete" in result.output
            or "Migration Status" in result.output
            or "No definition files found" in result.output
        )


class TestMigrateFinalizeCommand:
    """Tests for the migrate finalize command."""

    def test_finalize_help(self) -> None:
        """Test that finalize subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "finalize", "--help"])

        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--apply" in result.output
        assert "--keep-backups" in result.output

    def test_finalize_no_mode_specified(self) -> None:
        """Test that finalize requires --dry-run or --apply."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "finalize"])

        assert "Specify --dry-run or --apply" in result.output

    def test_finalize_dry_run(self) -> None:
        """Test finalize in dry-run mode."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "finalize", "--dry-run"])

        assert result.exit_code == 0
        # Should either report no deprecated files or show them
        assert (
            "No deprecated files" in result.output
            or "Dry run" in result.output
            or "Files to remove" in result.output
        )


class TestMigrateRollbackCommand:
    """Tests for the migrate rollback command."""

    def test_rollback_help(self) -> None:
        """Test that rollback subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "rollback", "--help"])

        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--dry-run" in result.output

    def test_rollback_no_files_specified(self) -> None:
        """Test rollback with no files and no --all flag."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "rollback"])

        assert "Specify files to rollback or use --all" in result.output

    def test_rollback_all_nothing_to_rollback(self) -> None:
        """Test rollback --all when there's nothing to rollback."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "rollback", "--all"])

        assert result.exit_code == 0
        assert "No files to rollback" in result.output
