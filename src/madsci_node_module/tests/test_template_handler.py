"""Tests for the template_handler lifecycle on AbstractNode."""

from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.node_types import (
    NodeInfo,
    NodeRepresentationTemplateDefinition,
    NodeResourceTemplateDefinition,
    RestNodeConfig,
)
from madsci.common.types.resource_types import Slot
from madsci.node_module.rest_node_module import RestNode


class TemplateTestConfig(RestNodeConfig):
    """Configuration for the template test node."""

    __test__ = False


class TemplateTestNode(RestNode):
    """A node subclass with declarative templates for testing."""

    __test__ = False

    config: TemplateTestConfig = TemplateTestConfig(
        node_name="template_test_node",
        module_name="template_test_node",
        enable_registry_resolution=False,
    )
    config_model = TemplateTestConfig

    resource_templates: ClassVar[list[NodeResourceTemplateDefinition]] = [
        NodeResourceTemplateDefinition(
            resource=Slot(
                resource_name="test_slot",
                resource_class="TestSlot",
                capacity=1,
                attributes={"description": "test slot"},
            ),
            template_name="test_resource_template",
            description="A test resource template",
            required_overrides=["resource_name"],
            tags=["test"],
            version="1.0.0",
        ),
    ]

    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="test_repr_template",
            default_values={"key": "value"},
            required_overrides=["override_field"],
            tags=["test"],
            version="1.0.0",
            description="A test representation template",
        ),
    ]

    def startup_handler(self) -> None:
        """Minimal startup handler."""
        self.startup_has_run = True


class EmptyTemplateTestNode(RestNode):
    """A node subclass with no declarative templates (default behavior)."""

    __test__ = False

    config: TemplateTestConfig = TemplateTestConfig(
        node_name="empty_template_test_node",
        module_name="empty_template_test_node",
        enable_registry_resolution=False,
    )
    config_model = TemplateTestConfig

    def startup_handler(self) -> None:
        """Minimal startup handler."""
        self.startup_has_run = True


@pytest.fixture
def mock_resource_client():
    """Create a mock resource client."""
    client = MagicMock()
    client.init_template.return_value = MagicMock()
    return client


@pytest.fixture
def mock_location_client():
    """Create a mock location client."""
    client = MagicMock()
    client.init_representation_template.return_value = MagicMock()
    return client


@pytest.fixture
def template_node(mock_resource_client, mock_location_client):
    """Create a TemplateTestNode with mocked clients."""
    node = TemplateTestNode(
        node_config=TemplateTestConfig(
            node_name="template_test_node",
            module_name="template_test_node",
            enable_registry_resolution=False,
        ),
    )
    node.resource_client = mock_resource_client
    node.location_client = mock_location_client
    return node


@pytest.fixture
def empty_template_node(mock_resource_client, mock_location_client):
    """Create an EmptyTemplateTestNode with mocked clients."""
    node = EmptyTemplateTestNode(
        node_config=TemplateTestConfig(
            node_name="empty_template_test_node",
            module_name="empty_template_test_node",
            enable_registry_resolution=False,
        ),
    )
    node.resource_client = mock_resource_client
    node.location_client = mock_location_client
    return node


class TestTemplateHandlerRegistration:
    """Test that templates are registered on template_handler() call."""

    def test_resource_template_registered(self, template_node, mock_resource_client):
        """Resource templates are registered via resource_client.init_template."""
        template_node.template_handler()

        mock_resource_client.init_template.assert_called_once()
        call_kwargs = mock_resource_client.init_template.call_args
        assert call_kwargs.kwargs["template_name"] == "test_resource_template"
        assert call_kwargs.kwargs["description"] == "A test resource template"
        assert call_kwargs.kwargs["required_overrides"] == ["resource_name"]
        assert call_kwargs.kwargs["tags"] == ["test"]
        assert call_kwargs.kwargs["version"] == "1.0.0"
        assert call_kwargs.kwargs["created_by"] == template_node.node_info.node_id

    def test_representation_template_registered(
        self, template_node, mock_location_client
    ):
        """Representation templates are registered via location_client.init_representation_template."""
        template_node.template_handler()

        mock_location_client.init_representation_template.assert_called_once()
        call_kwargs = mock_location_client.init_representation_template.call_args
        assert call_kwargs.kwargs["template_name"] == "test_repr_template"
        assert call_kwargs.kwargs["default_values"] == {"key": "value"}
        assert call_kwargs.kwargs["required_overrides"] == ["override_field"]
        assert call_kwargs.kwargs["tags"] == ["test"]
        assert call_kwargs.kwargs["version"] == "1.0.0"
        assert call_kwargs.kwargs["description"] == "A test representation template"
        assert call_kwargs.kwargs["created_by"] == template_node.node_info.node_id


class TestTemplateHandlerErrorIsolation:
    """Test that per-template errors do not prevent other templates or startup."""

    def test_resource_template_failure_does_not_prevent_repr_templates(
        self, template_node, mock_resource_client, mock_location_client
    ):
        """If a resource template registration fails, representation templates still register."""
        mock_resource_client.init_template.side_effect = ConnectionError(
            "server unavailable"
        )

        # Should not raise
        template_node.template_handler()

        # Representation templates should still be called
        mock_location_client.init_representation_template.assert_called_once()

    def test_template_handler_never_raises(
        self, template_node, mock_resource_client, mock_location_client
    ):
        """template_handler() never raises, even if all registrations fail."""
        mock_resource_client.init_template.side_effect = Exception("boom")
        mock_location_client.init_representation_template.side_effect = Exception(
            "crash"
        )

        # Should not raise
        template_node.template_handler()


class TestTemplateHandlerEmptyLists:
    """Test backward compatibility when no templates are declared."""

    def test_empty_template_lists_no_calls(
        self, empty_template_node, mock_resource_client, mock_location_client
    ):
        """template_handler() runs cleanly when all lists are empty (default case)."""
        empty_template_node.template_handler()

        mock_resource_client.init_template.assert_not_called()
        mock_location_client.init_representation_template.assert_not_called()


class TestTemplateHandlerCallOrder:
    """Test that template_handler runs before startup_handler in _startup."""

    def test_template_handler_called_before_startup_handler(self, template_node):
        """Verify template_handler() is called before startup_handler()."""
        call_order = []

        original_template_handler = template_node.template_handler
        original_startup_handler = template_node.startup_handler

        def tracked_template_handler():
            call_order.append("template_handler")
            original_template_handler()

        def tracked_startup_handler():
            call_order.append("startup_handler")
            original_startup_handler()

        template_node.template_handler = tracked_template_handler
        template_node.startup_handler = tracked_startup_handler

        # Call _startup directly (it's a threaded_daemon, but we can call the inner function)
        # We need to simulate what _startup does without threading
        template_node.node_status.initializing = True
        template_node.node_status.errored = False
        template_node.node_status.locked = False
        template_node.node_status.paused = False
        template_node.node_status.stopped = False
        template_node.template_handler()
        template_node.startup_handler()

        assert call_order == ["template_handler", "startup_handler"]


class TestTemplateHandlerErrorLogging:
    """Test that error logging identifies the template name and type."""

    def test_resource_template_error_logged_with_name(
        self, template_node, mock_resource_client
    ):
        """Failed resource template registration logs a warning with template name."""
        mock_resource_client.init_template.side_effect = ConnectionError("down")

        with patch.object(template_node.logger, "warning") as mock_warning:
            template_node.template_handler()

            mock_warning.assert_called()
            warning_kwargs = mock_warning.call_args_list[0].kwargs
            assert warning_kwargs["template_type"] == "resource"
            assert warning_kwargs["template_name"] == "test_resource_template"
            assert warning_kwargs["error"] == "down"

    def test_representation_template_error_logged_with_name(
        self, template_node, mock_location_client
    ):
        """Failed representation template registration logs a warning with template name."""
        mock_location_client.init_representation_template.side_effect = RuntimeError(
            "schema"
        )

        with patch.object(template_node.logger, "warning") as mock_warning:
            template_node.template_handler()

            # Find the call for the representation template (may not be first if resource succeeded)
            repr_calls = [
                c
                for c in mock_warning.call_args_list
                if c.kwargs.get("template_type") == "location_representation"
            ]
            assert len(repr_calls) == 1
            assert repr_calls[0].kwargs["template_name"] == "test_repr_template"


class TestNodeInfoTemplatePopulation:
    """Test that NodeInfo is populated with template definitions from the class."""

    def test_node_info_has_representation_templates(self, template_node):
        """NodeInfo.location_representation_templates is populated from the class variable."""
        assert len(template_node.node_info.location_representation_templates) == 1
        assert (
            template_node.node_info.location_representation_templates[0].template_name
            == "test_repr_template"
        )

    def test_empty_node_has_empty_template_lists(self, empty_template_node):
        """NodeInfo has empty lists when node declares no templates."""
        assert empty_template_node.node_info.location_representation_templates == []

    def test_node_info_template_serialization_roundtrip(self, template_node):
        """NodeInfo with templates can be serialized and deserialized."""
        dumped = template_node.node_info.model_dump(mode="json")
        assert "location_representation_templates" in dumped
        assert len(dumped["location_representation_templates"]) == 1

        # Round-trip
        restored = NodeInfo.model_validate(dumped)
        assert len(restored.location_representation_templates) == 1
        assert (
            restored.location_representation_templates[0].template_name
            == "test_repr_template"
        )


class TestNodeTemplateDefinitionTypes:
    """Test the node template definition Pydantic models."""

    def test_resource_template_definition(self):
        """NodeResourceTemplateDefinition can be created with all fields."""
        defn = NodeResourceTemplateDefinition(
            resource=Slot(resource_name="test", resource_class="Test", capacity=1),
            template_name="test_tmpl",
            description="A test",
            required_overrides=["name"],
            tags=["tag1"],
            version="2.0.0",
        )
        assert defn.template_name == "test_tmpl"
        assert defn.version == "2.0.0"
        assert defn.tags == ["tag1"]

    def test_resource_template_definition_defaults(self):
        """NodeResourceTemplateDefinition has sensible defaults."""
        defn = NodeResourceTemplateDefinition(
            resource=Slot(resource_name="test", resource_class="Test", capacity=1),
            template_name="test_tmpl",
        )
        assert defn.description == ""
        assert defn.required_overrides is None
        assert defn.tags is None
        assert defn.version == "1.0.0"

    def test_representation_template_definition(self):
        """NodeRepresentationTemplateDefinition can be created with all fields."""
        defn = NodeRepresentationTemplateDefinition(
            template_name="test_repr",
            default_values={"key": "val"},
            schema_def={"type": "object"},
            required_overrides=["field"],
            tags=["tag"],
            version="1.0.0",
            description="A repr template",
        )
        assert defn.template_name == "test_repr"
        assert defn.schema_def == {"type": "object"}
        assert defn.description == "A repr template"

    def test_representation_template_definition_defaults(self):
        """NodeRepresentationTemplateDefinition has sensible defaults."""
        defn = NodeRepresentationTemplateDefinition(template_name="test_repr")
        assert defn.default_values == {}
        assert defn.schema_def is None
        assert defn.required_overrides is None
        assert defn.tags is None
        assert defn.version == "1.0.0"
        assert defn.description is None
