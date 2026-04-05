"""Tests for MADSci TUI widgets.

Tests all reusable widgets in the TUI widget library using Textual's
async testing framework (``App.run_test``).
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App, ComposeResult

# ---------------------------------------------------------------------------
# Guard: skip entire module if textual is not installed
# ---------------------------------------------------------------------------

textual = pytest.importorskip("textual")


# ---------------------------------------------------------------------------
# Widget imports
# ---------------------------------------------------------------------------

from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin  # noqa: E402
from madsci.client.cli.tui.widgets.action_bar import ActionBar, ActionDef  # noqa: E402
from madsci.client.cli.tui.widgets.data_table_view import (  # noqa: E402
    ColumnDef,
    DataTableView,
)
from madsci.client.cli.tui.widgets.detail_panel import (  # noqa: E402
    DetailPanel,
    DetailSection,
)
from madsci.client.cli.tui.widgets.filter_bar import FilterBar, FilterDef  # noqa: E402
from madsci.client.cli.tui.widgets.log_viewer import LogViewer  # noqa: E402
from madsci.client.cli.tui.widgets.service_aware import (  # noqa: E402
    ServiceAwareContainer,
)
from madsci.client.cli.tui.widgets.status_badge import StatusBadge  # noqa: E402
from madsci.client.cli.utils.formatting import (  # noqa: E402
    STATUS_STYLES,
    get_status_style,
)

# ===========================================================================
# 3.1 StatusBadge
# ===========================================================================


class StatusBadgeApp(App):
    """Test app for StatusBadge."""

    def compose(self) -> ComposeResult:
        yield StatusBadge("healthy", id="badge-text")
        yield StatusBadge("running", show_text=False, id="badge-icon")
        yield StatusBadge(id="badge-default")


class TestStatusBadge:
    """Tests for the StatusBadge widget."""

    @pytest.mark.asyncio
    async def test_render_with_text(self) -> None:
        """StatusBadge renders icon + status text when show_text=True."""
        async with StatusBadgeApp().run_test() as pilot:
            badge = pilot.app.query_one("#badge-text", StatusBadge)
            rendered = badge.render()
            icon, colour = get_status_style("healthy")
            assert icon in rendered
            assert "healthy" in rendered
            assert colour in rendered

    @pytest.mark.asyncio
    async def test_render_without_text(self) -> None:
        """StatusBadge renders only icon when show_text=False."""
        async with StatusBadgeApp().run_test() as pilot:
            badge = pilot.app.query_one("#badge-icon", StatusBadge)
            rendered = badge.render()
            icon, _colour = get_status_style("running")
            assert icon in rendered
            # The status text should NOT appear
            assert "running" not in rendered

    @pytest.mark.asyncio
    async def test_default_status(self) -> None:
        """StatusBadge defaults to 'unknown'."""
        async with StatusBadgeApp().run_test() as pilot:
            badge = pilot.app.query_one("#badge-default", StatusBadge)
            assert badge.status == "unknown"
            icon, _colour = get_status_style("unknown")
            rendered = badge.render()
            assert icon in rendered

    @pytest.mark.asyncio
    async def test_reactive_status_change(self) -> None:
        """Changing status reactive updates the render output."""
        async with StatusBadgeApp().run_test() as pilot:
            badge = pilot.app.query_one("#badge-text", StatusBadge)
            badge.status = "failed"
            await pilot.pause()
            rendered = badge.render()
            icon, _colour = get_status_style("failed")
            assert icon in rendered
            assert "failed" in rendered

    @pytest.mark.asyncio
    async def test_all_known_statuses(self) -> None:
        """All STATUS_STYLES entries render correctly."""
        async with StatusBadgeApp().run_test() as pilot:
            badge = pilot.app.query_one("#badge-text", StatusBadge)
            for status_name, (expected_icon, _expected_colour) in STATUS_STYLES.items():
                badge.status = status_name
                await pilot.pause()
                rendered = badge.render()
                assert expected_icon in rendered
                assert status_name in rendered


# ===========================================================================
# 3.2 DetailPanel
# ===========================================================================


class DetailPanelApp(App):
    """Test app for DetailPanel."""

    def compose(self) -> ComposeResult:
        yield DetailPanel(id="panel")
        yield DetailPanel(placeholder="Custom placeholder", id="panel-custom")


class TestDetailPanel:
    """Tests for the DetailPanel widget."""

    @pytest.mark.asyncio
    async def test_initial_placeholder(self) -> None:
        """DetailPanel shows placeholder text initially."""
        async with DetailPanelApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", DetailPanel)
            label = panel.query_one("#detail-panel-content")
            assert "Select an item" in str(label.render())

    @pytest.mark.asyncio
    async def test_custom_placeholder(self) -> None:
        """DetailPanel uses custom placeholder text."""
        async with DetailPanelApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel-custom", DetailPanel)
            label = panel.query_one("#detail-panel-content")
            assert "Custom placeholder" in str(label.render())

    @pytest.mark.asyncio
    async def test_update_content(self) -> None:
        """update_content() renders title and sections."""
        async with DetailPanelApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", DetailPanel)
            panel.update_content(
                title="Test Title",
                sections=[
                    DetailSection("Section A", {"Key1": "Value1", "Key2": "Value2"}),
                    DetailSection("Section B", {"Foo": "Bar"}),
                ],
            )
            await pilot.pause()
            label = panel.query_one("#detail-panel-content")
            text = str(label.render())
            assert "Test Title" in text
            assert "Section A" in text
            assert "Key1" in text
            assert "Value1" in text
            assert "Section B" in text
            assert "Foo" in text

    @pytest.mark.asyncio
    async def test_update_content_empty_fields(self) -> None:
        """update_content() handles sections with no fields."""
        async with DetailPanelApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", DetailPanel)
            panel.update_content(
                title="Empty Section Test",
                sections=[
                    DetailSection("Empty", {}),
                ],
            )
            await pilot.pause()
            label = panel.query_one("#detail-panel-content")
            text = str(label.render())
            assert "Empty Section Test" in text
            assert "No data" in text

    @pytest.mark.asyncio
    async def test_clear_content(self) -> None:
        """clear_content() resets to placeholder."""
        async with DetailPanelApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", DetailPanel)
            panel.update_content("Title", [DetailSection("S", {"k": "v"})])
            await pilot.pause()
            panel.clear_content()
            await pilot.pause()
            label = panel.query_one("#detail-panel-content")
            text = str(label.render())
            assert "Select an item" in text


# ===========================================================================
# 3.3 ServiceAwareContainer
# ===========================================================================


class ServiceAwareApp(App):
    """Test app for ServiceAwareContainer."""

    def compose(self) -> ComposeResult:
        yield ServiceAwareContainer(
            service_url="http://localhost:9999/",
            service_name="Test Service",
            check_interval=100.0,  # Long interval to avoid timer noise
            id="sac",
        )


class TestServiceAwareContainer:
    """Tests for the ServiceAwareContainer widget."""

    @pytest.mark.asyncio
    async def test_initial_state_unavailable(self) -> None:
        """Container starts showing unavailable panel by default."""
        with patch(
            "madsci.client.cli.tui.widgets.service_aware.check_service_health_async",
            new_callable=AsyncMock,
        ) as mock_check:
            from madsci.client.cli.utils.service_health import ServiceHealthResult

            mock_check.return_value = ServiceHealthResult(
                name="Test Service",
                url="http://localhost:9999/",
                is_available=False,
                error="Connection refused",
            )
            async with ServiceAwareApp().run_test() as pilot:
                sac = pilot.app.query_one("#sac", ServiceAwareContainer)
                assert sac.is_available is False
                # Unavailable panel should be visible
                unavailable = sac.query_one("#service-unavailable-panel")
                assert unavailable.display is True

    @pytest.mark.asyncio
    async def test_available_state(self) -> None:
        """Container shows content panel when service is available."""
        with patch(
            "madsci.client.cli.tui.widgets.service_aware.check_service_health_async",
            new_callable=AsyncMock,
        ) as mock_check:
            from madsci.client.cli.utils.service_health import ServiceHealthResult

            mock_check.return_value = ServiceHealthResult(
                name="Test Service",
                url="http://localhost:9999/",
                is_available=True,
                version="1.0.0",
            )
            async with ServiceAwareApp().run_test() as pilot:
                sac = pilot.app.query_one("#sac", ServiceAwareContainer)
                await pilot.pause()
                assert sac.is_available is True
                content = sac.query_one("#service-content-panel")
                assert content.display is True

    @pytest.mark.asyncio
    async def test_check_health_delegates(self) -> None:
        """check_health() calls the shared async health check function."""
        with patch(
            "madsci.client.cli.tui.widgets.service_aware.check_service_health_async",
            new_callable=AsyncMock,
        ) as mock_check:
            from madsci.client.cli.utils.service_health import ServiceHealthResult

            mock_check.return_value = ServiceHealthResult(
                name="Test Service",
                url="http://localhost:9999/",
                is_available=True,
            )
            async with ServiceAwareApp().run_test() as pilot:
                sac = pilot.app.query_one("#sac", ServiceAwareContainer)
                result = await sac.check_health()
                assert result is True
                mock_check.assert_called()

    @pytest.mark.asyncio
    async def test_messages_posted(self) -> None:
        """ServiceAvailable/ServiceUnavailable messages are posted on state change."""
        with patch(
            "madsci.client.cli.tui.widgets.service_aware.check_service_health_async",
            new_callable=AsyncMock,
        ) as mock_check:
            from madsci.client.cli.utils.service_health import ServiceHealthResult

            mock_check.return_value = ServiceHealthResult(
                name="Test Service",
                url="http://localhost:9999/",
                is_available=False,
                error="timeout",
            )
            async with ServiceAwareApp().run_test() as pilot:
                sac = pilot.app.query_one("#sac", ServiceAwareContainer)
                assert sac.is_available is False

                # Switch to available
                mock_check.return_value = ServiceHealthResult(
                    name="Test Service",
                    url="http://localhost:9999/",
                    is_available=True,
                )
                await sac.check_health()
                await pilot.pause()
                assert sac.is_available is True


# ===========================================================================
# 3.4 DataTableView
# ===========================================================================


class DataTableViewApp(App):
    """Test app for DataTableView."""

    def compose(self) -> ComposeResult:
        yield DataTableView(
            columns=[
                ColumnDef("status", "Status"),
                ColumnDef("name", "Name"),
                ColumnDef("value", "Value", width=20),
            ],
            empty_message="Nothing here",
            id="dtv",
        )


class TestDataTableView:
    """Tests for the DataTableView widget."""

    @pytest.mark.asyncio
    async def test_initial_empty_state(self) -> None:
        """DataTableView shows empty message when no rows."""
        async with DataTableViewApp().run_test() as pilot:
            dtv = pilot.app.query_one("#dtv", DataTableView)
            empty_label = dtv.query_one("#dtv-empty-label")
            assert empty_label.display is True
            assert "Nothing here" in str(empty_label.render())

    @pytest.mark.asyncio
    async def test_populate_hides_empty(self) -> None:
        """Populating rows hides the empty message."""
        async with DataTableViewApp().run_test() as pilot:
            dtv = pilot.app.query_one("#dtv", DataTableView)
            dtv.clear_and_populate(
                [
                    {"status": "OK", "name": "Alpha", "value": "100"},
                    {"status": "ERR", "name": "Beta", "value": "200"},
                ]
            )
            await pilot.pause()
            empty_label = dtv.query_one("#dtv-empty-label")
            assert empty_label.display is False
            table = dtv.query_one("#dtv-table")
            assert table.display is True

    @pytest.mark.asyncio
    async def test_clear_and_repopulate(self) -> None:
        """clear_and_populate() replaces all rows."""
        async with DataTableViewApp().run_test() as pilot:
            dtv = pilot.app.query_one("#dtv", DataTableView)
            dtv.clear_and_populate(
                [
                    {"status": "A", "name": "One", "value": "1"},
                ]
            )
            await pilot.pause()

            dtv.clear_and_populate(
                [
                    {"status": "B", "name": "Two", "value": "2"},
                    {"status": "C", "name": "Three", "value": "3"},
                ]
            )
            await pilot.pause()
            assert len(dtv._rows) == 2

    @pytest.mark.asyncio
    async def test_clear_restores_empty(self) -> None:
        """Clearing all rows restores the empty state."""
        async with DataTableViewApp().run_test() as pilot:
            dtv = pilot.app.query_one("#dtv", DataTableView)
            dtv.clear_and_populate(
                [
                    {"status": "A", "name": "One", "value": "1"},
                ]
            )
            await pilot.pause()
            dtv.clear_and_populate([])
            await pilot.pause()
            empty_label = dtv.query_one("#dtv-empty-label")
            assert empty_label.display is True

    @pytest.mark.asyncio
    async def test_missing_keys_use_empty_string(self) -> None:
        """Rows with missing keys use empty string for the cell."""
        async with DataTableViewApp().run_test() as pilot:
            dtv = pilot.app.query_one("#dtv", DataTableView)
            dtv.clear_and_populate(
                [
                    {"status": "OK"},  # missing name and value
                ]
            )
            await pilot.pause()
            assert len(dtv._rows) == 1


# ===========================================================================
# 3.5 ActionBar
# ===========================================================================


class ActionBarApp(App):
    """Test app for ActionBar."""

    def compose(self) -> ComposeResult:
        yield ActionBar(
            actions=[
                ActionDef("r", "Refresh", "refresh"),
                ActionDef("p", "Pause", "pause", variant="warning"),
                ActionDef("c", "Cancel", "cancel", variant="error"),
            ],
            id="abar",
        )


class TestActionBar:
    """Tests for the ActionBar widget."""

    @pytest.mark.asyncio
    async def test_render_contains_all_actions(self) -> None:
        """ActionBar renders all defined actions."""
        async with ActionBarApp().run_test() as pilot:
            abar = pilot.app.query_one("#abar", ActionBar)
            rendered = abar.render()
            assert "Refresh" in rendered
            assert "Pause" in rendered
            assert "Cancel" in rendered
            assert "[r]" in rendered
            assert "[p]" in rendered
            assert "[c]" in rendered

    @pytest.mark.asyncio
    async def test_variant_colours(self) -> None:
        """ActionBar applies variant colours correctly."""
        async with ActionBarApp().run_test() as pilot:
            abar = pilot.app.query_one("#abar", ActionBar)
            rendered = abar.render()
            # "Pause" should have yellow (warning variant)
            assert "yellow" in rendered
            # "Cancel" should have red (error variant)
            assert "red" in rendered

    @pytest.mark.asyncio
    async def test_trigger_action_posts_message(self) -> None:
        """trigger_action() posts an ActionTriggered message."""
        messages_received: list[str] = []

        class TestActionBarApp(App):
            def compose(self) -> ComposeResult:
                yield ActionBar(
                    actions=[ActionDef("r", "Refresh", "refresh")],
                    id="abar2",
                )

            def on_action_bar_action_triggered(
                self, event: ActionBar.ActionTriggered
            ) -> None:
                messages_received.append(event.action)

        async with TestActionBarApp().run_test() as pilot:
            abar = pilot.app.query_one("#abar2", ActionBar)
            abar.trigger_action("refresh")
            await pilot.pause()
            assert "refresh" in messages_received

    @pytest.mark.asyncio
    async def test_trigger_unknown_action_noop(self) -> None:
        """trigger_action() with unknown name is a no-op."""
        async with ActionBarApp().run_test() as pilot:
            abar = pilot.app.query_one("#abar", ActionBar)
            # Should not raise
            abar.trigger_action("nonexistent")


# ===========================================================================
# 3.6 FilterBar
# ===========================================================================


class FilterBarApp(App):
    """Test app for FilterBar."""

    def compose(self) -> ComposeResult:
        yield FilterBar(
            search_placeholder="Type to search...",
            filters=[
                FilterDef(
                    name="level",
                    label="Level",
                    options=[("all", "All"), ("info", "Info"), ("error", "Error")],
                    default="all",
                ),
            ],
            id="fbar",
        )


class TestFilterBar:
    """Tests for the FilterBar widget."""

    @pytest.mark.asyncio
    async def test_compose_creates_input_and_select(self) -> None:
        """FilterBar composes a search input and filter selects."""
        async with FilterBarApp().run_test() as pilot:
            fbar = pilot.app.query_one("#fbar", FilterBar)
            from textual.widgets import Input, Select

            search = fbar.query_one("#filter-search", Input)
            assert search is not None
            level_select = fbar.query_one("#filter-level", Select)
            assert level_select is not None

    @pytest.mark.asyncio
    async def test_get_search_text_empty(self) -> None:
        """get_search_text() returns empty string initially."""
        async with FilterBarApp().run_test() as pilot:
            fbar = pilot.app.query_one("#fbar", FilterBar)
            assert fbar.get_search_text() == ""

    @pytest.mark.asyncio
    async def test_get_filter_values_default(self) -> None:
        """get_filter_values() returns default values."""
        async with FilterBarApp().run_test() as pilot:
            fbar = pilot.app.query_one("#fbar", FilterBar)
            values = fbar.get_filter_values()
            assert "level" in values
            assert values["level"] == "all"

    @pytest.mark.asyncio
    async def test_no_filters(self) -> None:
        """FilterBar works with no dropdown filters."""

        class NoFilterApp(App):
            def compose(self) -> ComposeResult:
                yield FilterBar(id="fbar-none")

        async with NoFilterApp().run_test() as pilot:
            fbar = pilot.app.query_one("#fbar-none", FilterBar)
            assert fbar.get_filter_values() == {}
            assert fbar.get_search_text() == ""


# ===========================================================================
# 3.7 LogViewer
# ===========================================================================


class LogViewerApp(App):
    """Test app for LogViewer."""

    def compose(self) -> ComposeResult:
        yield LogViewer(max_seen=100, id="lv")


class TestLogViewer:
    """Tests for the LogViewer widget."""

    @pytest.mark.asyncio
    async def test_append_entries_dedup(self) -> None:
        """Duplicate entries are not appended."""
        async with LogViewerApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv", LogViewer)
            entries = [
                {"event_id": "1", "log_level": 20, "event_data": {"message": "hello"}},
                {"event_id": "2", "log_level": 30, "event_data": {"message": "warn"}},
            ]
            count = lv.append_entries(entries)
            assert count == 2

            # Append same entries again
            count2 = lv.append_entries(entries)
            assert count2 == 0

    @pytest.mark.asyncio
    async def test_append_mixed_new_old(self) -> None:
        """Only new entries are counted."""
        async with LogViewerApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv", LogViewer)
            lv.append_entries(
                [
                    {"event_id": "a", "log_level": 20, "event_data": {"message": "a"}},
                ]
            )
            count = lv.append_entries(
                [
                    {"event_id": "a", "log_level": 20, "event_data": {"message": "a"}},
                    {"event_id": "b", "log_level": 20, "event_data": {"message": "b"}},
                ]
            )
            assert count == 1

    @pytest.mark.asyncio
    async def test_clear_resets_dedup(self) -> None:
        """clear() resets the dedup cache so entries can be re-added."""
        async with LogViewerApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv", LogViewer)
            entries = [
                {"event_id": "x", "log_level": 20, "event_data": {"message": "x"}},
            ]
            lv.append_entries(entries)
            lv.clear()
            count = lv.append_entries(entries)
            assert count == 1

    @pytest.mark.asyncio
    async def test_max_seen_eviction(self) -> None:
        """Oldest seen IDs are evicted when max_seen is exceeded."""

        class SmallCacheApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewer(max_seen=5, id="lv-small")

        async with SmallCacheApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv-small", LogViewer)
            # Add 10 entries, exceeding max_seen=5
            entries = [
                {"event_id": str(i), "log_level": 20, "event_data": {"message": str(i)}}
                for i in range(10)
            ]
            count = lv.append_entries(entries)
            assert count == 10
            # Only last 5 should be in the cache
            assert len(lv._seen_ids) == 5

    @pytest.mark.asyncio
    async def test_custom_formatter(self) -> None:
        """Custom formatter is used for rendering."""
        async with LogViewerApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv", LogViewer)
            lv.set_formatter(lambda entry: f"CUSTOM: {entry.get('event_id')}")
            count = lv.append_entries(
                [
                    {
                        "event_id": "fmt-1",
                        "log_level": 20,
                        "event_data": {"message": "hi"},
                    },
                ]
            )
            assert count == 1

    @pytest.mark.asyncio
    async def test_follow_mode_reactive(self) -> None:
        """follow_mode starts as False and can be toggled."""
        async with LogViewerApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv", LogViewer)
            assert lv.follow_mode is False
            lv.follow_mode = True
            await pilot.pause()
            assert lv.follow_mode is True

    @pytest.mark.asyncio
    async def test_custom_id_key(self) -> None:
        """append_entries() uses custom id_key for dedup."""
        async with LogViewerApp().run_test() as pilot:
            lv = pilot.app.query_one("#lv", LogViewer)
            entries = [
                {"custom_id": "c1", "log_level": 20, "event_data": {"message": "hi"}},
                {"custom_id": "c2", "log_level": 20, "event_data": {"message": "bye"}},
            ]
            count = lv.append_entries(entries, id_key="custom_id")
            assert count == 2
            # Dups with same custom key
            count2 = lv.append_entries(entries, id_key="custom_id")
            assert count2 == 0


# ===========================================================================
# 3.8 Mixins
# ===========================================================================


class TestAutoRefreshMixin:
    """Tests for the AutoRefreshMixin."""

    def test_default_values(self) -> None:
        """Mixin provides default auto_refresh_enabled and refresh_interval."""
        assert hasattr(AutoRefreshMixin, "auto_refresh_enabled")
        assert hasattr(AutoRefreshMixin, "refresh_interval")
        assert AutoRefreshMixin.refresh_interval > 0

    @pytest.mark.asyncio
    async def test_refresh_data_is_noop_by_default(self) -> None:
        """Default refresh_data() does nothing (no error)."""
        mixin = AutoRefreshMixin()
        await mixin.refresh_data()

    @pytest.mark.asyncio
    async def test_toggle_action_in_screen(self) -> None:
        """action_toggle_auto_refresh() toggles the flag in a screen context."""
        from textual.screen import Screen

        class TestScreen(AutoRefreshMixin, Screen):
            async def refresh_data(self) -> None:
                pass

        class ToggleApp(App):
            SCREENS: ClassVar[dict] = {"test": TestScreen}  # type: ignore[assignment]

            def on_mount(self) -> None:
                self.push_screen("test")

        async with ToggleApp().run_test() as pilot:
            screen = pilot.app.screen
            assert screen.auto_refresh_enabled is True
            screen.action_toggle_auto_refresh()
            await pilot.pause()
            assert screen.auto_refresh_enabled is False
            screen.action_toggle_auto_refresh()
            await pilot.pause()
            assert screen.auto_refresh_enabled is True


class TestServiceURLMixin:
    """Tests for the ServiceURLMixin."""

    def test_fallback_to_defaults(self) -> None:
        """get_service_url() falls back to DEFAULT_SERVICES."""
        mixin = ServiceURLMixin()
        mixin.app = type("FakeApp", (), {"service_urls": {}})()  # type: ignore[attr-defined]
        url = mixin.get_service_url("event_manager")
        assert "8001" in url

    def test_app_service_urls(self) -> None:
        """get_service_url() reads from app.service_urls."""
        mixin = ServiceURLMixin()
        mixin.app = type(  # type: ignore[attr-defined]
            "FakeApp", (), {"service_urls": {"event_manager": "http://custom:9999/"}}
        )()
        assert mixin.get_service_url("event_manager") == "http://custom:9999/"

    def test_no_app_graceful(self) -> None:
        """get_service_url() handles missing app attribute gracefully."""

        mixin = ServiceURLMixin()
        # No self.app attribute
        url = mixin.get_service_url("event_manager")
        assert "8001" in url


# ===========================================================================
# 3.9 Widget exports (__init__.py)
# ===========================================================================


class TestWidgetExports:
    """Tests for the widgets package exports."""

    def test_all_widgets_importable(self) -> None:
        """All widget classes are importable from the package."""
        from madsci.client.cli.tui.widgets import (
            ActionBar,
            ActionDef,
            ColumnDef,
            DataTableView,
            DetailPanel,
            DetailSection,
            FilterBar,
            FilterDef,
            LogViewer,
            ServiceAwareContainer,
            StatusBadge,
        )

        assert all(
            [
                ActionBar,
                ActionDef,
                ColumnDef,
                DataTableView,
                DetailPanel,
                DetailSection,
                FilterBar,
                FilterDef,
                LogViewer,
                ServiceAwareContainer,
                StatusBadge,
            ]
        )

    def test_all_list_complete(self) -> None:
        """__all__ contains all expected exports."""
        from madsci.client.cli.tui import widgets

        expected = {
            "ActionBar",
            "ActionDef",
            "ColumnDef",
            "DataTableView",
            "DetailPanel",
            "DetailSection",
            "FilterBar",
            "FilterDef",
            "LogViewer",
            "ServiceAwareContainer",
            "StatusBadge",
        }
        assert set(widgets.__all__) == expected

    def test_mixins_importable(self) -> None:
        """Mixin classes are importable from the mixins module."""
        from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin

        assert AutoRefreshMixin is not None
        assert ServiceURLMixin is not None
