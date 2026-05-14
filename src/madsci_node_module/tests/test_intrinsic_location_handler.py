"""Tests for the intrinsic_location_handler lifecycle on AbstractNode."""

from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.location_types import LocationManagement
from madsci.common.types.node_types import (
    NodeInfo,
    NodeIntrinsicLocationDefinition,
    RestNodeConfig,
)
from madsci.node_module.rest_node_module import RestNode


class IntrinsicLocationTestConfig(RestNodeConfig):
    """Configuration for the intrinsic location test node."""

    __test__ = False


class IntrinsicLocationTestNode(RestNode):
    """A node subclass with intrinsic locations for testing."""

    __test__ = False

    config: IntrinsicLocationTestConfig = IntrinsicLocationTestConfig(
        node_name="intrinsic_loc_test_node",
        module_name="intrinsic_loc_test_node",
        enable_registry_resolution=False,
    )
    config_model = IntrinsicLocationTestConfig

    intrinsic_locations: ClassVar[list[NodeIntrinsicLocationDefinition]] = [
        NodeIntrinsicLocationDefinition(
            location_name="deck_1",
            description="First deck slot",
            representation_template_name="deck_repr",
            representation_overrides={"rows": 8, "cols": 12},
            resource_template_name="plate_resource",
            resource_template_overrides={"capacity": 96},
            allow_transfers=True,
        ),
        NodeIntrinsicLocationDefinition(
            location_name="deck_2",
            description="Second deck slot",
            representation_template_name="deck_repr",
            representation_overrides={"rows": 4, "cols": 6},
            allow_transfers=False,
        ),
    ]

    def startup_handler(self) -> None:
        """Minimal startup handler."""
        self.startup_has_run = True


class EmptyIntrinsicLocationTestNode(RestNode):
    """A node subclass with no intrinsic locations (default behavior)."""

    __test__ = False

    config: IntrinsicLocationTestConfig = IntrinsicLocationTestConfig(
        node_name="empty_intrinsic_loc_node",
        module_name="empty_intrinsic_loc_node",
        enable_registry_resolution=False,
    )
    config_model = IntrinsicLocationTestConfig

    def startup_handler(self) -> None:
        """Minimal startup handler."""
        self.startup_has_run = True


@pytest.fixture
def mock_location_client():
    """Create a mock location client."""
    client = MagicMock()
    client.init_location.return_value = MagicMock()
    return client


@pytest.fixture
def intrinsic_node(mock_location_client):
    """Create an IntrinsicLocationTestNode with mocked clients."""
    node = IntrinsicLocationTestNode(
        node_config=IntrinsicLocationTestConfig(
            node_name="intrinsic_loc_test_node",
            module_name="intrinsic_loc_test_node",
            enable_registry_resolution=False,
        ),
    )
    node.location_client = mock_location_client
    return node


@pytest.fixture
def empty_intrinsic_node(mock_location_client):
    """Create an EmptyIntrinsicLocationTestNode with mocked clients."""
    node = EmptyIntrinsicLocationTestNode(
        node_config=IntrinsicLocationTestConfig(
            node_name="empty_intrinsic_loc_node",
            module_name="empty_intrinsic_loc_node",
            enable_registry_resolution=False,
        ),
    )
    node.location_client = mock_location_client
    return node


def _find_call_by_location(call_args_list, location_name):
    """Helper: find the call whose location_name kwarg matches."""
    return next(c for c in call_args_list if c.kwargs["location_name"] == location_name)


class TestIntrinsicLocationHandlerRegistration:
    """Test that intrinsic locations are registered on intrinsic_location_handler() call."""

    def test_init_location_called_for_each_intrinsic_location(
        self, intrinsic_node, mock_location_client
    ):
        """init_location is called once per intrinsic location definition."""
        intrinsic_node.intrinsic_location_handler()

        assert mock_location_client.init_location.call_count == 2

    def test_location_name_auto_prefixed_with_node_name(
        self, intrinsic_node, mock_location_client
    ):
        """Each location name is prefixed with '{node_name}.'."""
        intrinsic_node.intrinsic_location_handler()

        call_args_list = mock_location_client.init_location.call_args_list
        location_names = [call.kwargs["location_name"] for call in call_args_list]
        assert "intrinsic_loc_test_node.deck_1" in location_names
        assert "intrinsic_loc_test_node.deck_2" in location_names

    def test_managed_by_set_to_node(self, intrinsic_node, mock_location_client):
        """managed_by is set to LocationManagement.NODE for each location."""
        intrinsic_node.intrinsic_location_handler()

        for call in mock_location_client.init_location.call_args_list:
            assert call.kwargs["managed_by"] == LocationManagement.NODE

    def test_owner_has_node_id(self, intrinsic_node, mock_location_client):
        """owner.node_id is set to the node's node_id."""
        intrinsic_node.intrinsic_location_handler()

        for call in mock_location_client.init_location.call_args_list:
            owner = call.kwargs["owner"]
            assert owner.node_id == intrinsic_node.node_info.node_id

    def test_representations_include_node_name_key(
        self, intrinsic_node, mock_location_client
    ):
        """representations dict uses node_name as key with overrides as value."""
        intrinsic_node.intrinsic_location_handler()

        deck_1_call = _find_call_by_location(
            mock_location_client.init_location.call_args_list,
            "intrinsic_loc_test_node.deck_1",
        )
        assert deck_1_call.kwargs["representations"] == {
            "intrinsic_loc_test_node": {"rows": 8, "cols": 12}
        }

    def test_resource_template_fields_passed(
        self, intrinsic_node, mock_location_client
    ):
        """Resource template name and overrides are passed correctly."""
        intrinsic_node.intrinsic_location_handler()

        deck_1_call = _find_call_by_location(
            mock_location_client.init_location.call_args_list,
            "intrinsic_loc_test_node.deck_1",
        )
        assert deck_1_call.kwargs["resource_template_name"] == "plate_resource"
        assert deck_1_call.kwargs["resource_template_overrides"] == {"capacity": 96}

    def test_description_passed(self, intrinsic_node, mock_location_client):
        """Description is forwarded from the definition."""
        intrinsic_node.intrinsic_location_handler()

        deck_1_call = _find_call_by_location(
            mock_location_client.init_location.call_args_list,
            "intrinsic_loc_test_node.deck_1",
        )
        assert deck_1_call.kwargs["description"] == "First deck slot"

    def test_allow_transfers_passed(self, intrinsic_node, mock_location_client):
        """allow_transfers is forwarded from the definition."""
        intrinsic_node.intrinsic_location_handler()

        deck_2_call = _find_call_by_location(
            mock_location_client.init_location.call_args_list,
            "intrinsic_loc_test_node.deck_2",
        )
        assert deck_2_call.kwargs["allow_transfers"] is False


class TestIntrinsicLocationHandlerErrorIsolation:
    """Test that per-location errors do not prevent other locations from registering."""

    def test_first_failure_does_not_prevent_second(
        self, intrinsic_node, mock_location_client
    ):
        """If first location registration fails, second still registers."""
        call_count = 0

        def side_effect(**_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("server unavailable")
            return MagicMock()

        mock_location_client.init_location.side_effect = side_effect

        # Should not raise
        intrinsic_node.intrinsic_location_handler()

        assert mock_location_client.init_location.call_count == 2

    def test_handler_never_raises_even_if_all_fail(
        self, intrinsic_node, mock_location_client
    ):
        """intrinsic_location_handler() never raises, even if all registrations fail."""
        mock_location_client.init_location.side_effect = Exception("boom")

        # Should not raise
        intrinsic_node.intrinsic_location_handler()

    def test_failure_logged_with_location_name(
        self, intrinsic_node, mock_location_client
    ):
        """Failed registration logs a warning with the location name."""
        mock_location_client.init_location.side_effect = ConnectionError("down")

        with patch.object(intrinsic_node.logger, "warning") as mock_warning:
            intrinsic_node.intrinsic_location_handler()

            assert mock_warning.call_count == 2
            for call in mock_warning.call_args_list:
                assert "location_name" in call.kwargs
                assert "error" in call.kwargs


class TestIntrinsicLocationHandlerEmptyList:
    """Test backward compatibility when no intrinsic locations are declared."""

    def test_empty_intrinsic_locations_no_calls(
        self, empty_intrinsic_node, mock_location_client
    ):
        """intrinsic_location_handler() runs cleanly when list is empty (default)."""
        empty_intrinsic_node.intrinsic_location_handler()

        mock_location_client.init_location.assert_not_called()


class TestIntrinsicLocationHandlerCallOrder:
    """Test that intrinsic_location_handler runs between template_handler and startup_handler."""

    def test_intrinsic_location_handler_called_between_template_and_startup(
        self, intrinsic_node
    ):
        """Verify intrinsic_location_handler is called between template_handler and startup_handler."""
        call_order = []

        original_template_handler = intrinsic_node.template_handler
        original_intrinsic_location_handler = intrinsic_node.intrinsic_location_handler
        original_startup_handler = intrinsic_node.startup_handler

        def tracked_template():
            call_order.append("template_handler")
            original_template_handler()

        def tracked_intrinsic():
            call_order.append("intrinsic_location_handler")
            original_intrinsic_location_handler()

        def tracked_startup():
            call_order.append("startup_handler")
            original_startup_handler()

        intrinsic_node.template_handler = tracked_template
        intrinsic_node.intrinsic_location_handler = tracked_intrinsic
        intrinsic_node.startup_handler = tracked_startup

        # Simulate _startup sequence
        intrinsic_node.node_status.initializing = True
        intrinsic_node.node_status.errored = False
        intrinsic_node.node_status.locked = False
        intrinsic_node.node_status.paused = False
        intrinsic_node.node_status.stopped = False
        intrinsic_node.template_handler()
        intrinsic_node.intrinsic_location_handler()
        intrinsic_node.startup_handler()

        assert call_order == [
            "template_handler",
            "intrinsic_location_handler",
            "startup_handler",
        ]


class TestNodeInfoIntrinsicLocationPopulation:
    """Test that NodeInfo is populated with intrinsic location definitions."""

    def test_node_info_has_intrinsic_locations(self, intrinsic_node):
        """NodeInfo.intrinsic_locations is populated from the class variable."""
        assert len(intrinsic_node.node_info.intrinsic_locations) == 2
        names = [
            loc.location_name for loc in intrinsic_node.node_info.intrinsic_locations
        ]
        assert "deck_1" in names
        assert "deck_2" in names

    def test_empty_node_has_empty_intrinsic_locations(self, empty_intrinsic_node):
        """NodeInfo has empty list when node declares no intrinsic locations."""
        assert empty_intrinsic_node.node_info.intrinsic_locations == []

    def test_node_info_intrinsic_locations_are_copies(self, intrinsic_node):
        """NodeInfo intrinsic_locations list is a copy, not a reference to the class variable."""
        intrinsic_node.node_info.intrinsic_locations.append(
            NodeIntrinsicLocationDefinition(
                location_name="extra",
                representation_template_name="extra_repr",
            )
        )
        # Class variable should not be affected
        assert len(IntrinsicLocationTestNode.intrinsic_locations) == 2

    def test_node_info_intrinsic_location_serialization_roundtrip(self, intrinsic_node):
        """NodeInfo with intrinsic_locations can be serialized and deserialized."""
        dumped = intrinsic_node.node_info.model_dump(mode="json")
        assert "intrinsic_locations" in dumped
        assert len(dumped["intrinsic_locations"]) == 2

        # Round-trip
        restored = NodeInfo.model_validate(dumped)
        assert len(restored.intrinsic_locations) == 2
        names = [loc.location_name for loc in restored.intrinsic_locations]
        assert "deck_1" in names
        assert "deck_2" in names
