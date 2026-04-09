"""Basic composition tests for TUI screens.

These tests verify that screens can be instantiated and composed without
errors. They use Textual's async test runner to push screens onto a minimal
host app and confirm no exception is raised.
"""

from __future__ import annotations

from typing import ClassVar

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
    async with app.run_test() as pilot:
        await pilot.app.push_screen(ResourcesScreen())
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


@pytest.mark.asyncio
async def test_locations_detail_panel_shows_managed_by() -> None:
    """LocationsScreen detail panel should display Managed By field."""
    from madsci.client.cli.tui.screens.locations import (
        _build_general_section,
    )

    section = _build_general_section(
        "test_id",
        {"location_name": "test", "managed_by": "node"},
    )
    # Check that the section has a 'Managed By' field
    assert "Managed By" in section.fields
    assert section.fields["Managed By"] == "NODE"


@pytest.mark.asyncio
async def test_locations_detail_panel_shows_owner() -> None:
    """LocationsScreen detail panel should display Owner field."""
    from madsci.client.cli.tui.screens.locations import (
        _build_general_section,
    )

    node_id = "01JTEST12345678901234"
    section = _build_general_section(
        "test_id",
        {
            "location_name": "test",
            "managed_by": "node",
            "owner": {"node_id": node_id},
        },
    )
    assert "Owner" in section.fields
    assert node_id in section.fields["Owner"]
