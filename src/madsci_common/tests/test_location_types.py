"""Tests for location_types.py — Phase 1 of MongoDB migration + Phase 2 lab config types."""

import yaml
from madsci.common.types.location_types import (
    LabLocationConfig,
    Location,
    LocationImportResult,
    LocationManagerHealth,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
    RepresentationTrainingEntry,
)


class TestLocationManagerSettings:
    """Tests for the updated LocationManagerSettings."""

    def test_settings_has_document_db_fields(self):
        """Verify document_db_url and database_name exist with defaults."""
        settings = LocationManagerSettings(enable_registry_resolution=False)
        assert str(settings.document_db_url) == "mongodb://localhost:27017/"
        assert settings.database_name == "madsci_locations"

    def test_settings_document_db_url_mongo_alias(self):
        """Verify mongo_db_url alias works for backward compatibility."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            mongo_db_url="mongodb://custom:27017/",
        )
        assert str(settings.document_db_url) == "mongodb://custom:27017/"


class TestLocationManagerHealth:
    """Tests for the updated LocationManagerHealth."""

    def test_health_has_document_db_connected(self):
        """Verify document_db_connected field exists."""
        health = LocationManagerHealth()
        assert health.document_db_connected is None

    def test_health_has_cache_connected(self):
        """Verify cache_connected field still exists."""
        health = LocationManagerHealth()
        assert health.cache_connected is None

    def test_health_document_db_connected_set(self):
        """Verify document_db_connected can be set."""
        health = LocationManagerHealth(document_db_connected=True)
        assert health.document_db_connected is True

    def test_health_has_num_node_managed_locations(self):
        """Verify num_node_managed_locations field exists with default 0."""
        health = LocationManagerHealth()
        assert health.num_node_managed_locations == 0

    def test_health_has_num_lab_managed_locations(self):
        """Verify num_lab_managed_locations field exists with default 0."""
        health = LocationManagerHealth()
        assert health.num_lab_managed_locations == 0

    def test_health_has_last_reconciliation_at(self):
        """Verify last_reconciliation_at field exists with default None."""
        health = LocationManagerHealth()
        assert health.last_reconciliation_at is None

    def test_health_node_managed_locations_set(self):
        """Verify num_node_managed_locations can be set."""
        health = LocationManagerHealth(num_node_managed_locations=5)
        assert health.num_node_managed_locations == 5

    def test_health_lab_managed_locations_set(self):
        """Verify num_lab_managed_locations can be set."""
        health = LocationManagerHealth(num_lab_managed_locations=3)
        assert health.num_lab_managed_locations == 3

    def test_health_last_reconciliation_at_set(self):
        """Verify last_reconciliation_at can be set to an ISO timestamp."""
        health = LocationManagerHealth(
            last_reconciliation_at="2026-04-09T12:00:00+00:00"
        )
        assert health.last_reconciliation_at == "2026-04-09T12:00:00+00:00"


class TestLocationImportResult:
    """Tests for the new LocationImportResult model."""

    def test_import_result_model(self):
        """Verify LocationImportResult structure and defaults."""
        result = LocationImportResult()
        assert result.imported == 0
        assert result.skipped == 0
        assert result.errors == []
        assert result.locations == []

    def test_import_result_with_data(self):
        """Verify LocationImportResult with populated data."""
        loc = Location(location_name="test_loc")
        result = LocationImportResult(
            imported=1,
            skipped=2,
            errors=["error1"],
            locations=[loc],
        )
        assert result.imported == 1
        assert result.skipped == 2
        assert result.errors == ["error1"]
        assert len(result.locations) == 1
        assert result.locations[0].location_name == "test_loc"


class TestRepresentationTrainingEntry:
    """Tests for the RepresentationTrainingEntry model."""

    def test_minimal_training_entry(self):
        """Training entry requires only location_name and node_name."""
        entry = RepresentationTrainingEntry(
            location_name="deck_slot_1",
            node_name="robotarm_1",
        )
        assert entry.location_name == "deck_slot_1"
        assert entry.node_name == "robotarm_1"
        assert entry.representation_template_name is None
        assert entry.overrides == {}

    def test_training_entry_with_template_and_overrides(self):
        """Training entry can specify a representation template and overrides."""
        entry = RepresentationTrainingEntry(
            location_name="deck_slot_1",
            node_name="robotarm_1",
            representation_template_name="arm_deck_access",
            overrides={"position": [1, 2, 3], "gripper": "wide"},
        )
        assert entry.representation_template_name == "arm_deck_access"
        assert entry.overrides == {"position": [1, 2, 3], "gripper": "wide"}


class TestLabLocationConfig:
    """Tests for the LabLocationConfig model."""

    def test_empty_config(self):
        """LabLocationConfig validates with all-empty defaults."""
        config = LabLocationConfig()
        assert config.representation_templates == []
        assert config.location_templates == []
        assert config.training == []
        assert config.locations == []

    def test_fully_populated_config(self):
        """LabLocationConfig validates with all fields populated."""
        repr_tmpl = LocationRepresentationTemplate(
            template_name="arm_repr",
            default_values={"gripper": "standard"},
        )
        loc_tmpl = LocationTemplate(
            template_name="deck_slot",
            representation_templates={"arm": "arm_repr"},
        )
        training = RepresentationTrainingEntry(
            location_name="slot_1",
            node_name="robotarm_1",
            representation_template_name="arm_repr",
            overrides={"position": [0, 0, 0]},
        )
        loc = Location(
            location_name="slot_1",
            description="First deck slot",
        )
        config = LabLocationConfig(
            representation_templates=[repr_tmpl],
            location_templates=[loc_tmpl],
            training=[training],
            locations=[loc],
        )
        assert len(config.representation_templates) == 1
        assert len(config.location_templates) == 1
        assert len(config.training) == 1
        assert len(config.locations) == 1

    def test_yaml_round_trip(self, tmp_path):
        """LabLocationConfig round-trips through YAML without data loss."""
        config = LabLocationConfig(
            representation_templates=[
                LocationRepresentationTemplate(
                    template_name="arm_repr",
                    default_values={"gripper": "standard"},
                    version="1.0.0",
                ),
            ],
            location_templates=[
                LocationTemplate(
                    template_name="deck_slot",
                    representation_templates={"arm": "arm_repr"},
                    version="1.0.0",
                ),
            ],
            training=[
                RepresentationTrainingEntry(
                    location_name="slot_1",
                    node_name="robotarm_1",
                    overrides={"position": [1, 2, 3]},
                ),
            ],
            locations=[
                Location(
                    location_name="slot_1",
                    description="First deck slot",
                ),
            ],
        )

        yaml_path = tmp_path / "locations.yaml"
        yaml_path.write_text(yaml.dump(config.model_dump(mode="json")))

        raw = yaml.safe_load(yaml_path.read_text())
        restored = LabLocationConfig.model_validate(raw)

        assert len(restored.representation_templates) == 1
        assert restored.representation_templates[0].template_name == "arm_repr"
        assert len(restored.location_templates) == 1
        assert restored.location_templates[0].template_name == "deck_slot"
        assert len(restored.training) == 1
        assert restored.training[0].location_name == "slot_1"
        assert restored.training[0].node_name == "robotarm_1"
        assert len(restored.locations) == 1
        assert restored.locations[0].location_name == "slot_1"


class TestLabConfigFileSetting:
    """Tests for the lab_config_file field on LocationManagerSettings."""

    def test_default_lab_config_file(self):
        """lab_config_file defaults to 'locations.yaml'."""
        settings = LocationManagerSettings(enable_registry_resolution=False)
        assert settings.lab_config_file == "locations.yaml"

    def test_lab_config_file_override(self):
        """lab_config_file can be overridden."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            lab_config_file="custom_locations.yaml",
        )
        assert settings.lab_config_file == "custom_locations.yaml"

    def test_lab_config_file_none(self):
        """lab_config_file can be set to None to disable."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            lab_config_file=None,
        )
        assert settings.lab_config_file is None
