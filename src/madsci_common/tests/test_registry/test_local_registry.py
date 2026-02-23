"""Tests for the LocalRegistryManager."""

import tempfile
from pathlib import Path

import pytest
from madsci.common.registry import LocalRegistryManager, LockManager, RegistryLockError


@pytest.fixture
def temp_registry():
    """Create a temporary registry for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = LocalRegistryManager(registry_path=Path(tmpdir) / "registry.json")
        yield registry


@pytest.fixture
def temp_registry_with_lock():
    """Create a temporary registry with a custom lock manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_manager = LockManager()
        registry = LocalRegistryManager(
            registry_path=Path(tmpdir) / "registry.json",
            lock_manager=lock_manager,
        )
        yield registry, lock_manager


class TestLocalRegistryManager:
    """Tests for LocalRegistryManager."""

    def test_resolve_creates_new_id(self, temp_registry):
        """Test that resolving a new name creates a new ID."""
        node_id = temp_registry.resolve("test_node", "node", acquire_lock=False)

        assert node_id is not None
        assert len(node_id) == 26  # ULID length

    def test_resolve_returns_same_id(self, temp_registry):
        """Test that resolving the same name returns the same ID."""
        id1 = temp_registry.resolve("test_node", "node", acquire_lock=False)
        id2 = temp_registry.resolve("test_node", "node", acquire_lock=False)

        assert id1 == id2

    def test_resolve_different_names_different_ids(self, temp_registry):
        """Test that different names get different IDs."""
        id1 = temp_registry.resolve("node_1", "node", acquire_lock=False)
        id2 = temp_registry.resolve("node_2", "node", acquire_lock=False)

        assert id1 != id2

    def test_resolve_stores_metadata(self, temp_registry):
        """Test that metadata is stored with the entry."""
        metadata = {"module_name": "test_module", "version": "1.0.0"}
        temp_registry.resolve(
            "test_node", "node", metadata=metadata, acquire_lock=False
        )

        entry = temp_registry.get_entry("test_node")
        assert entry is not None
        assert entry.metadata["module_name"] == "test_module"
        assert entry.metadata["version"] == "1.0.0"

    def test_lookup_returns_id(self, temp_registry):
        """Test that lookup returns the ID without acquiring lock."""
        expected_id = temp_registry.resolve("test_node", "node", acquire_lock=False)
        found_id = temp_registry.lookup("test_node")

        assert found_id == expected_id

    def test_lookup_returns_none_for_missing(self, temp_registry):
        """Test that lookup returns None for missing entries."""
        found_id = temp_registry.lookup("nonexistent")

        assert found_id is None

    def test_get_entry_returns_full_entry(self, temp_registry):
        """Test that get_entry returns the full entry."""
        temp_registry.resolve(
            "test_node", "node", metadata={"key": "value"}, acquire_lock=False
        )

        entry = temp_registry.get_entry("test_node")

        assert entry is not None
        assert entry.component_type == "node"
        assert entry.metadata["key"] == "value"

    def test_list_entries_returns_all(self, temp_registry):
        """Test that list_entries returns all entries."""
        temp_registry.resolve("node_1", "node", acquire_lock=False)
        temp_registry.resolve("node_2", "node", acquire_lock=False)
        temp_registry.resolve("manager_1", "manager", acquire_lock=False)

        entries = temp_registry.list_entries(include_stale=True)

        assert len(entries) == 3

    def test_list_entries_filters_by_type(self, temp_registry):
        """Test that list_entries filters by component type."""
        temp_registry.resolve("node_1", "node", acquire_lock=False)
        temp_registry.resolve("node_2", "node", acquire_lock=False)
        temp_registry.resolve("manager_1", "manager", acquire_lock=False)

        entries = temp_registry.list_entries(component_type="node", include_stale=True)

        assert len(entries) == 2
        assert all(e.component_type == "node" for _, e in entries)

    def test_rename_changes_name_keeps_id(self, temp_registry):
        """Test that rename changes the name but keeps the ID."""
        original_id = temp_registry.resolve("old_name", "node", acquire_lock=False)

        returned_id = temp_registry.rename("old_name", "new_name")

        assert returned_id == original_id
        assert temp_registry.lookup("old_name") is None
        assert temp_registry.lookup("new_name") == original_id

    def test_export_and_import(self, temp_registry):
        """Test export and import of registry data."""
        temp_registry.resolve("node_1", "node", acquire_lock=False)
        temp_registry.resolve("node_2", "node", acquire_lock=False)

        exported = temp_registry.export()

        # Create a new registry and import
        with tempfile.TemporaryDirectory() as tmpdir:
            new_registry = LocalRegistryManager(
                registry_path=Path(tmpdir) / "new_registry.json"
            )
            new_registry.import_entries(exported)

            # Verify entries were imported
            assert new_registry.lookup("node_1") is not None
            assert new_registry.lookup("node_2") is not None


class TestLockManager:
    """Tests for the LockManager."""

    def test_lock_prevents_duplicate(self):
        """Test that locks prevent duplicate claims."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry1 = LocalRegistryManager(
                registry_path=Path(tmpdir) / "registry.json",
                lock_manager=LockManager(),
            )
            registry2 = LocalRegistryManager(
                registry_path=Path(tmpdir) / "registry.json",
                lock_manager=LockManager(),  # Different instance
            )

            # First resolver gets the lock
            registry1.resolve("test_node", "node")

            # Second resolver should fail
            with pytest.raises(RegistryLockError):
                registry2.resolve("test_node", "node")

            # Clean up
            registry1.release("test_node")

    def test_lock_release_allows_new_claim(self):
        """Test that releasing a lock allows another process to claim."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry1 = LocalRegistryManager(
                registry_path=Path(tmpdir) / "registry.json",
                lock_manager=LockManager(),
            )
            registry2 = LocalRegistryManager(
                registry_path=Path(tmpdir) / "registry.json",
                lock_manager=LockManager(),
            )

            # First resolver gets the lock
            id1 = registry1.resolve("test_node", "node")

            # Release the lock
            registry1.release("test_node")

            # Now second resolver should succeed with same ID
            id2 = registry2.resolve("test_node", "node")
            assert id1 == id2

            # Clean up
            registry2.release("test_node")
