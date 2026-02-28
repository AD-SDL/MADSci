"""Integration tests for migration converter --apply against fixture data.

These tests run the converter against a copy of the v0.6 fixture data to
validate that IDs are registered, backups are created, deprecated markers
are added, and rollback restores originals.

The fixture data in fixtures/migration/v0.6/ is a static snapshot decoupled
from the live example lab, so these tests remain stable as the example lab
configuration evolves.
"""

import shutil
from pathlib import Path

import pytest
import yaml
from madsci.common.migration import MigrationConverter, MigrationScanner
from madsci.common.migration.converter import MigrationRollback
from madsci.common.registry import LocalRegistryManager
from madsci.common.types.migration_types import MigrationStatus, OutputFormat

# Path to v0.6 fixture data (self-contained, decoupled from live example_lab)
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "migration" / "v0.6"


@pytest.fixture()
def lab_copy(tmp_path: Path) -> Path:
    """Create a copy of v0.6 fixtures in tmp_path for safe modification."""
    if not FIXTURE_DIR.exists():
        pytest.skip("v0.6 fixture directory not found")
    dest = tmp_path / "v0.6_fixtures"
    shutil.copytree(FIXTURE_DIR, dest)
    return dest


@pytest.fixture()
def temp_registry(tmp_path: Path) -> LocalRegistryManager:
    """Create a temporary registry for testing."""
    registry_path = tmp_path / "test_registry.json"
    return LocalRegistryManager(registry_path=registry_path)


class TestMigrateConvertApply:
    """Test applying migration converter to a copy of fixture data."""

    def test_convert_apply_creates_backups(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Converting with apply should create .bak backup files."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        # Check that backup files exist for each migrated file
        for migration in plan.files:
            if migration.status == MigrationStatus.MIGRATED:
                assert migration.backup_path is not None
                assert migration.backup_path.exists(), (
                    f"Backup not created for {migration.source_path.name}"
                )

    def test_convert_apply_registers_ids(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Converting with apply should register component IDs in the registry."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        # Check that manager IDs are registered
        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]
        for m in manager_files:
            if m.component_id and m.name:
                registered_id = temp_registry.lookup(m.name)
                assert registered_id is not None, (
                    f"ID not registered for manager '{m.name}'"
                )
                assert registered_id == m.component_id, (
                    f"Registered ID mismatch for '{m.name}': "
                    f"expected {m.component_id}, got {registered_id}"
                )

    def test_convert_apply_adds_deprecation_marker(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Converting with apply should add deprecation markers to definition files."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        # Check that migrated files have deprecation markers
        for migration in plan.files:
            if migration.status == MigrationStatus.MIGRATED:
                content = migration.source_path.read_text()
                assert "DEPRECATED" in content, (
                    f"Deprecation marker missing in {migration.source_path.name}"
                )
                # Verify the file is still valid YAML with _deprecated field
                data = yaml.safe_load(content)
                assert data.get("_deprecated") is True, (
                    f"_deprecated field missing in {migration.source_path.name}"
                )

    def test_convert_apply_sets_migrated_status(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Converting with apply should set migration status to MIGRATED."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        results = []
        for migration in plan.files:
            result = converter.convert(migration, dry_run=False, create_backup=True)
            results.append(result)

        migrated_count = sum(1 for r in results if r.status == MigrationStatus.MIGRATED)
        assert migrated_count == len(results), (
            f"Expected all {len(results)} files to be migrated, "
            f"but only {migrated_count} were migrated"
        )

    def test_rollback_restores_originals(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Rollback should restore original file contents from backups."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()

        # Capture original content of first manager file
        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]
        first_manager = manager_files[0]
        original_content = first_manager.source_path.read_text()

        # Apply migration
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)
        migrated = converter.convert(first_manager, dry_run=False, create_backup=True)

        # Verify file was modified
        modified_content = migrated.source_path.read_text()
        assert modified_content != original_content

        # Rollback
        rollback = MigrationRollback(registry=temp_registry)
        rolled_back = rollback.rollback(migrated)

        # Verify restored
        restored_content = rolled_back.source_path.read_text()
        assert restored_content == original_content
        assert rolled_back.status == MigrationStatus.PENDING

    def test_rollback_removes_backup(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Rollback should remove the backup file after restoring."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        first_file = plan.files[0]

        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)
        migrated = converter.convert(first_file, dry_run=False, create_backup=True)
        assert migrated.backup_path is not None
        assert migrated.backup_path.exists()

        rollback = MigrationRollback(registry=temp_registry)
        rolled_back = rollback.rollback(migrated)

        assert not rolled_back.backup_path.exists(), (
            "Backup file should be removed after rollback"
        )

    def test_rescan_after_migration_shows_deprecated(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Rescanning after migration should show files as DEPRECATED."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        # Rescan
        new_plan = scanner.scan()
        deprecated_count = sum(
            1 for f in new_plan.files if f.status == MigrationStatus.DEPRECATED
        )
        assert deprecated_count == new_plan.total_count, (
            f"Expected all {new_plan.total_count} files to show as DEPRECATED after migration, "
            f"but only {deprecated_count} are"
        )

    def test_node_ids_registered(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Node IDs should be registered in the registry after migration."""
        scanner = MigrationScanner(lab_copy)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]
        for m in node_files:
            if m.component_id and m.name:
                registered_id = temp_registry.lookup(m.name)
                assert registered_id is not None, (
                    f"ID not registered for node '{m.name}'"
                )


class TestMigrateYamlOutput:
    """Test that YAML output format generates settings.yaml files."""

    def test_yaml_format_generates_settings_yaml_for_managers(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """YAML format should create <type>.settings.yaml for each manager."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]
        for m in manager_files:
            if m.status == MigrationStatus.MIGRATED:
                assert len(m.output_files) > 0, (
                    f"No output files for {m.source_path.name}"
                )
                output = m.output_files[0]
                assert output.name.endswith(".settings.yaml"), (
                    f"Expected .settings.yaml, got {output.name}"
                )
                assert output.exists(), f"Output file not created: {output}"
                # Verify it's valid YAML
                data = yaml.safe_load(output.read_text())
                assert isinstance(data, dict)

    def test_yaml_format_generates_per_node_directories(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """YAML format should create nodes/<node_name>/settings.yaml for each node."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]
        for m in node_files:
            if m.status == MigrationStatus.MIGRATED:
                assert len(m.output_files) > 0, f"No output files for node {m.name}"
                output = m.output_files[0]
                assert output.name == "settings.yaml", (
                    f"Expected settings.yaml, got {output.name}"
                )
                # Should be in a per-node directory: nodes/<node_name>/settings.yaml
                assert output.parent.name == m.name, (
                    f"Expected node dir '{m.name}', got '{output.parent.name}'"
                )
                assert output.parent.parent.name == "nodes"
                assert output.exists()
                # Verify it's valid YAML with node-specific settings
                data = yaml.safe_load(output.read_text())
                assert isinstance(data, dict)
                assert "node_name" in data

    def test_per_node_directories_avoid_conflicts(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Each node should get its own directory with unique settings."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        node_files = [
            m
            for m in plan.files
            if m.file_type.value == "node_definition"
            and m.status == MigrationStatus.MIGRATED
        ]
        assert len(node_files) >= 2, "Need at least 2 nodes to test conflict avoidance"

        # Collect all node settings
        node_settings = {}
        for m in node_files:
            output = m.output_files[0]
            data = yaml.safe_load(output.read_text())
            node_settings[m.name] = data

        # Verify each node has a distinct node_name
        node_names = [s.get("node_name") for s in node_settings.values()]
        assert len(set(node_names)) == len(node_names), (
            f"Node names should be unique, got: {node_names}"
        )

    def test_yaml_settings_contain_lowercase_keys(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """YAML output should use lowercase keys."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        for m in plan.files:
            if m.status == MigrationStatus.MIGRATED and m.output_files:
                output = m.output_files[0]
                data = yaml.safe_load(output.read_text())
                for key in data:
                    assert key == key.lower(), (
                        f"Expected lowercase key, got '{key}' in {output}"
                    )


class TestMigrateEnvOutput:
    """Test that env output format still works correctly."""

    def test_env_format_generates_dotenv_for_managers(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Env format should create .env.<type> for each manager."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.ENV)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        manager_files = [
            m for m in plan.files if m.file_type.value == "manager_definition"
        ]
        for m in manager_files:
            if m.status == MigrationStatus.MIGRATED and m.output_files:
                output = m.output_files[0]
                assert output.name.startswith(".env."), (
                    f"Expected .env.<type>, got {output.name}"
                )
                assert output.exists()

    def test_env_format_generates_per_node_directories(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Env format should also create per-node directories with .env files."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.ENV)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        node_files = [m for m in plan.files if m.file_type.value == "node_definition"]
        for m in node_files:
            if m.status == MigrationStatus.MIGRATED and m.output_files:
                output = m.output_files[0]
                assert output.name == ".env", f"Expected .env, got {output.name}"
                # Should be in a per-node directory
                assert output.parent.name == m.name
                assert output.parent.parent.name == "nodes"
                assert output.exists()


class TestMigrationLocationData:
    """Regression tests for location data preservation during migration."""

    def test_location_data_preserved_in_yaml_output(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Location definitions should appear in migrated YAML settings."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        # Find the location manager output
        location_migrations = [
            m
            for m in plan.files
            if m.original_data.get("manager_type") == "location_manager"
        ]
        assert len(location_migrations) == 1

        migration = location_migrations[0]
        assert migration.status == MigrationStatus.MIGRATED
        assert len(migration.output_files) > 0

        output = migration.output_files[0]
        data = yaml.safe_load(output.read_text())

        # Locations should be preserved with the prefixed key
        assert "location_locations" in data, (
            f"location_locations missing from migrated YAML. Keys: {list(data.keys())}"
        )
        locations = data["location_locations"]
        assert len(locations) == 2
        assert locations[0]["location_name"] == "deck_1"
        assert locations[1]["location_name"] == "deck_2"

        # Transfer capabilities should also be preserved
        assert "location_transfer_capabilities" in data
        tc = data["location_transfer_capabilities"]
        assert len(tc["transfer_templates"]) == 1
        assert tc["transfer_templates"][0]["node_name"] == "robot_arm"

    def test_manager_name_preserved_in_yaml_output(
        self, lab_copy: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Manager name and description should map to correct prefixed settings keys."""
        scanner = MigrationScanner(lab_copy, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry, output_dir=lab_copy)

        for migration in plan.files:
            converter.convert(migration, dry_run=False, create_backup=True)

        # Check all manager migrations produce correct name/description keys
        manager_files = [
            m
            for m in plan.files
            if m.file_type.value == "manager_definition"
            and m.status == MigrationStatus.MIGRATED
        ]

        for m in manager_files:
            manager_type = m.original_data.get("manager_type", "")
            prefix = manager_type.replace("_manager", "")
            output = m.output_files[0]
            data = yaml.safe_load(output.read_text())

            # Name should be mapped to {prefix}_manager_name, not {prefix}_name
            expected_name_key = f"{prefix}_manager_name"
            wrong_name_key = f"{prefix}_name"

            assert expected_name_key in data, (
                f"{m.source_path.name}: expected key '{expected_name_key}' "
                f"in output, got keys: {list(data.keys())}"
            )
            assert wrong_name_key not in data, (
                f"{m.source_path.name}: found incorrect key '{wrong_name_key}' "
                f"(should be '{expected_name_key}')"
            )

    def test_output_stays_within_project_for_root_definitions(
        self, tmp_path: Path, temp_registry: LocalRegistryManager
    ) -> None:
        """Migration output should stay within the project directory even for root-level definitions."""
        # Create a definition file at the project root (not in a subdirectory)
        definition = {
            "name": "Root Location Manager",
            "description": "A location manager at project root",
            "manager_id": "01JK7069DXAKAMWE0PDX6EY1PD",
            "manager_type": "location_manager",
            "locations": [
                {
                    "location_name": "deck_1",
                    "location_id": "01K5HDZZCF27YHD2WDGSXFPPKF",
                    "description": "Test deck 1",
                    "representations": {"robot_arm": {"position": [10, 15, 5]}},
                }
            ],
        }

        def_path = tmp_path / "location.manager.yaml"
        with def_path.open("w") as f:
            yaml.dump(definition, f, default_flow_style=False, sort_keys=False)

        scanner = MigrationScanner(tmp_path, output_format=OutputFormat.YAML)
        plan = scanner.scan()
        converter = MigrationConverter(registry=temp_registry)

        for migration in plan.files:
            result = converter.convert(migration, dry_run=False, create_backup=True)
            # Output file must be inside the project directory
            for output_file in result.output_files:
                assert str(output_file).startswith(str(tmp_path)), (
                    f"Output file {output_file} is outside project dir {tmp_path}"
                )
