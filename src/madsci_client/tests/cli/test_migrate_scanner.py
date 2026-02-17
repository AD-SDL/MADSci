"""Integration tests for migration scanner against versioned fixture data.

These tests validate that the migration scanner correctly finds all definition
files in the v0.6-format fixture directory and that convert --dry-run produces
correct output.

The fixture data in fixtures/migration/v0.6/ is a static snapshot of the
v0.6 definition format. Future config format changes can add v0.7/, v0.8/
etc. without breaking existing tests.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.migration import MigrationScanner

# Path to v0.6 fixture data (self-contained, decoupled from live example_lab)
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "migration" / "v0.6"


@pytest.fixture()
def fixture_path() -> Path:
    """Get path to v0.6 fixture data, skip if not found."""
    if not FIXTURE_DIR.exists():
        pytest.skip("v0.6 fixture directory not found")
    return FIXTURE_DIR


class TestMigrationScannerAgainstFixtures:
    """Validate that MigrationScanner finds all definition files in fixtures."""

    def test_scanner_finds_all_manager_definitions(self, fixture_path: Path) -> None:
        """Scanner should find all 7 manager definition files."""
        scanner = MigrationScanner(fixture_path)
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
            "lab.manager.yaml",
            "event.manager.yaml",
            "experiment.manager.yaml",
            "resource.manager.yaml",
            "data.manager.yaml",
            "workcell.manager.yaml",
            "location.manager.yaml",
        }
        assert manager_names == expected_managers

    def test_scanner_finds_all_node_definitions(self, fixture_path: Path) -> None:
        """Scanner should find all 3 node definition files."""
        scanner = MigrationScanner(fixture_path)
        plan = scanner.scan()

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]
        node_names = {m.source_path.name for m in node_files}

        expected_nodes = {
            "robot.node.yaml",
            "liquid_handler.node.yaml",
            "plate_reader.node.yaml",
        }
        assert node_names == expected_nodes, (
            f"Expected {expected_nodes}, got {node_names}"
        )
        assert len(node_files) == 3

    def test_scanner_total_file_count(self, fixture_path: Path) -> None:
        """Scanner should find exactly 10 definition files (7 manager + 3 node)."""
        scanner = MigrationScanner(fixture_path)
        plan = scanner.scan()

        assert plan.total_count == 10, (
            f"Expected 10 total definition files, found {plan.total_count}"
        )

    def test_all_files_have_pending_status(self, fixture_path: Path) -> None:
        """All found files should have PENDING status (not yet migrated)."""
        scanner = MigrationScanner(fixture_path)
        plan = scanner.scan()

        assert plan.pending_count == plan.total_count
        assert plan.migrated_count == 0
        assert plan.failed_count == 0

    def test_all_manager_files_have_component_ids(self, fixture_path: Path) -> None:
        """All manager definition files should have extractable component IDs."""
        scanner = MigrationScanner(fixture_path)
        plan = scanner.scan()

        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]

        for m in manager_files:
            assert m.component_id, f"{m.source_path.name} has no component_id"
            assert m.name, f"{m.source_path.name} has no name"

    def test_all_node_files_have_component_ids(self, fixture_path: Path) -> None:
        """All node definition files should have extractable component IDs."""
        scanner = MigrationScanner(fixture_path)
        plan = scanner.scan()

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]

        for m in node_files:
            assert m.component_id, f"{m.source_path.name} has no component_id"
            assert m.name, f"{m.source_path.name} has no name"

    def test_manager_files_have_migration_actions(self, fixture_path: Path) -> None:
        """All manager files should have planned migration actions."""
        scanner = MigrationScanner(fixture_path)
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


class TestMigrateScanCLIAgainstFixtures:
    """Validate the CLI `madsci migrate scan` command against fixture data."""

    def test_scan_cli_finds_files(self, fixture_path: Path) -> None:
        """CLI scan should find and report migration files."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "scan", str(fixture_path)])

        assert result.exit_code == 0
        assert "files requiring migration" in result.output

    def test_scan_cli_json_output(self, fixture_path: Path) -> None:
        """CLI scan JSON output should be parseable and have expected structure."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["migrate", "scan", str(fixture_path), "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "files" in data
        assert len(data["files"]) == 10

    def test_scan_cli_verbose_shows_details(self, fixture_path: Path) -> None:
        """CLI scan with --verbose should show names and IDs."""
        runner = CliRunner()
        result = runner.invoke(
            madsci, ["migrate", "scan", str(fixture_path), "--verbose"]
        )

        assert result.exit_code == 0
        # Verbose output should include component names
        assert "Name:" in result.output
        assert "ID:" in result.output


class TestMigrateConvertDryRunAgainstFixtures:
    """Validate convert --dry-run against fixture data."""

    def test_convert_dry_run_does_not_modify_files(self, fixture_path: Path) -> None:
        """Convert --dry-run should not modify any files."""
        from madsci.common.migration import MigrationConverter

        scanner = MigrationScanner(fixture_path)
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
