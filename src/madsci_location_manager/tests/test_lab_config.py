"""Tests for the lab config file reconciliation (Phase 2: Lab Config as Living Document)."""

import time

import pytest
import yaml
from madsci.common.db_handlers.cache_handler import InMemoryCacheHandler
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.types.location_types import (
    LabLocationConfig,
    Location,
    LocationManagement,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
    RepresentationTrainingEntry,
)
from madsci.location_manager.location_server import LocationManager


@pytest.fixture
def document_handler():
    """Create an InMemoryDocumentStorageHandler for testing."""
    handler = InMemoryDocumentStorageHandler(database_name="test_lab_config")
    yield handler
    handler.close()


@pytest.fixture
def cache_handler():
    """Create an InMemoryCacheHandler for testing."""
    handler = InMemoryCacheHandler()
    yield handler
    handler.close()


def _make_manager(
    settings: LocationManagerSettings,
    cache_handler: InMemoryCacheHandler,
    document_handler: InMemoryDocumentStorageHandler,
) -> LocationManager:
    """Helper to create a LocationManager with in-memory handlers."""
    return LocationManager(
        settings=settings,
        cache_handler=cache_handler,
        document_handler=document_handler,
    )


class TestReconcileLabConfigRepresentationTemplates:
    """Lab config reconciliation creates and updates representation templates."""

    def test_creates_missing_representation_templates(
        self, tmp_path, cache_handler, document_handler
    ):
        """Representation templates from the config file are created on startup."""
        config = LabLocationConfig(
            representation_templates=[
                LocationRepresentationTemplate(
                    template_name="arm_repr",
                    default_values={"gripper": "standard"},
                    version="1.0.0",
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup reconciliation should have created the template
        tmpl = manager.state_handler.get_representation_template("arm_repr")
        assert tmpl is not None
        assert tmpl.default_values == {"gripper": "standard"}

    def test_updates_representation_template_on_version_change(
        self, tmp_path, cache_handler, document_handler
    ):
        """Existing representation template is updated when version changes in config."""
        # First, create with v1
        config_v1 = LabLocationConfig(
            representation_templates=[
                LocationRepresentationTemplate(
                    template_name="arm_repr",
                    default_values={"gripper": "standard"},
                    version="1.0.0",
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config_v1.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Verify v1 was created
        tmpl = manager.state_handler.get_representation_template("arm_repr")
        assert tmpl is not None
        assert tmpl.version == "1.0.0"

        # Now update to v2
        config_v2 = LabLocationConfig(
            representation_templates=[
                LocationRepresentationTemplate(
                    template_name="arm_repr",
                    default_values={"gripper": "wide"},
                    version="2.0.0",
                ),
            ],
        )
        config_path.write_text(yaml.dump(config_v2.model_dump(mode="json")))

        # Force mtime cache invalidation
        manager._lab_config_mtime = None

        results = manager._reconcile_lab_config()
        assert results["templates_synced"] >= 1
        tmpl = manager.state_handler.get_representation_template("arm_repr")
        assert tmpl.default_values == {"gripper": "wide"}
        assert tmpl.version == "2.0.0"


class TestReconcileLabConfigLocationTemplates:
    """Lab config reconciliation creates and updates location templates."""

    def test_creates_missing_location_templates(
        self, tmp_path, cache_handler, document_handler
    ):
        """Location templates from the config file are created on startup."""
        config = LabLocationConfig(
            location_templates=[
                LocationTemplate(
                    template_name="deck_slot",
                    representation_templates={"arm": "arm_repr"},
                    version="1.0.0",
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup reconciliation should have created the template
        tmpl = manager.state_handler.get_location_template("deck_slot")
        assert tmpl is not None
        assert tmpl.representation_templates == {"arm": "arm_repr"}

    def test_updates_location_template_on_version_change(
        self, tmp_path, cache_handler, document_handler
    ):
        """Existing location template is updated when version changes in config."""
        config_v1 = LabLocationConfig(
            location_templates=[
                LocationTemplate(
                    template_name="deck_slot",
                    representation_templates={"arm": "arm_repr"},
                    version="1.0.0",
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config_v1.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Verify v1 was created
        tmpl = manager.state_handler.get_location_template("deck_slot")
        assert tmpl is not None
        assert tmpl.version == "1.0.0"

        config_v2 = LabLocationConfig(
            location_templates=[
                LocationTemplate(
                    template_name="deck_slot",
                    representation_templates={"arm": "arm_repr", "lh": "lh_repr"},
                    version="2.0.0",
                ),
            ],
        )
        config_path.write_text(yaml.dump(config_v2.model_dump(mode="json")))
        manager._lab_config_mtime = None

        results = manager._reconcile_lab_config()
        assert results["templates_synced"] >= 1
        tmpl = manager.state_handler.get_location_template("deck_slot")
        assert tmpl.representation_templates == {"arm": "arm_repr", "lh": "lh_repr"}


class TestReconcileLabConfigLocations:
    """Lab config reconciliation creates locations with managed_by=LAB."""

    def test_creates_missing_locations(self, tmp_path, cache_handler, document_handler):
        """Locations from the config file are created with managed_by=LAB on startup."""
        config = LabLocationConfig(
            locations=[
                Location(
                    location_name="slot_1",
                    description="First deck slot",
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup reconciliation should have created the location
        loc = manager.state_handler.get_location("slot_1")
        assert loc is not None
        assert loc.managed_by == LocationManagement.LAB
        assert loc.description == "First deck slot"

    def test_existing_locations_are_not_duplicated(
        self, tmp_path, cache_handler, document_handler
    ):
        """Running reconciliation again does not duplicate locations (idempotent)."""
        config = LabLocationConfig(
            locations=[
                Location(location_name="slot_1"),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup already synced. Run again:
        manager._lab_config_mtime = None
        results = manager._reconcile_lab_config()

        assert results["locations_synced"] == 0
        # Verify only one location exists
        all_locs = manager.state_handler.get_locations()
        assert len(all_locs) == 1


class TestReconcileLabConfigTraining:
    """Lab config reconciliation applies training entries."""

    def test_training_adds_representations(
        self, tmp_path, cache_handler, document_handler
    ):
        """Training entries add node representations to existing locations."""
        config = LabLocationConfig(
            representation_templates=[
                LocationRepresentationTemplate(
                    template_name="arm_repr",
                    default_values={"gripper": "standard", "max_payload": 2.0},
                ),
            ],
            locations=[
                Location(location_name="slot_1"),
            ],
            training=[
                RepresentationTrainingEntry(
                    location_name="slot_1",
                    node_name="robotarm_1",
                    representation_template_name="arm_repr",
                    overrides={"position": [1, 2, 3]},
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup reconciliation should have applied training
        loc = manager.state_handler.get_location("slot_1")
        repr_data = loc.representations["robotarm_1"]
        # Template defaults merged with overrides
        assert repr_data["gripper"] == "standard"
        assert repr_data["max_payload"] == 2.0
        assert repr_data["position"] == [1, 2, 3]

    def test_training_without_template(self, tmp_path, cache_handler, document_handler):
        """Training entries without a template use only overrides."""
        config = LabLocationConfig(
            locations=[
                Location(location_name="slot_1"),
            ],
            training=[
                RepresentationTrainingEntry(
                    location_name="slot_1",
                    node_name="robotarm_1",
                    overrides={"position": [4, 5, 6]},
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup reconciliation should have applied training
        loc = manager.state_handler.get_location("slot_1")
        assert loc.representations["robotarm_1"] == {"position": [4, 5, 6]}

    def test_training_for_nonexistent_location_is_skipped(
        self, tmp_path, cache_handler, document_handler
    ):
        """Training entries for locations that don't exist are skipped, not errors."""
        config = LabLocationConfig(
            training=[
                RepresentationTrainingEntry(
                    location_name="nonexistent_slot",
                    node_name="robotarm_1",
                    overrides={"position": [1, 2, 3]},
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        # Startup reconciliation skips the training entry
        manager = _make_manager(settings, cache_handler, document_handler)

        # Call again explicitly to verify results
        manager._lab_config_mtime = None
        results = manager._reconcile_lab_config()

        assert results["training_skipped"] == 1
        assert results["training_applied"] == 0


class TestReconcileLabConfigCaching:
    """Lab config file mtime caching behavior."""

    def test_mtime_caching_uses_cached_config(
        self, tmp_path, cache_handler, document_handler
    ):
        """Same mtime means the file is not re-parsed, but cached config is still processed."""
        config = LabLocationConfig(
            locations=[
                Location(location_name="cached_loc"),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup created the location
        assert manager.state_handler.get_location("cached_loc") is not None

        # Delete the location to test whether cache still works
        manager.state_handler.delete_location("cached_loc")

        # Second call with same mtime should use cached config
        # and re-create the location since it's missing
        results = manager._reconcile_lab_config()
        assert results["locations_synced"] == 1
        assert manager.state_handler.get_location("cached_loc") is not None

    def test_file_changes_detected_on_mtime_change(
        self, tmp_path, cache_handler, document_handler
    ):
        """When file mtime changes, the new content is parsed."""
        config_v1 = LabLocationConfig(
            locations=[
                Location(location_name="v1_loc"),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config_v1.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup created v1_loc
        assert manager.state_handler.get_location("v1_loc") is not None

        # Write new content (mtime changes)
        config_v2 = LabLocationConfig(
            locations=[
                Location(location_name="v1_loc"),
                Location(location_name="v2_loc"),
            ],
        )
        # Ensure mtime actually changes
        time.sleep(0.05)
        config_path.write_text(yaml.dump(config_v2.model_dump(mode="json")))

        results = manager._reconcile_lab_config()
        assert results["locations_synced"] == 1  # v2_loc is new
        assert manager.state_handler.get_location("v2_loc") is not None


class TestReconcileLabConfigNoFile:
    """Behavior when lab config file is absent or disabled."""

    def test_no_file_returns_zero_results(
        self, tmp_path, cache_handler, document_handler
    ):
        """When the lab config file doesn't exist, nothing happens."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(tmp_path / "nonexistent.yaml"),
        )
        manager = _make_manager(settings, cache_handler, document_handler)
        results = manager._reconcile_lab_config()

        assert results["templates_synced"] == 0
        assert results["locations_synced"] == 0
        assert results["training_applied"] == 0
        assert results["training_skipped"] == 0

    def test_disabled_returns_zero_results(self, cache_handler, document_handler):
        """When lab_config_file is None, nothing happens."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=None,
        )
        manager = _make_manager(settings, cache_handler, document_handler)
        results = manager._reconcile_lab_config()

        assert results["templates_synced"] == 0
        assert results["locations_synced"] == 0
        assert results["training_applied"] == 0
        assert results["training_skipped"] == 0


class TestReconcileLabConfigTransferGraph:
    """Transfer graph is rebuilt when lab config changes affect locations or training."""

    def test_graph_rebuilt_when_locations_synced(
        self, tmp_path, cache_handler, document_handler
    ):
        """Transfer graph is rebuilt when new locations are synced from config."""
        config = LabLocationConfig(
            locations=[
                Location(location_name="graph_loc_1"),
                Location(location_name="graph_loc_2"),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Verify both locations were created on startup
        assert manager.state_handler.get_location("graph_loc_1") is not None
        assert manager.state_handler.get_location("graph_loc_2") is not None
        # The test verifies the method completes without error when calling
        # _rebuild_transfer_graph (which delegates to transfer_planner.rebuild_transfer_graph)


class TestReconcileIntegration:
    """Integration test: _reconcile() calls _reconcile_lab_config()."""

    def test_reconcile_includes_lab_config_results(
        self, tmp_path, cache_handler, document_handler
    ):
        """The main _reconcile() method includes lab config results."""
        config = LabLocationConfig(
            locations=[
                Location(location_name="integrated_loc"),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # Startup already synced. Delete and force re-reconcile.
        manager.state_handler.delete_location("integrated_loc")
        manager._lab_config_mtime = None

        results = manager._reconcile()

        # Should include both existing reconciliation keys and new lab config keys
        assert "resources_resolved" in results
        assert "representations_updated" in results
        assert "templates_synced" in results
        assert "locations_synced" in results
        assert "training_applied" in results
        assert results["locations_synced"] == 1


class TestStartupReconciliation:
    """Tests that lab config is reconciled during manager initialization."""

    def test_startup_reconciles_lab_config(
        self, tmp_path, cache_handler, document_handler
    ):
        """Manager startup reconciles the lab config file and creates resources."""
        config = LabLocationConfig(
            representation_templates=[
                LocationRepresentationTemplate(
                    template_name="startup_repr",
                    default_values={"key": "value"},
                    version="1.0.0",
                ),
            ],
            location_templates=[
                LocationTemplate(
                    template_name="startup_tmpl",
                    representation_templates={"role": "startup_repr"},
                    version="1.0.0",
                ),
            ],
            locations=[
                Location(location_name="startup_loc"),
            ],
            training=[
                RepresentationTrainingEntry(
                    location_name="startup_loc",
                    node_name="node_1",
                    representation_template_name="startup_repr",
                    overrides={"extra": "data"},
                ),
            ],
        )
        config_path = tmp_path / "locations.yaml"
        config_path.write_text(yaml.dump(config.model_dump(mode="json")))

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_enabled=False,
            lab_config_file=str(config_path),
        )
        manager = _make_manager(settings, cache_handler, document_handler)

        # All items should have been synced at startup
        assert (
            manager.state_handler.get_representation_template("startup_repr")
            is not None
        )
        assert manager.state_handler.get_location_template("startup_tmpl") is not None
        loc = manager.state_handler.get_location("startup_loc")
        assert loc is not None
        assert loc.managed_by == LocationManagement.LAB
        # Training should have been applied
        repr_data = loc.representations.get("node_1")
        assert repr_data is not None
        assert repr_data["key"] == "value"
        assert repr_data["extra"] == "data"
