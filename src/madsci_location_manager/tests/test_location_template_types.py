"""Tests for location template type definitions."""

import pytest
from madsci.common.types.location_types import (
    CreateLocationFromTemplateRequest,
    Location,
    LocationManagerHealth,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from madsci.common.utils import new_ulid_str


class TestLocationRepresentationTemplate:
    """Tests for LocationRepresentationTemplate model."""

    def test_create_with_required_fields(self):
        """Template can be created with just template_name."""
        template = LocationRepresentationTemplate(template_name="test_repr")
        assert template.template_name == "test_repr"
        assert template.template_id  # ULID should be auto-generated
        assert template.default_values == {}
        assert template.required_overrides == []
        assert template.tags == []
        assert template.version == "1.0.0"
        assert template.created_at is not None
        assert template.updated_at is None
        assert template.description is None
        assert template.schema_def is None
        assert template.created_by is None

    def test_create_with_all_fields(self):
        """Template can be created with all fields populated."""
        template_id = new_ulid_str()
        template = LocationRepresentationTemplate(
            template_id=template_id,
            template_name="robotarm_deck_access",
            description="Robot arm deck access representation",
            default_values={"gripper_config": "standard", "max_payload": 2.0},
            schema_def={
                "type": "object",
                "properties": {"position": {"type": "array"}},
            },
            required_overrides=["position"],
            tags=["robot_arm", "deck"],
            created_by="node_123",
            version="2.0.0",
        )
        assert template.template_id == template_id
        assert template.template_name == "robotarm_deck_access"
        assert template.default_values == {
            "gripper_config": "standard",
            "max_payload": 2.0,
        }
        assert template.required_overrides == ["position"]
        assert template.tags == ["robot_arm", "deck"]
        assert template.version == "2.0.0"

    def test_ulid_validation(self):
        """Template ID must be a valid ULID."""
        template = LocationRepresentationTemplate(template_name="test")
        # Auto-generated ID should be valid
        assert len(template.template_id) == 26

    def test_serialization_roundtrip(self):
        """Template can be serialized and deserialized."""
        template = LocationRepresentationTemplate(
            template_name="test_repr",
            default_values={"key": "value"},
            required_overrides=["field1"],
        )
        data = template.model_dump(mode="json")
        restored = LocationRepresentationTemplate.model_validate(data)
        assert restored.template_name == template.template_name
        assert restored.template_id == template.template_id
        assert restored.default_values == template.default_values


class TestLocationTemplate:
    """Tests for LocationTemplate model."""

    def test_create_with_required_fields(self):
        """Template can be created with just template_name."""
        template = LocationTemplate(template_name="ot2_deck_slot")
        assert template.template_name == "ot2_deck_slot"
        assert template.template_id  # ULID auto-generated
        assert template.representation_templates == {}
        assert template.resource_template_name is None
        assert template.default_allow_transfers is True
        assert template.version == "1.0.0"

    def test_create_with_all_fields(self):
        """Template can be created with all fields."""
        template = LocationTemplate(
            template_name="ot2_deck_slot",
            description="OT-2 deck slot",
            resource_template_name="location_container",
            resource_template_overrides={"capacity": 2},
            representation_templates={
                "deck_controller": "lh_deck_repr",
                "transfer_arm": "robotarm_deck_access",
            },
            default_allow_transfers=False,
            tags=["ot2", "deck"],
            created_by="admin",
            version="1.0.0",
        )
        assert template.representation_templates == {
            "deck_controller": "lh_deck_repr",
            "transfer_arm": "robotarm_deck_access",
        }
        assert template.resource_template_name == "location_container"
        assert template.default_allow_transfers is False

    def test_serialization_roundtrip(self):
        """Template can be serialized and deserialized."""
        template = LocationTemplate(
            template_name="test_template",
            representation_templates={"role": "repr_template"},
        )
        data = template.model_dump(mode="json")
        restored = LocationTemplate.model_validate(data)
        assert restored.template_name == template.template_name
        assert restored.representation_templates == template.representation_templates


class TestCreateLocationFromTemplateRequest:
    """Tests for CreateLocationFromTemplateRequest model."""

    def test_create_with_required_fields(self):
        """Request can be created with required fields."""
        request = CreateLocationFromTemplateRequest(
            location_name="lh1.deck_1",
            template_name="ot2_deck_slot",
        )
        assert request.location_name == "lh1.deck_1"
        assert request.template_name == "ot2_deck_slot"
        assert request.node_bindings == {}
        assert request.representation_overrides == {}
        assert request.resource_template_overrides is None
        assert request.description is None
        assert request.allow_transfers is None

    def test_create_with_all_fields(self):
        """Request can be created with all fields."""
        request = CreateLocationFromTemplateRequest(
            location_name="lh1.deck_1",
            template_name="ot2_deck_slot",
            node_bindings={"deck_controller": "lh1", "transfer_arm": "arm1"},
            representation_overrides={
                "deck_controller": {"deck_position": 1},
                "transfer_arm": {"position": [10, 15, 5]},
            },
            resource_template_overrides={"capacity": 2},
            description="First deck slot",
            allow_transfers=False,
        )
        assert request.node_bindings == {
            "deck_controller": "lh1",
            "transfer_arm": "arm1",
        }
        assert request.representation_overrides["deck_controller"] == {
            "deck_position": 1
        }
        assert request.allow_transfers is False

    def test_validation_missing_required(self):
        """Request fails without required fields."""
        with pytest.raises(ValueError):
            CreateLocationFromTemplateRequest()


class TestLocationTraceabilityFields:
    """Tests for new traceability fields on the Location model."""

    def test_location_without_new_fields_validates(self):
        """Existing Location data without new fields still validates (backwards compat)."""
        location = Location(
            location_name="test_loc",
            location_id=new_ulid_str(),
            description="A test location",
        )
        assert location.location_template_name is None
        assert location.node_bindings is None

    def test_location_with_traceability_fields(self):
        """Location can include template traceability fields."""
        location = Location(
            location_name="test_loc",
            location_id=new_ulid_str(),
            location_template_name="ot2_deck_slot",
            node_bindings={"deck_controller": "lh1", "transfer_arm": "arm1"},
        )
        assert location.location_template_name == "ot2_deck_slot"
        assert location.node_bindings == {
            "deck_controller": "lh1",
            "transfer_arm": "arm1",
        }

    def test_location_serialization_with_new_fields(self):
        """Location with new fields can be serialized and deserialized."""
        location = Location(
            location_name="test_loc",
            location_id=new_ulid_str(),
            location_template_name="my_template",
            node_bindings={"role": "node"},
        )
        data = location.model_dump(mode="json")
        restored = Location.model_validate(data)
        assert restored.location_template_name == "my_template"
        assert restored.node_bindings == {"role": "node"}

    def test_location_from_dict_without_new_fields(self):
        """Location from dict without new fields (old format) still works."""
        data = {
            "location_name": "old_loc",
            "location_id": new_ulid_str(),
            "representations": {"node1": {"key": "val"}},
            "resource_template_name": "container",
        }
        location = Location.model_validate(data)
        assert location.location_template_name is None
        assert location.node_bindings is None


class TestLocationManagerSettingsReconciliation:
    """Tests for reconciliation config fields on LocationManagerSettings."""

    def test_defaults(self):
        """Default reconciliation settings."""
        settings = LocationManagerSettings(enable_registry_resolution=False)
        assert settings.reconciliation_interval_seconds == 30.0
        assert settings.reconciliation_enabled is True

    def test_custom_values(self):
        """Custom reconciliation settings."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            reconciliation_interval_seconds=60.0,
            reconciliation_enabled=False,
        )
        assert settings.reconciliation_interval_seconds == 60.0
        assert settings.reconciliation_enabled is False


class TestLocationManagerHealthTemplateFields:
    """Tests for new template count fields on LocationManagerHealth."""

    def test_defaults(self):
        """Default health has zero template counts."""
        health = LocationManagerHealth()
        assert health.num_representation_templates == 0
        assert health.num_location_templates == 0
        assert health.num_unresolved_locations == 0

    def test_with_counts(self):
        """Health with template counts."""
        health = LocationManagerHealth(
            num_representation_templates=5,
            num_location_templates=3,
            num_unresolved_locations=2,
        )
        assert health.num_representation_templates == 5
        assert health.num_location_templates == 3
        assert health.num_unresolved_locations == 2
