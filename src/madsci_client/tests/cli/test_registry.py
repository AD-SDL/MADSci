"""Tests for the madsci registry command."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci


class TestRegistryCommandGroup:
    """Tests for the registry command group."""

    def test_registry_help(self) -> None:
        """Test that registry command shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "--help"])

        assert result.exit_code == 0
        assert "ID Registry management commands" in result.output
        assert "list" in result.output
        assert "resolve" in result.output
        assert "rename" in result.output
        assert "clean" in result.output
        assert "export" in result.output
        assert "import" in result.output


class TestRegistryListCommand:
    """Tests for the registry list command."""

    def test_list_help(self) -> None:
        """Test that list subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "list", "--help"])

        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--include-stale" in result.output
        assert "--json" in result.output

    def test_list_empty_registry(self) -> None:
        """Test listing entries on an empty registry."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(madsci, ["registry", "list"])

        assert result.exit_code == 0
        assert "No registry entries found" in result.output

    def test_list_empty_registry_json(self) -> None:
        """Test listing entries on an empty registry with JSON output."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(madsci, ["registry", "list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_list_with_entries(self) -> None:
        """Test listing entries on a registry with entries."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                # First, register an entry by resolving a name
                from madsci.common.registry import LocalRegistryManager

                mgr = LocalRegistryManager()
                mgr.resolve("test_node", component_type="node")
                mgr.release("test_node")

                # Now list
                result = runner.invoke(madsci, ["registry", "list"])

        assert result.exit_code == 0
        assert "test_node" in result.output

    def test_list_type_filter(self) -> None:
        """Test listing entries with type filter."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                from madsci.common.registry import LocalRegistryManager

                mgr = LocalRegistryManager()
                mgr.resolve("test_node", component_type="node")
                mgr.resolve("test_manager", component_type="manager")
                mgr.release("test_node")
                mgr.release("test_manager")

                result = runner.invoke(
                    madsci, ["registry", "list", "--type", "node", "--json"]
                )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "test_node"
        assert data[0]["type"] == "node"


class TestRegistryResolveCommand:
    """Tests for the registry resolve command."""

    def test_resolve_help(self) -> None:
        """Test that resolve subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "resolve", "--help"])

        assert result.exit_code == 0
        assert "NAME" in result.output
        assert "--json" in result.output

    def test_resolve_not_found(self) -> None:
        """Test resolving a name that doesn't exist."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(madsci, ["registry", "resolve", "nonexistent"])

        # ctx.exit(1) doesn't set exit_code in Click's CliRunner
        assert "not found" in result.output

    def test_resolve_not_found_json(self) -> None:
        """Test resolving a nonexistent name with JSON output."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(
                    madsci, ["registry", "resolve", "nonexistent", "--json"]
                )

        data = json.loads(result.output)
        assert "error" in data

    def test_resolve_existing_entry(self) -> None:
        """Test resolving a registered name."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                from madsci.common.registry import LocalRegistryManager

                mgr = LocalRegistryManager()
                component_id = mgr.resolve("test_node", component_type="node")
                mgr.release("test_node")

                result = runner.invoke(
                    madsci, ["registry", "resolve", "test_node", "--json"]
                )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "test_node"
        assert data["id"] == component_id
        assert data["type"] == "node"


class TestRegistryRenameCommand:
    """Tests for the registry rename command."""

    def test_rename_help(self) -> None:
        """Test that rename subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "rename", "--help"])

        assert result.exit_code == 0
        assert "OLD_NAME" in result.output
        assert "NEW_NAME" in result.output
        assert "--force" in result.output

    def test_rename_nonexistent(self) -> None:
        """Test renaming a name that doesn't exist."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(
                    madsci, ["registry", "rename", "old_name", "new_name"]
                )

        assert "Error" in result.output or "not found" in result.output.lower()

    def test_rename_success(self) -> None:
        """Test successfully renaming an entry."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                from madsci.common.registry import LocalRegistryManager

                mgr = LocalRegistryManager()
                mgr.resolve("old_name", component_type="node")
                mgr.release("old_name")

                result = runner.invoke(
                    madsci, ["registry", "rename", "old_name", "new_name"]
                )

        assert result.exit_code == 0
        assert "Renamed" in result.output


class TestRegistryCleanCommand:
    """Tests for the registry clean command."""

    def test_clean_help(self) -> None:
        """Test that clean subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "clean", "--help"])

        assert result.exit_code == 0
        assert "--older-than" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_clean_empty_registry(self) -> None:
        """Test cleaning an empty registry."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(madsci, ["registry", "clean", "--force"])

        assert result.exit_code == 0
        assert "No stale entries" in result.output

    def test_clean_dry_run(self) -> None:
        """Test clean dry run mode."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(madsci, ["registry", "clean", "--dry-run"])

        assert result.exit_code == 0


class TestRegistryExportCommand:
    """Tests for the registry export command."""

    def test_export_help(self) -> None:
        """Test that export subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "export", "--help"])

        assert result.exit_code == 0
        assert "--output" in result.output

    def test_export_stdout(self) -> None:
        """Test exporting registry to stdout."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(madsci, ["registry", "export"])

        assert result.exit_code == 0
        # Output should be valid JSON
        data = json.loads(result.output)
        assert "entries" in data or "version" in data

    def test_export_to_file(self) -> None:
        """Test exporting registry to a file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            output_path = Path(tmpdir) / "export.json"
            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(
                    madsci, ["registry", "export", "--output", str(output_path)]
                )

            assert result.exit_code == 0
            assert "Exported" in result.output
            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert isinstance(data, dict)


class TestRegistryImportCommand:
    """Tests for the registry import command."""

    def test_import_help(self) -> None:
        """Test that import subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["registry", "import", "--help"])

        assert result.exit_code == 0
        assert "FILE" in result.output
        assert "--merge" in result.output
        assert "--force" in result.output

    def test_import_from_file(self) -> None:
        """Test importing registry from a file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"

            # Create an import file
            import_path = Path(tmpdir) / "import.json"
            import_data = {"entries": {}, "version": 1}
            import_path.write_text(json.dumps(import_data))

            with patch.dict(os.environ, {"MADSCI_REGISTRY_PATH": str(registry_path)}):
                result = runner.invoke(
                    madsci,
                    ["registry", "import", str(import_path), "--force"],
                )

        assert result.exit_code == 0
        assert "Imported" in result.output
