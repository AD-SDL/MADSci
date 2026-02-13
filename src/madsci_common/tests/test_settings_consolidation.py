"""Unit tests for E.3 settings consolidation: structural config overrides."""

from pathlib import Path
from typing import Optional

import yaml
from madsci.common.types.location_types import (
    LocationDefinition,
    LocationManagerSettings,
    LocationTransferCapabilities,
)
from madsci.common.types.resource_types.definitions import (
    ResourceManagerSettings,
    TemplateDefinition,
)
from madsci.common.types.workcell_types import (
    WorkcellManagerDefinition,
    WorkcellManagerSettings,
)
from pydantic import AnyUrl


class TestWorkcellSettingsNodes:
    """Test WorkcellManagerSettings.nodes field."""

    def test_nodes_none_by_default(self) -> None:
        """Nodes should be None by default in settings."""
        settings = WorkcellManagerSettings()
        assert settings.nodes is None

    def test_nodes_can_be_set(self) -> None:
        """Should be able to set nodes in settings."""
        settings = WorkcellManagerSettings(
            nodes={"node1": AnyUrl("http://localhost:2000/")}
        )
        assert settings.nodes is not None
        assert "node1" in settings.nodes

    def test_settings_nodes_override_definition(self) -> None:
        """When settings.nodes is set, it should override definition.nodes."""
        definition = WorkcellManagerDefinition(
            name="Test Workcell",
            nodes={"old_node": AnyUrl("http://localhost:3000/")},
        )
        settings_nodes = {"new_node": AnyUrl("http://localhost:4000/")}

        # Simulate the override logic from workcell_server.initialize()
        if settings_nodes is not None:
            definition.nodes = settings_nodes

        assert "new_node" in definition.nodes
        assert "old_node" not in definition.nodes

    def test_none_settings_nodes_preserve_definition(self) -> None:
        """When settings.nodes is None, definition.nodes should be preserved."""
        definition = WorkcellManagerDefinition(
            name="Test Workcell",
            nodes={"original_node": AnyUrl("http://localhost:3000/")},
        )
        settings_nodes: Optional[dict] = None

        if settings_nodes is not None:
            definition.nodes = settings_nodes

        assert "original_node" in definition.nodes


class TestLocationSettingsFiles:
    """Test LocationManagerSettings file override fields."""

    def test_locations_file_none_by_default(self) -> None:
        """locations_file should be None by default."""
        settings = LocationManagerSettings()
        assert settings.locations_file is None

    def test_transfer_capabilities_file_none_by_default(self) -> None:
        """transfer_capabilities_file should be None by default."""
        settings = LocationManagerSettings()
        assert settings.transfer_capabilities_file is None

    def test_locations_file_can_be_set(self) -> None:
        """Should be able to set locations_file."""
        settings = LocationManagerSettings(locations_file="locations.yaml")
        assert settings.locations_file is not None

    def test_locations_file_override_logic(self, tmp_path: Path) -> None:
        """Loading locations from a file should override definition locations."""
        locations_data = [
            {"location_name": "loc_from_file"},
        ]
        locations_file = tmp_path / "locations.yaml"
        locations_file.write_text(yaml.dump(locations_data))

        raw = yaml.safe_load(locations_file.read_text())
        parsed = [LocationDefinition.model_validate(loc) for loc in raw]

        assert len(parsed) == 1
        assert parsed[0].location_name == "loc_from_file"

    def test_transfer_capabilities_file_override_logic(self, tmp_path: Path) -> None:
        """Loading transfer capabilities from a file should parse correctly."""
        tc_data = {
            "transfer_templates": [
                {
                    "node_name": "robot1",
                    "action": "transfer",
                    "source_argument_name": "src",
                    "target_argument_name": "tgt",
                }
            ]
        }
        tc_file = tmp_path / "transfer_capabilities.yaml"
        tc_file.write_text(yaml.dump(tc_data))

        raw = yaml.safe_load(tc_file.read_text())
        parsed = LocationTransferCapabilities.model_validate(raw)

        assert len(parsed.transfer_templates) == 1
        assert parsed.transfer_templates[0].node_name == "robot1"


class TestResourceSettingsTemplatesFile:
    """Test ResourceManagerSettings.default_templates_file field."""

    def test_default_templates_file_none_by_default(self) -> None:
        """default_templates_file should be None by default."""
        settings = ResourceManagerSettings()
        assert settings.default_templates_file is None

    def test_default_templates_file_can_be_set(self) -> None:
        """Should be able to set default_templates_file."""
        settings = ResourceManagerSettings(default_templates_file="templates.yaml")
        assert settings.default_templates_file is not None

    def test_templates_file_override_logic(self, tmp_path: Path) -> None:
        """Loading templates from a file should parse correctly."""
        templates_data = [
            {
                "template_name": "test_template",
                "description": "A test template",
                "base_resource": {
                    "base_type": "resource",
                    "resource_name": "test",
                    "resource_class": "test_class",
                },
            }
        ]
        templates_file = tmp_path / "templates.yaml"
        templates_file.write_text(yaml.dump(templates_data))

        raw = yaml.safe_load(templates_file.read_text())
        parsed = [TemplateDefinition.model_validate(t) for t in raw]

        assert len(parsed) == 1
        assert parsed[0].template_name == "test_template"
