"""Basic composition tests for TUI screens.

These tests verify that screens can be instantiated and composed without
errors. They use Textual's async test runner to push screens onto a minimal
host app and confirm no exception is raised.
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import patch

import pytest

textual = pytest.importorskip("textual")

from textual.app import App  # noqa: E402


@pytest.fixture
def mock_app_class():
    """Return a minimal App subclass with service_urls for testing screens."""

    class TestApp(App):
        service_urls: ClassVar[dict] = {
            "lab_manager": "http://localhost:8000/",
            "event_manager": "http://localhost:8001/",
            "experiment_manager": "http://localhost:8002/",
            "resource_manager": "http://localhost:8003/",
            "data_manager": "http://localhost:8004/",
            "workcell_manager": "http://localhost:8005/",
            "location_manager": "http://localhost:8006/",
        }

    return TestApp


@pytest.mark.asyncio
async def test_data_browser_composes(mock_app_class) -> None:
    """DataBrowserScreen composes without error."""
    from madsci.client.cli.tui.screens.data_browser import DataBrowserScreen

    app = mock_app_class()
    async with app.run_test() as pilot:
        await pilot.app.push_screen(DataBrowserScreen())
        assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_experiments_screen_composes(mock_app_class) -> None:
    """ExperimentsScreen composes without error."""
    from madsci.client.cli.tui.screens.experiments import ExperimentsScreen

    app = mock_app_class()
    async with app.run_test() as pilot:
        await pilot.app.push_screen(ExperimentsScreen())
        assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_locations_screen_composes(mock_app_class) -> None:
    """LocationsScreen composes without error."""
    from madsci.client.cli.tui.screens.locations import LocationsScreen

    app = mock_app_class()
    async with app.run_test() as pilot:
        await pilot.app.push_screen(LocationsScreen())
        assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_resources_screen_composes(mock_app_class) -> None:
    """ResourcesScreen composes without error."""
    from madsci.client.cli.tui.screens.resources import ResourcesScreen

    app = mock_app_class()
    with patch(
        "madsci.client.resource_client.ResourceClient.__init__", return_value=None
    ):
        async with app.run_test() as pilot:
            await pilot.app.push_screen(ResourcesScreen())
            assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_dashboard_screen_composes(mock_app_class) -> None:
    """DashboardScreen composes without error."""
    from madsci.client.cli.tui.screens.dashboard import DashboardScreen

    app = mock_app_class()
    async with app.run_test() as pilot:
        await pilot.app.push_screen(DashboardScreen())
        assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_locations_screen_has_managed_by_column(mock_app_class) -> None:
    """LocationsScreen table should include a 'Managed By' column."""
    from madsci.client.cli.tui.screens.locations import LocationsScreen

    app = mock_app_class()
    async with app.run_test() as pilot:
        screen = LocationsScreen()
        await pilot.app.push_screen(screen)
        from textual.widgets import DataTable

        table = screen.query_one("#locations-table", DataTable)
        column_labels = [col.label.plain for col in table.columns.values()]
        assert "Managed By" in column_labels


def test_locations_detail_panel_shows_managed_by() -> None:
    """LocationsScreen detail panel should display Managed By field."""
    from madsci.client.cli.tui.screens.locations import _build_general_section
    from madsci.common.types.location_types import Location, LocationManagement

    loc = Location(location_name="test", managed_by=LocationManagement.NODE)
    section = _build_general_section(loc)
    assert "Managed By" in section.fields
    assert section.fields["Managed By"] == "NODE"


def test_locations_detail_panel_shows_owner() -> None:
    """LocationsScreen detail panel should display Owner field."""
    from madsci.client.cli.tui.screens.locations import _build_general_section
    from madsci.common.types.auth_types import OwnershipInfo
    from madsci.common.types.location_types import Location, LocationManagement
    from madsci.common.utils import new_ulid_str

    node_id = new_ulid_str()
    loc = Location(
        location_name="test",
        managed_by=LocationManagement.NODE,
        owner=OwnershipInfo(node_id=node_id),
    )
    section = _build_general_section(loc)
    assert "Owner" in section.fields
    assert node_id in section.fields["Owner"]


def test_dashboard_no_httpx_import() -> None:
    """RecentEventsPanel should use EventClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.dashboard")
    source = inspect.getsource(mod)

    # The module should not import httpx
    assert "import httpx" not in source, (
        "dashboard.py still imports httpx; should use EventClient instead"
    )

    # The module should import EventClient
    assert "EventClient" in source, "dashboard.py should import and use EventClient"


def test_recent_events_panel_has_event_client_field() -> None:
    """RecentEventsPanel should have a lazy _event_client field."""
    from madsci.client.cli.tui.screens.dashboard import RecentEventsPanel

    panel = RecentEventsPanel()
    assert hasattr(panel, "_event_client"), (
        "RecentEventsPanel should have a _event_client field"
    )
    assert panel._event_client is None, "_event_client should be None until first use"


def test_extract_message_with_event_model() -> None:
    """_extract_message should work with Event model instances."""
    from madsci.client.cli.tui.screens.dashboard import _extract_message
    from madsci.common.types.event_types import Event

    event = Event(event_data={"message": "Something happened"})
    result = _extract_message(event)
    assert "Something happened" in result


def test_format_level_with_event_log_level_enum() -> None:
    """_format_level should handle EventLogLevel enum values."""
    from madsci.client.cli.tui.screens.dashboard import _format_level
    from madsci.common.types.event_types import EventLogLevel

    assert _format_level(EventLogLevel.INFO) == "INFO"
    assert _format_level(EventLogLevel.ERROR) == "ERROR"
    assert _format_level(EventLogLevel.DEBUG) == "DEBUG"
    assert _format_level(EventLogLevel.WARNING) in ("WARN", "WARNING")
    assert _format_level(EventLogLevel.CRITICAL) in ("CRIT", "CRITICAL")


# ---------------------------------------------------------------------------
# Location screen migration tests
# ---------------------------------------------------------------------------


def test_locations_no_httpx_import() -> None:
    """locations.py should use LocationClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.locations")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "locations.py still imports httpx; should use LocationClient instead"
    )
    assert "get_async_client" not in source, (
        "locations.py still uses get_async_client; should use LocationClient instead"
    )
    assert "LocationClient" in source, (
        "locations.py should import and use LocationClient"
    )


def test_transfer_graph_no_httpx_import() -> None:
    """transfer_graph.py should use LocationClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.transfer_graph")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "transfer_graph.py still imports httpx; should use LocationClient instead"
    )
    assert "LocationClient" in source, (
        "transfer_graph.py should import and use LocationClient"
    )


def test_locations_screen_has_location_client_field() -> None:
    """LocationsScreen should have a lazy _location_client field."""
    from madsci.client.cli.tui.screens.locations import LocationsScreen

    screen = LocationsScreen()
    assert hasattr(screen, "_location_client"), (
        "LocationsScreen should have a _location_client field"
    )
    assert screen._location_client is None, (
        "_location_client should be None until first use"
    )


def test_locations_data_stores_location_models() -> None:
    """LocationsScreen.locations_data should be typed for Location models."""
    from madsci.client.cli.tui.screens.locations import LocationsScreen

    screen = LocationsScreen()
    # The dict should be empty initially and typed for Location models
    assert isinstance(screen.locations_data, dict)
    assert len(screen.locations_data) == 0


def test_matches_filter_with_location_model() -> None:
    """_matches_filter should accept a Location model instance."""
    from madsci.client.cli.tui.screens.locations import _matches_filter
    from madsci.common.types.location_types import Location

    loc = Location(location_name="test_robot_arm")
    assert _matches_filter(loc, "") is True
    assert _matches_filter(loc, "robot") is True
    assert _matches_filter(loc, "nonexistent") is False


def test_build_general_section_with_location_model() -> None:
    """_build_general_section should accept a Location model instance."""
    from madsci.client.cli.tui.screens.locations import _build_general_section
    from madsci.common.types.location_types import Location

    loc = Location(
        location_name="test_location",
        description="A test location",
        allow_transfers=False,
        location_template_name="my_template",
    )
    section = _build_general_section(loc)
    assert section.title == "General"
    assert section.fields["Name"] == "test_location"
    assert section.fields["ID"] == loc.location_id
    assert section.fields["Allow Transfers"] == "False"
    assert section.fields["Template"] == "my_template"
    assert "A test location" in section.fields.get("Description", "")


def test_build_resource_section_with_location_model() -> None:
    """_build_resource_section should accept a Location model instance."""
    from madsci.client.cli.tui.screens.locations import _build_resource_section
    from madsci.common.types.location_types import Location

    loc = Location(location_name="test_loc", resource_id="res-123")
    section = _build_resource_section(loc)
    assert section.title == "Resource"
    assert section.fields["Resource ID"] == "res-123"


def test_build_representations_section_with_location_model() -> None:
    """_build_representations_section should accept a Location model."""
    from madsci.client.cli.tui.screens.locations import _build_representations_section
    from madsci.common.types.location_types import Location

    loc = Location(
        location_name="test_loc",
        representations={"arm_node": "joint_angles_123"},
    )
    section = _build_representations_section(loc)
    assert section is not None
    assert section.title == "Representations"
    assert "arm_node" in section.fields

    # No representations should return None
    loc_empty = Location(location_name="test_loc_empty", representations={})
    assert _build_representations_section(loc_empty) is None


def test_build_node_bindings_section_with_location_model() -> None:
    """_build_node_bindings_section should accept a Location model."""
    from madsci.client.cli.tui.screens.locations import _build_node_bindings_section
    from madsci.common.types.location_types import Location

    loc = Location(
        location_name="test_loc",
        node_bindings={"gripper": "robot_arm_1"},
    )
    section = _build_node_bindings_section(loc)
    assert section is not None
    assert section.title == "Node Bindings"
    assert section.fields["gripper"] == "robot_arm_1"

    # No bindings should return None
    loc_no_bindings = Location(location_name="test_loc_2", node_bindings=None)
    assert _build_node_bindings_section(loc_no_bindings) is None


def test_build_reservation_section_with_location_model() -> None:
    """_build_reservation_section should accept a Location model."""
    from madsci.client.cli.tui.screens.locations import _build_reservation_section
    from madsci.common.types.location_types import Location

    # No reservation should return None
    loc = Location(location_name="test_loc")
    assert _build_reservation_section(loc) is None


def test_transfer_graph_screen_accepts_location_client() -> None:
    """TransferGraphScreen should accept a LocationClient instance."""
    from madsci.client.cli.tui.screens.transfer_graph import TransferGraphScreen
    from madsci.client.location_client import LocationClient

    client = LocationClient(location_server_url="http://localhost:8006")
    screen = TransferGraphScreen(location_client=client)
    assert screen._location_client is client


# ---------------------------------------------------------------------------
# Resource screen migration tests
# ---------------------------------------------------------------------------


def test_resources_no_httpx_import() -> None:
    """resources.py should use ResourceClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.resources")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "resources.py still imports httpx; should use ResourceClient instead"
    )
    assert "get_async_client" not in source, (
        "resources.py still uses get_async_client; should use ResourceClient instead"
    )
    assert "ResourceClient" in source, (
        "resources.py should import and use ResourceClient"
    )


def test_resource_tree_no_httpx_import() -> None:
    """resource_tree.py should use ResourceClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.resource_tree")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "resource_tree.py still imports httpx; should use ResourceClient instead"
    )
    assert "ResourceClient" in source, (
        "resource_tree.py should import and use ResourceClient"
    )


def test_resources_screen_has_resource_client_field() -> None:
    """ResourcesScreen should have a lazy _resource_client field."""
    from madsci.client.cli.tui.screens.resources import ResourcesScreen

    screen = ResourcesScreen()
    assert hasattr(screen, "_resource_client"), (
        "ResourcesScreen should have a _resource_client field"
    )
    assert screen._resource_client is None, (
        "_resource_client should be None until first use"
    )


def test_resources_data_stores_resource_models() -> None:
    """ResourcesScreen.resources_data should be typed for Resource models."""
    from madsci.client.cli.tui.screens.resources import ResourcesScreen

    screen = ResourcesScreen()
    # The dict should be empty initially and typed for Resource models
    assert isinstance(screen.resources_data, dict)
    assert len(screen.resources_data) == 0


def test_matches_filter_with_resource_model() -> None:
    """_matches_filter should accept a Resource model instance."""
    from madsci.client.cli.tui.screens.resources import _matches_filter
    from madsci.common.types.resource_types import Resource

    res = Resource(resource_name="test_vial", base_type="resource")
    assert _matches_filter(res, "", {}) is True
    assert _matches_filter(res, "vial", {}) is True
    assert _matches_filter(res, "nonexistent", {}) is False


def test_matches_filter_with_type_filter_and_resource_model() -> None:
    """_matches_filter type filter should work with Resource model."""
    from madsci.client.cli.tui.screens.resources import _matches_filter
    from madsci.common.types.resource_types import Asset

    res = Asset(resource_name="plate_1")
    assert _matches_filter(res, "", {"type": "all"}) is True
    assert _matches_filter(res, "", {"type": "asset"}) is True
    assert _matches_filter(res, "", {"type": "consumable"}) is False


def test_build_general_section_with_resource_model() -> None:
    """_build_general_section should accept a Resource model instance."""
    from madsci.client.cli.tui.screens.resources import _build_general_section
    from madsci.common.types.resource_types import Resource

    res = Resource(
        resource_name="test_resource",
        resource_class="vials",
        resource_description="A test resource for experiments",
    )
    section = _build_general_section(res)
    assert section.title == "General"
    assert section.fields["Name"] == "test_resource"
    assert section.fields["ID"] == res.resource_id
    assert section.fields["Base Type"] == "resource"
    assert section.fields["Class"] == "vials"
    assert "A test resource" in section.fields.get("Description", "")


def test_build_state_section_with_consumable_model() -> None:
    """_build_state_section should accept a Consumable model instance."""
    from madsci.client.cli.tui.screens.resources import _build_state_section
    from madsci.common.types.resource_types import Consumable

    res = Consumable(
        resource_name="reagent",
        quantity=50.0,
        capacity=100.0,
        unit="mL",
    )
    section = _build_state_section(res)
    assert section is not None
    assert section.title == "State"
    assert section.fields["Quantity"] == "50.0"
    assert section.fields["Capacity"] == "100.0"
    assert section.fields["Unit"] == "mL"
    assert "50%" in section.fields.get("Utilization", "")


def test_build_state_section_returns_none_for_no_quantity() -> None:
    """_build_state_section should return None for a plain Resource."""
    from madsci.client.cli.tui.screens.resources import _build_state_section
    from madsci.common.types.resource_types import Resource

    res = Resource(resource_name="basic_resource")
    section = _build_state_section(res)
    assert section is None


def test_build_hierarchy_section_with_resource_model() -> None:
    """_build_hierarchy_section should accept a Resource model instance."""
    from madsci.client.cli.tui.screens.resources import _build_hierarchy_section
    from madsci.common.types.resource_types import Resource

    res = Resource(
        resource_name="child_resource",
        parent_id="parent_123",
        key="slot_0",
    )
    section = _build_hierarchy_section(res)
    assert section is not None
    assert section.title == "Hierarchy"
    assert section.fields["Parent ID"] == "parent_123"
    assert section.fields["Key"] == "slot_0"


def test_build_hierarchy_section_returns_none_for_no_parent() -> None:
    """_build_hierarchy_section should return None with no parent or key."""
    from madsci.client.cli.tui.screens.resources import _build_hierarchy_section
    from madsci.common.types.resource_types import Resource

    res = Resource(resource_name="orphan_resource")
    section = _build_hierarchy_section(res)
    assert section is None


def test_build_attributes_section_with_resource_model() -> None:
    """_build_attributes_section should accept a Resource model instance."""
    from madsci.client.cli.tui.screens.resources import _build_attributes_section
    from madsci.common.types.resource_types import Resource

    res = Resource(
        resource_name="labeled_resource",
        attributes={"color": "blue", "weight": "150g"},
    )
    section = _build_attributes_section(res)
    assert section is not None
    assert section.title == "Attributes"
    assert section.fields["color"] == "blue"
    assert section.fields["weight"] == "150g"


def test_build_attributes_section_returns_none_for_empty() -> None:
    """_build_attributes_section should return None with no attributes."""
    from madsci.client.cli.tui.screens.resources import _build_attributes_section
    from madsci.common.types.resource_types import Resource

    res = Resource(resource_name="plain_resource", attributes={})
    section = _build_attributes_section(res)
    assert section is None


def test_build_timestamps_section_with_resource_model() -> None:
    """_build_timestamps_section should accept a Resource model instance."""
    from datetime import datetime, timezone

    from madsci.client.cli.tui.screens.resources import _build_timestamps_section
    from madsci.common.types.resource_types import Resource

    now = datetime.now(tz=timezone.utc)
    res = Resource(
        resource_name="timed_resource",
        created_at=now,
        updated_at=now,
    )
    section = _build_timestamps_section(res)
    assert section is not None
    assert section.title == "Timestamps"
    assert "Created" in section.fields
    assert "Updated" in section.fields


def test_build_timestamps_section_returns_none_for_no_timestamps() -> None:
    """_build_timestamps_section should return None with no timestamps."""
    from madsci.client.cli.tui.screens.resources import _build_timestamps_section
    from madsci.common.types.resource_types import Resource

    res = Resource(resource_name="no_time_resource")
    section = _build_timestamps_section(res)
    assert section is None


def test_resource_tree_screen_accepts_resource_client() -> None:
    """ResourceTreeScreen should accept a ResourceClient instance."""
    from unittest.mock import MagicMock

    from madsci.client.cli.tui.screens.resource_tree import ResourceTreeScreen

    mock_client = MagicMock()
    screen = ResourceTreeScreen(
        resource_id="test_resource_id",
        resource_client=mock_client,
    )
    assert screen._resource_client is mock_client


# ---------------------------------------------------------------------------
# Nodes screen migration tests
# ---------------------------------------------------------------------------


def test_nodes_no_httpx_import() -> None:
    """nodes.py should use WorkcellClient/RestNodeClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.nodes")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "nodes.py still imports httpx; should use WorkcellClient/RestNodeClient instead"
    )
    assert "get_async_client" not in source, (
        "nodes.py still uses get_async_client; should use WorkcellClient instead"
    )
    assert "WorkcellClient" in source, "nodes.py should import and use WorkcellClient"
    assert "RestNodeClient" in source, "nodes.py should import and use RestNodeClient"


def test_nodes_screen_has_workcell_client_field() -> None:
    """NodesScreen should have a lazy _workcell_client field."""
    from madsci.client.cli.tui.screens.nodes import NodesScreen

    screen = NodesScreen()
    assert hasattr(screen, "_workcell_client"), (
        "NodesScreen should have a _workcell_client field"
    )
    assert screen._workcell_client is None, (
        "_workcell_client should be None until first use"
    )


def test_nodes_data_stores_node_models() -> None:
    """NodesScreen.nodes_data should be typed for Node models."""
    from madsci.client.cli.tui.screens.nodes import NodesScreen

    screen = NodesScreen()
    # The dict should be empty initially and typed for Node models
    assert isinstance(screen.nodes_data, dict)
    assert len(screen.nodes_data) == 0


def test_get_node_status_name_with_node_status_model() -> None:
    """_get_node_status_name should accept a NodeStatus model instance."""
    from madsci.client.cli.tui.screens.nodes import _get_node_status_name
    from madsci.common.types.node_types import NodeStatus

    disconnected = NodeStatus(disconnected=True)
    assert _get_node_status_name(disconnected) == "disconnected"

    errored = NodeStatus(errored=True)
    assert _get_node_status_name(errored) == "errored"

    connected = NodeStatus()
    assert _get_node_status_name(connected) == "connected"


def test_build_general_section_with_node_model() -> None:
    """_build_general_section should accept Node, NodeInfo, NodeStatus models."""
    from madsci.client.cli.tui.screens.nodes import _build_general_section
    from madsci.common.types.node_types import Node, NodeInfo, NodeStatus
    from madsci.common.utils import new_ulid_str

    test_node_id = new_ulid_str()
    node = Node(
        node_url="http://localhost:2000/",
        status=NodeStatus(errored=True),
        info=NodeInfo(
            node_name="test_node",
            module_name="test_module",
            module_version="1.0.0",
            node_id=test_node_id,
        ),
    )
    section = _build_general_section(node, node.info, node.status)
    assert section.title == "General"
    assert "localhost" in section.fields["URL"]
    assert section.fields["Node ID"] == test_node_id
    assert section.fields["Module"] == "test_module"


def test_build_status_flags_section_with_node_status_model() -> None:
    """_build_status_flags_section should accept a NodeStatus model instance."""
    from madsci.client.cli.tui.screens.nodes import _build_status_flags_section
    from madsci.common.types.node_types import NodeStatus

    status = NodeStatus(errored=True, locked=True)
    section = _build_status_flags_section(status)
    assert section.title == "Status Flags"
    # ready is a computed field: should be False since errored=True
    assert "[red]No[/red]" in section.fields["Ready"]
    # errored and locked should show Yes
    assert "[red]Yes[/red]" in section.fields["Errored"]
    assert "[red]Yes[/red]" in section.fields["Locked"]


def test_build_actions_section_with_action_definition_models() -> None:
    """_build_actions_section should accept ActionDefinition models."""
    from madsci.client.cli.tui.screens.nodes import _build_actions_section
    from madsci.common.types.action_types import ActionDefinition

    actions = {
        "grab": ActionDefinition(
            name="grab",
            description="Grab an item",
        ),
        "release": ActionDefinition(
            name="release",
            description="Release an item",
        ),
    }
    section = _build_actions_section(actions)
    assert section.title == "Actions"
    assert "Grab an item" in section.fields["grab"]


def test_node_detail_screen_accepts_node_model() -> None:
    """NodeDetailScreen should accept a Node model instance."""
    from madsci.client.cli.tui.screens.nodes import NodeDetailScreen
    from madsci.common.types.node_types import Node, NodeStatus

    node = Node(
        node_url="http://localhost:2000/",
        status=NodeStatus(),
        state={"position": "home"},
    )
    screen = NodeDetailScreen(node_name="test_node", node_data=node)
    assert screen.node_data is node
    assert screen.node_name == "test_node"


# ---------------------------------------------------------------------------
# Status screen migration tests
# ---------------------------------------------------------------------------


def test_status_no_raw_httpx_for_nodes() -> None:
    """status.py should not use get_async_client for node endpoint."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.status")
    source = inspect.getsource(mod)

    assert "WorkcellClient" in source, (
        "status.py should import and use WorkcellClient for node data"
    )


def test_status_screen_has_workcell_client_field() -> None:
    """StatusScreen should have a lazy _workcell_client field."""
    from madsci.client.cli.tui.screens.status import StatusScreen

    screen = StatusScreen()
    assert hasattr(screen, "_workcell_client"), (
        "StatusScreen should have a _workcell_client field"
    )
    assert screen._workcell_client is None, (
        "_workcell_client should be None until first use"
    )


# ---------------------------------------------------------------------------
# Workflow screen migration tests
# ---------------------------------------------------------------------------


def test_workflows_no_httpx_import() -> None:
    """workflows.py should use WorkcellClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.workflows")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "workflows.py still imports httpx; should use WorkcellClient instead"
    )
    assert "get_async_client" not in source, (
        "workflows.py still uses get_async_client; should use WorkcellClient instead"
    )
    assert "WorkcellClient" in source, (
        "workflows.py should import and use WorkcellClient"
    )


def test_workflows_screen_has_workcell_client_field() -> None:
    """WorkflowsScreen should have a lazy _workcell_client field."""
    from madsci.client.cli.tui.screens.workflows import WorkflowsScreen

    screen = WorkflowsScreen()
    assert hasattr(screen, "_workcell_client"), (
        "WorkflowsScreen should have a _workcell_client field"
    )
    assert screen._workcell_client is None, (
        "_workcell_client should be None until first use"
    )


def test_workflows_data_stores_workflow_models() -> None:
    """WorkflowsScreen.workflows_data should be typed for Workflow models."""
    from madsci.client.cli.tui.screens.workflows import WorkflowsScreen

    screen = WorkflowsScreen()
    assert isinstance(screen.workflows_data, dict)
    assert len(screen.workflows_data) == 0


def test_get_workflow_status_name_with_workflow_status_model() -> None:
    """_get_workflow_status_name should accept a WorkflowStatus model."""
    from madsci.client.cli.tui.screens.workflows import _get_workflow_status_name
    from madsci.common.types.workflow_types import WorkflowStatus

    status = WorkflowStatus(running=True)
    assert _get_workflow_status_name(status) == "running"

    status = WorkflowStatus(completed=True)
    assert _get_workflow_status_name(status) == "completed"

    status = WorkflowStatus(failed=True)
    assert _get_workflow_status_name(status) == "failed"

    status = WorkflowStatus(paused=True)
    assert _get_workflow_status_name(status) == "paused"

    status = WorkflowStatus(cancelled=True)
    assert _get_workflow_status_name(status) == "cancelled"

    status = WorkflowStatus()
    assert _get_workflow_status_name(status) == "unknown"


def test_matches_filter_with_workflow_model() -> None:
    """_matches_filter should accept a Workflow model instance."""
    from madsci.client.cli.tui.screens.workflows import _matches_filter
    from madsci.common.types.workflow_types import Workflow

    wf = Workflow(name="test_workflow", steps=[])
    assert _matches_filter(wf, "", {}) is True
    assert _matches_filter(wf, "test", {}) is True
    assert _matches_filter(wf, "nonexistent", {}) is False


def test_matches_filter_with_status_filter_and_workflow_model() -> None:
    """_matches_filter status filter should work with Workflow model."""
    from madsci.client.cli.tui.screens.workflows import _matches_filter
    from madsci.common.types.workflow_types import Workflow, WorkflowStatus

    wf = Workflow(
        name="test_workflow",
        status=WorkflowStatus(running=True),
        steps=[],
    )
    assert _matches_filter(wf, "", {"status": "all"}) is True
    assert _matches_filter(wf, "", {"status": "running"}) is True
    assert _matches_filter(wf, "", {"status": "completed"}) is False


def test_build_timing_section_with_workflow_model() -> None:
    """_build_timing_section should accept a Workflow model instance."""
    from datetime import datetime, timezone

    from madsci.client.cli.tui.screens.workflows import _build_timing_section
    from madsci.common.types.workflow_types import Workflow

    now = datetime.now(tz=timezone.utc)
    wf = Workflow(
        name="timed_workflow",
        start_time=now,
        end_time=now,
        submitted_time=now,
        steps=[],
    )
    section = _build_timing_section(wf)
    assert section is not None
    assert section.title == "Timing"
    assert "Started" in section.fields
    assert "Ended" in section.fields
    assert "Submitted" in section.fields


def test_build_timing_section_returns_none_for_no_times() -> None:
    """_build_timing_section should return None when no time fields are set."""
    from madsci.client.cli.tui.screens.workflows import _build_timing_section
    from madsci.common.types.workflow_types import Workflow

    wf = Workflow(name="no_times", steps=[])
    section = _build_timing_section(wf)
    assert section is None


def test_build_progress_section_with_workflow_model() -> None:
    """_build_progress_section should accept a Workflow model."""
    from madsci.client.cli.tui.screens.workflows import _build_progress_section
    from madsci.common.types.action_types import ActionStatus
    from madsci.common.types.step_types import Step
    from madsci.common.types.workflow_types import Workflow, WorkflowStatus

    steps = [
        Step(name="step1", action="do_thing", status=ActionStatus.SUCCEEDED),
        Step(name="step2", action="do_other", status=ActionStatus.NOT_STARTED),
    ]
    wf = Workflow(
        name="progress_workflow",
        steps=steps,
        status=WorkflowStatus(running=True, current_step_index=1),
    )
    section = _build_progress_section(wf)
    assert section is not None
    assert section.title == "Progress"
    assert "Total" in section.fields
    assert section.fields["Total"] == "2"


def test_build_progress_section_returns_none_for_no_steps() -> None:
    """_build_progress_section should return None when no steps."""
    from madsci.client.cli.tui.screens.workflows import _build_progress_section
    from madsci.common.types.workflow_types import Workflow

    wf = Workflow(name="empty", steps=[])
    section = _build_progress_section(wf)
    assert section is None


# ---------------------------------------------------------------------------
# Workflow detail screen migration tests
# ---------------------------------------------------------------------------


def test_workflow_detail_no_httpx_import() -> None:
    """workflow_detail.py should use WorkcellClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.workflow_detail")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "workflow_detail.py still imports httpx; should use WorkcellClient instead"
    )
    assert "WorkcellClient" in source, (
        "workflow_detail.py should import and use WorkcellClient"
    )


def test_workflow_detail_screen_has_workcell_client_field() -> None:
    """WorkflowDetailScreen should have a lazy _workcell_client field."""
    from madsci.client.cli.tui.screens.workflow_detail import WorkflowDetailScreen
    from madsci.common.types.workflow_types import Workflow

    wf = Workflow(name="test", steps=[])
    screen = WorkflowDetailScreen(
        workflow_id=wf.workflow_id,
        workflow_data=wf,
    )
    assert hasattr(screen, "_workcell_client"), (
        "WorkflowDetailScreen should have a _workcell_client field"
    )
    assert screen._workcell_client is None, (
        "_workcell_client should be None until first use"
    )


def test_workflow_detail_screen_accepts_workflow_model() -> None:
    """WorkflowDetailScreen should accept a Workflow model instance."""
    from madsci.client.cli.tui.screens.workflow_detail import WorkflowDetailScreen
    from madsci.common.types.workflow_types import Workflow

    wf = Workflow(name="detail_test", steps=[])
    screen = WorkflowDetailScreen(
        workflow_id=wf.workflow_id,
        workflow_data=wf,
    )
    assert screen.workflow_data is wf
    assert screen.workflow_id == wf.workflow_id


# ---------------------------------------------------------------------------
# Action executor screen migration tests
# ---------------------------------------------------------------------------


def test_action_executor_no_httpx_import() -> None:
    """action_executor.py should use RestNodeClient, not raw httpx."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.action_executor")
    source = inspect.getsource(mod)

    assert "import httpx" not in source, (
        "action_executor.py still imports httpx; should use RestNodeClient instead"
    )
    assert "RestNodeClient" in source, (
        "action_executor.py should import and use RestNodeClient"
    )


def test_action_executor_imports_action_types() -> None:
    """action_executor.py should import ActionRequest, ActionResult, ActionStatus."""
    import importlib
    import inspect

    mod = importlib.import_module("madsci.client.cli.tui.screens.action_executor")
    source = inspect.getsource(mod)

    assert "ActionRequest" in source, "action_executor.py should import ActionRequest"
    assert "ActionResult" in source, "action_executor.py should import ActionResult"
    assert "ActionStatus" in source, "action_executor.py should import ActionStatus"


@pytest.mark.asyncio
async def test_action_executor_composes(mock_app_class) -> None:
    """ActionExecutorScreen composes without error."""
    from madsci.client.cli.tui.screens.action_executor import ActionExecutorScreen

    app = mock_app_class()
    async with app.run_test() as pilot:
        await pilot.app.push_screen(
            ActionExecutorScreen(
                node_name="test_node",
                node_url="http://localhost:2000",
                actions={"test_action": {"description": "A test action", "args": {}}},
            )
        )
        assert pilot.app.screen is not None


def test_show_result_with_action_result_model() -> None:
    """_show_result should accept an ActionResult model instance."""
    from unittest.mock import MagicMock

    from madsci.client.cli.tui.screens.action_executor import ActionExecutorScreen
    from madsci.common.types.action_types import ActionResult, ActionStatus

    screen = ActionExecutorScreen(
        node_name="test_node",
        node_url="http://localhost:2000",
        actions={},
    )
    panel = MagicMock()

    result = ActionResult(
        action_id="01JTEST000000000000000001",
        status=ActionStatus.SUCCEEDED,
    )
    # Should not raise when passed an ActionResult model
    screen._show_result(panel, "test_action", result)

    # Verify update_content was called
    panel.update_content.assert_called_once()
    call_kwargs = panel.update_content.call_args
    assert "test_action" in call_kwargs.kwargs.get(
        "title", call_kwargs[1].get("title", "")
    )


def test_show_result_displays_action_result_fields() -> None:
    """_show_result should display fields from ActionResult model."""
    from unittest.mock import MagicMock

    from madsci.client.cli.tui.screens.action_executor import ActionExecutorScreen
    from madsci.common.types.action_types import ActionResult, ActionStatus
    from madsci.common.types.base_types import Error

    screen = ActionExecutorScreen(
        node_name="test_node",
        node_url="http://localhost:2000",
        actions={},
    )
    panel = MagicMock()

    result = ActionResult(
        action_id="01JTEST000000000000000002",
        status=ActionStatus.FAILED,
        errors=[Error(message="Something went wrong")],
        json_result={"key": "value"},
    )
    screen._show_result(panel, "do_thing", result)

    call_kwargs = panel.update_content.call_args
    sections = call_kwargs.kwargs.get("sections", call_kwargs[1].get("sections", []))

    # Should have at least a Result section
    section_titles = [s.title for s in sections]
    assert "Result" in section_titles

    # The Result section should have the action ID
    result_section = next(s for s in sections if s.title == "Result")
    assert "01JTEST000000000000000002" in result_section.fields.get("Action ID", "")

    # Should have an Errors section
    assert "Errors" in section_titles


def test_show_result_with_json_result_data() -> None:
    """_show_result should display json_result data from ActionResult."""
    from unittest.mock import MagicMock

    from madsci.client.cli.tui.screens.action_executor import ActionExecutorScreen
    from madsci.common.types.action_types import ActionResult, ActionStatus

    screen = ActionExecutorScreen(
        node_name="test_node",
        node_url="http://localhost:2000",
        actions={},
    )
    panel = MagicMock()

    result = ActionResult(
        action_id="01JTEST000000000000000003",
        status=ActionStatus.SUCCEEDED,
        json_result={"temperature": 25.5, "pressure": 1.01},
    )
    screen._show_result(panel, "measure", result)

    call_kwargs = panel.update_content.call_args
    sections = call_kwargs.kwargs.get("sections", call_kwargs[1].get("sections", []))
    section_titles = [s.title for s in sections]
    assert "Data" in section_titles


# ---------------------------------------------------------------------------
# Regression test: no raw httpx in TUI screens
# ---------------------------------------------------------------------------


def test_no_raw_httpx_in_tui_screens() -> None:
    """Ensure TUI screens use client classes, not raw httpx.

    This regression test prevents re-introduction of raw HTTP calls
    in TUI screen files. All service communication must go through
    the typed client classes (ExperimentClient, EventClient, etc.).
    """
    import ast
    from pathlib import Path

    screens_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "madsci"
        / "client"
        / "cli"
        / "tui"
        / "screens"
    )
    violations: list[str] = []

    for py_file in sorted(screens_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "httpx":
                        violations.append(f"{py_file.name} imports httpx directly")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "httpx" in node.module
            ):
                violations.append(f"{py_file.name} imports from httpx")

    assert not violations, (
        "TUI screens must use typed client classes, not raw httpx. "
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations)
    )
