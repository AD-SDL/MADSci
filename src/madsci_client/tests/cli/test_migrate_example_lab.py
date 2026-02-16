"""Integration tests for migration tool against example_lab.

These tests validate that the migration scanner correctly finds all definition
files in the example_lab directory and that convert --dry-run produces
correct output.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.migration import MigrationScanner

# Path to example_lab relative to this test file
EXAMPLE_LAB = Path(__file__).resolve().parents[4] / "example_lab"


@pytest.fixture()
def example_lab_path() -> Path:
    """Get path to example_lab, skip if not found."""
    if not EXAMPLE_LAB.exists():
        pytest.skip("example_lab directory not found")
    return EXAMPLE_LAB


class TestMigrationScannerAgainstExampleLab:
    """Validate that MigrationScanner finds all definition files in example_lab."""

    def test_scanner_finds_all_manager_definitions(
        self, example_lab_path: Path
    ) -> None:
        """Scanner should find all 7 manager definition files."""
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]

        assert len(manager_files) == 7, (
            f"Expected 7 manager definitions, found {len(manager_files)}: "
            f"{[m.source_path.name for m in manager_files]}"
        )

        manager_names = {m.source_path.name for m in manager_files}
        expected_managers = {
            "example_lab.manager.yaml",
            "example_event.manager.yaml",
            "example_experiment.manager.yaml",
            "example_resource.manager.yaml",
            "example_data.manager.yaml",
            "example_workcell.manager.yaml",
            "example_location.manager.yaml",
        }
        assert manager_names == expected_managers

    def test_scanner_finds_all_node_definitions(self, example_lab_path: Path) -> None:
        """Scanner should find all committed node definition files."""
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]
        node_names = {m.source_path.name for m in node_files}

        # These 5 node definitions are committed to the repo
        expected_nodes = {
            "robotarm_1.node.yaml",
            "advanced_example_node.node.yaml",
            "liquidhandler_1.node.yaml",
            "liquidhandler_2.node.yaml",
            "platereader_1.node.yaml",
        }
        assert expected_nodes.issubset(node_names), (
            f"Missing expected node definitions: {expected_nodes - node_names}"
        )
        assert len(node_files) >= 5, (
            f"Expected at least 5 node definitions, found {len(node_files)}: "
            f"{[m.source_path.name for m in node_files]}"
        )

    def test_scanner_total_file_count(self, example_lab_path: Path) -> None:
        """Scanner should find at least 12 definition files (7 manager + 5 node).

        Note: locally-generated or gitignored files may increase the count.
        """
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        assert plan.total_count >= 12, (
            f"Expected at least 12 total definition files, found {plan.total_count}"
        )

    def test_all_files_have_pending_status(self, example_lab_path: Path) -> None:
        """All found files should have PENDING status (not yet migrated)."""
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        assert plan.pending_count == plan.total_count
        assert plan.migrated_count == 0
        assert plan.failed_count == 0

    def test_all_manager_files_have_component_ids(self, example_lab_path: Path) -> None:
        """All manager definition files should have extractable component IDs."""
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]

        for m in manager_files:
            assert m.component_id, f"{m.source_path.name} has no component_id"
            assert m.name, f"{m.source_path.name} has no name"

    def test_all_node_files_have_component_ids(self, example_lab_path: Path) -> None:
        """All node definition files should have extractable component IDs."""
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]

        for m in node_files:
            assert m.component_id, f"{m.source_path.name} has no component_id"
            assert m.name, f"{m.source_path.name} has no name"

    def test_manager_files_have_migration_actions(self, example_lab_path: Path) -> None:
        """All manager files should have planned migration actions."""
        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]

        for m in manager_files:
            assert len(m.actions) > 0, f"{m.source_path.name} has no migration actions"
            action_descriptions = [a.description for a in m.actions]
            # Should have at least a register action and env var generation
            assert any("Register" in d for d in action_descriptions), (
                f"{m.source_path.name} missing 'Register' action"
            )
            assert any("environment variable" in d for d in action_descriptions), (
                f"{m.source_path.name} missing env var generation action"
            )


class TestMigrateScanCLIAgainstExampleLab:
    """Validate the CLI `madsci migrate scan` command against example_lab."""

    def test_scan_cli_finds_files(self, example_lab_path: Path) -> None:
        """CLI scan should find and report migration files."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "scan", str(example_lab_path)])

        assert result.exit_code == 0
        assert "files requiring migration" in result.output

    def test_scan_cli_json_output(self, example_lab_path: Path) -> None:
        """CLI scan JSON output should be parseable and have expected structure."""
        runner = CliRunner()
        result = runner.invoke(
            madsci, ["migrate", "scan", str(example_lab_path), "--json"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "files" in data
        assert len(data["files"]) >= 12

    def test_scan_cli_verbose_shows_details(self, example_lab_path: Path) -> None:
        """CLI scan with --verbose should show names and IDs."""
        runner = CliRunner()
        result = runner.invoke(
            madsci, ["migrate", "scan", str(example_lab_path), "--verbose"]
        )

        assert result.exit_code == 0
        # Verbose output should include component names
        assert "Name:" in result.output
        assert "ID:" in result.output


class TestMigrateConvertDryRunAgainstExampleLab:
    """Validate convert --dry-run against example_lab."""

    def test_convert_dry_run_does_not_modify_files(
        self, example_lab_path: Path
    ) -> None:
        """Convert --dry-run should not modify any files in example_lab."""
        from madsci.common.migration import MigrationConverter

        scanner = MigrationScanner(example_lab_path)
        plan = scanner.scan()

        # Capture original file sizes
        original_sizes = {}
        for m in plan.files:
            if m.source_path.exists():
                original_sizes[m.source_path] = m.source_path.stat().st_size

        converter = MigrationConverter()
        for m in plan.files:
            converter.convert(m, dry_run=True)

        # Verify no files changed
        for path, original_size in original_sizes.items():
            assert path.exists(), f"{path} was deleted during dry-run"
            assert path.stat().st_size == original_size, (
                f"{path} was modified during dry-run"
            )
