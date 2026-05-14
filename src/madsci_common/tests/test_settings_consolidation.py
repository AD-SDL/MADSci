"""Unit tests for E.3 settings consolidation: structural config overrides."""

import warnings
from typing import Optional

from madsci.common.types.location_types import (
    LocationManagerSettings,
    LocationTransferCapabilities,
)
from madsci.common.types.resource_types.definitions import (
    ResourceManagerDefinition,
    ResourceManagerSettings,
    TemplateDefinition,
)
from madsci.common.types.workcell_types import (
    WorkcellInfo,
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

    def test_settings_nodes_override_workcell_info(self) -> None:
        """When settings.nodes is set, it should override workcell info nodes."""
        info = WorkcellInfo(
            name="Test Workcell",
            nodes={"old_node": AnyUrl("http://localhost:3000/")},
        )
        settings_nodes = {"new_node": AnyUrl("http://localhost:4000/")}

        # Simulate the override logic
        if settings_nodes is not None:
            info.nodes = settings_nodes

        assert "new_node" in info.nodes
        assert "old_node" not in info.nodes

    def test_none_settings_nodes_preserve_workcell_info(self) -> None:
        """When settings.nodes is None, workcell info nodes should be preserved."""
        info = WorkcellInfo(
            name="Test Workcell",
            nodes={"original_node": AnyUrl("http://localhost:3000/")},
        )
        settings_nodes: Optional[dict] = None

        if settings_nodes is not None:
            info.nodes = settings_nodes

        assert "original_node" in info.nodes


class TestLocationSettingsInline:
    """Test LocationManagerSettings inline data fields."""

    def test_transfer_capabilities_none_by_default(self) -> None:
        """transfer_capabilities should be None by default."""
        settings = LocationManagerSettings()
        assert settings.transfer_capabilities is None

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
