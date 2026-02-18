"""Unit tests for E.3 settings consolidation: structural config overrides."""

import warnings
from typing import Optional

from madsci.common.types.location_types import (
    LocationDefinition,
    LocationManagerDefinition,
    LocationManagerSettings,
    LocationTransferCapabilities,
)
from madsci.common.types.resource_types.definitions import (
    ResourceManagerDefinition,
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            definition = WorkcellManagerDefinition(
                name="Test Workcell",
                nodes={"original_node": AnyUrl("http://localhost:3000/")},
            )
        settings_nodes: Optional[dict] = None

        if settings_nodes is not None:
            definition.nodes = settings_nodes

        assert "original_node" in definition.nodes


class TestLocationSettingsInline:
    """Test LocationManagerSettings inline data fields."""

    def test_locations_none_by_default(self) -> None:
        """locations should be None by default."""
        settings = LocationManagerSettings()
        assert settings.locations is None

    def test_transfer_capabilities_none_by_default(self) -> None:
        """transfer_capabilities should be None by default."""
        settings = LocationManagerSettings()
        assert settings.transfer_capabilities is None

    def test_locations_can_be_set(self) -> None:
        """Should be able to set locations inline."""
        loc = LocationDefinition(location_name="test_loc")
        settings = LocationManagerSettings(locations=[loc])
        assert settings.locations is not None
        assert len(settings.locations) == 1
        assert settings.locations[0].location_name == "test_loc"

    def test_locations_override_logic(self) -> None:
        """Settings locations should be usable to override definition locations."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            definition = LocationManagerDefinition(
                name="Test Location Manager",
                locations=[LocationDefinition(location_name="old_loc")],
            )
        settings_locations = [LocationDefinition(location_name="new_loc")]

        # Simulate the override logic
        if settings_locations is not None:
            definition.locations = settings_locations

        assert len(definition.locations) == 1
        assert definition.locations[0].location_name == "new_loc"

    def test_transfer_capabilities_can_be_set(self) -> None:
        """Should be able to set transfer_capabilities inline."""
        tc = LocationTransferCapabilities(
            transfer_templates=[
                {
                    "node_name": "robot1",
                    "action": "transfer",
                    "source_argument_name": "src",
                    "target_argument_name": "tgt",
                }
            ]
        )
        settings = LocationManagerSettings(transfer_capabilities=tc)
        assert settings.transfer_capabilities is not None
        assert len(settings.transfer_capabilities.transfer_templates) == 1


class TestResourceSettingsInline:
    """Test ResourceManagerSettings inline default_templates field."""

    def test_default_templates_none_by_default(self) -> None:
        """default_templates should be None by default."""
        settings = ResourceManagerSettings()
        assert settings.default_templates is None

    def test_default_templates_can_be_set(self) -> None:
        """Should be able to set default_templates inline."""
        template = TemplateDefinition(
            template_name="test_template",
            description="A test template",
            base_resource={
                "base_type": "resource",
                "resource_name": "test",
                "resource_class": "test_class",
            },
        )
        settings = ResourceManagerSettings(default_templates=[template])
        assert settings.default_templates is not None
        assert len(settings.default_templates) == 1
        assert settings.default_templates[0].template_name == "test_template"

    def test_none_default_templates_preserve_definition(self) -> None:
        """When settings.default_templates is None, definition should be preserved."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            definition = ResourceManagerDefinition(
                default_templates=[
                    TemplateDefinition(
                        template_name="original",
                        base_resource={
                            "base_type": "resource",
                            "resource_name": "orig",
                            "resource_class": "orig_class",
                        },
                    )
                ],
            )
        settings_templates = None

        if settings_templates is not None:
            definition.default_templates = settings_templates

        assert len(definition.default_templates) == 1
        assert definition.default_templates[0].template_name == "original"
