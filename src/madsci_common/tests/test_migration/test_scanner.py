"""Tests for the MigrationScanner."""

import pytest
from madsci.common.migration import MigrationScanner
from madsci.common.types.migration_types import FileType, MigrationStatus


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project with definition files."""
    # Create manager definition
    managers_dir = tmp_path / "managers"
    managers_dir.mkdir()

    (managers_dir / "test.manager.yaml").write_text("""
name: Test Manager
manager_type: workcell_manager
manager_id: 01ABC123
nodes:
  node1: http://localhost:2000/
""")

    # Create node definition
    nodes_dir = tmp_path / "node_definitions"
    nodes_dir.mkdir()

    (nodes_dir / "test.node.yaml").write_text("""
node_name: test_node
node_id: 01XYZ789
module_name: test_module
""")

    return tmp_path


@pytest.fixture
def empty_project(tmp_path):
    """Create an empty project directory."""
    return tmp_path


class TestMigrationScanner:
    """Tests for MigrationScanner."""

    def test_scan_finds_definitions(self, sample_project):
        """Test that scanner finds definition files."""
        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        assert len(plan.files) == 2

        types = {m.file_type for m in plan.files}
        assert FileType.MANAGER_DEFINITION in types
        assert FileType.NODE_DEFINITION in types

    def test_scan_extracts_ids(self, sample_project):
        """Test that scanner extracts IDs from definitions."""
        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        manager = next(
            m for m in plan.files if m.file_type == FileType.MANAGER_DEFINITION
        )
        assert manager.component_id == "01ABC123"
        assert manager.name == "Test Manager"

        node = next(m for m in plan.files if m.file_type == FileType.NODE_DEFINITION)
        assert node.component_id == "01XYZ789"
        assert node.name == "test_node"

    def test_scan_empty_project(self, empty_project):
        """Test scanning an empty project."""
        scanner = MigrationScanner(empty_project)
        plan = scanner.scan()

        assert len(plan.files) == 0

    def test_scan_creates_actions(self, sample_project):
        """Test that scanner creates migration actions."""
        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        for migration in plan.files:
            # Should have at least register_id, generate_env, create_backup, mark_deprecated
            action_types = [a.action_type for a in migration.actions]
            assert "register_id" in action_types or migration.component_id == ""
            assert "create_backup" in action_types
            assert "mark_deprecated" in action_types

    def test_scan_status_pending_for_new_files(self, sample_project):
        """Test that new files have PENDING status."""
        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        for migration in plan.files:
            assert migration.status == MigrationStatus.PENDING

    def test_scan_skips_backup_files(self, sample_project):
        """Test that scanner skips .bak files."""
        # Create a backup file
        backup_file = sample_project / "managers" / "test.manager.yaml.bak"
        backup_file.write_text("backup content")

        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        # Should not include the backup file
        paths = [str(m.source_path) for m in plan.files]
        assert not any(".bak" in p for p in paths)

    def test_scan_detects_deprecated_files(self, sample_project):
        """Test that scanner detects already deprecated files."""
        # Modify a file to be deprecated
        manager_file = sample_project / "managers" / "test.manager.yaml"
        content = manager_file.read_text()
        manager_file.write_text(f"_deprecated: true\n{content}")

        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        manager = next(
            m for m in plan.files if m.file_type == FileType.MANAGER_DEFINITION
        )
        assert manager.status == MigrationStatus.DEPRECATED

    def test_plan_properties(self, sample_project):
        """Test migration plan properties."""
        scanner = MigrationScanner(sample_project)
        plan = scanner.scan()

        assert plan.total_count == 2
        assert plan.pending_count == 2
        assert plan.migrated_count == 0
        assert plan.progress_percent == 0
