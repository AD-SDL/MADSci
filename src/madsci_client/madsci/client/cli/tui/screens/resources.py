"""Resource inventory screen for MADSci TUI.

Provides resource browsing with filtering by type and search,
a detail panel for selected resources, and actions for delete,
lock/unlock, and tree visualization.
"""

import asyncio
from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import (
    AutoRefreshMixin,
    ServiceURLMixin,
    preserve_cursor,
)
from madsci.client.cli.tui.screens.resource_tree import ResourceTreeScreen
from madsci.client.cli.tui.widgets import (
    ActionBar,
    ActionDef,
    DetailPanel,
    DetailSection,
    FilterBar,
    FilterDef,
)
from madsci.client.cli.utils.formatting import format_timestamp
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Label


def _matches_filter(
    res_data: dict,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether a resource matches the current filter criteria.

    Args:
        res_data: Resource data dictionary.
        search: Search text (matched against resource_name, case-insensitive).
        filters: Filter dict; supports ``"type"`` key.

    Returns:
        True if the resource passes the filters.
    """
    type_filter = filters.get("type", "all")
    if (
        type_filter
        and type_filter != "all"
        and res_data.get("base_type", "") != type_filter
    ):
        return False

    if search:
        name = res_data.get("resource_name", "")
        if search.lower() not in name.lower():
            return False

    return True


def _build_general_section(res_id: str, data: dict) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        res_id: Resource ID.
        data: Resource data dictionary.

    Returns:
        DetailSection with general fields.
    """
    fields: dict[str, str] = {
        "Name": data.get("resource_name", "Unknown"),
        "ID": res_id,
        "Base Type": data.get("base_type", "unknown"),
        "Class": data.get("resource_class", "-") or "-",
    }
    desc = data.get("resource_description")
    if desc:
        fields["Description"] = str(desc)[:100]
    return DetailSection("General", fields)


def _build_state_section(data: dict) -> DetailSection | None:
    """Build the quantity/capacity state section.

    Args:
        data: Resource data dictionary.

    Returns:
        DetailSection if quantity or capacity exists, else None.
    """
    quantity = data.get("quantity")
    capacity = data.get("capacity")
    if quantity is None and capacity is None:
        return None

    fields: dict[str, str] = {}
    if quantity is not None:
        fields["Quantity"] = str(quantity)
    if capacity is not None:
        fields["Capacity"] = str(capacity)

    if quantity is not None and capacity is not None:
        try:
            q = float(quantity)
            c = float(capacity)
            if c > 0:
                ratio = q / c
                filled = int(ratio * 20)
                empty = 20 - filled
                bar = "\u2588" * filled + "\u2591" * empty
                percent = int(ratio * 100)
                fields["Utilization"] = f"{bar} {int(q)}/{int(c)} ({percent}%)"
        except (ValueError, TypeError):
            pass

    unit = data.get("unit")
    if unit:
        fields["Unit"] = str(unit)

    return DetailSection("State", fields)


def _build_hierarchy_section(data: dict) -> DetailSection | None:
    """Build the hierarchy section.

    Args:
        data: Resource data dictionary.

    Returns:
        DetailSection if parent or children info exists, else None.
    """
    fields: dict[str, str] = {}
    parent_id = data.get("parent_id")
    if parent_id:
        fields["Parent ID"] = str(parent_id)
    key = data.get("key")
    if key:
        fields["Key"] = str(key)
    if fields:
        return DetailSection("Hierarchy", fields)
    return None


def _build_ownership_section(data: dict) -> DetailSection | None:
    """Build the ownership section.

    Args:
        data: Resource data dictionary.

    Returns:
        DetailSection if ownership info exists, else None.
    """
    owner = data.get("owner") or {}
    if not isinstance(owner, dict):
        return None
    fields: dict[str, str] = {}
    for key in ("user_id", "experiment_id", "campaign_id"):
        value = owner.get(key)
        if value:
            fields[key.replace("_", " ").title()] = str(value)
    if fields:
        return DetailSection("Ownership", fields)
    return None


def _build_timestamps_section(data: dict) -> DetailSection | None:
    """Build the timestamps section.

    Args:
        data: Resource data dictionary.

    Returns:
        DetailSection if any timestamp exists, else None.
    """
    fields: dict[str, str] = {}
    created = data.get("created_at")
    updated = data.get("updated_at")
    if created:
        fields["Created"] = format_timestamp(created, short=True)
    if updated:
        fields["Updated"] = format_timestamp(updated, short=True)
    if fields:
        return DetailSection("Timestamps", fields)
    return None


def _build_attributes_section(data: dict) -> DetailSection | None:
    """Build the custom attributes section.

    Args:
        data: Resource data dictionary.

    Returns:
        DetailSection if custom attributes exist, else None.
    """
    attrs = data.get("attributes") or {}
    if not isinstance(attrs, dict) or not attrs:
        return None
    fields = {str(k): str(v)[:80] for k, v in attrs.items()}
    return DetailSection("Attributes", fields)


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal confirmation dialog for resource deletion."""

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    ConfirmDeleteScreen #confirm-dialog {
        width: 60;
        height: auto;
        border: thick $error;
        padding: 1 2;
        background: $surface;
    }
    ConfirmDeleteScreen Button {
        margin: 1 1 0 0;
    }
    """

    def __init__(self, resource_id: str, resource_name: str, **kwargs: Any) -> None:
        """Initialize the confirmation screen."""
        super().__init__(**kwargs)
        self._resource_id = resource_id
        self._resource_name = resource_name

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        with VerticalScroll(id="confirm-dialog"):
            yield Label("[bold red]Delete Resource[/bold red]")
            yield Label("")
            yield Label(
                f"Are you sure you want to delete [bold]{self._resource_name}[/bold]?"
            )
            yield Label(f"[dim]{self._resource_id}[/dim]")
            yield Label("")
            with Horizontal():
                yield Button("Delete", id="confirm-delete", variant="error")
                yield Button("Cancel", id="cancel-delete", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(event.button.id == "confirm-delete")


class ResourcesScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing resource inventory and management."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("n", "new_resource", "New"),
        ("d", "delete_resource", "Delete"),
        ("l", "toggle_lock", "Lock/Unlock"),
        ("t", "show_tree", "Tree"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.resources_data: dict[str, dict] = {}
        self.selected_resource_id: str | None = None
        self._resource_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the resources screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label("[bold blue]Resource Inventory[/bold blue]")
            yield Label("")

            yield FilterBar(
                search_placeholder="Search resources...",
                filters=[
                    FilterDef(
                        "type",
                        "Type",
                        [
                            ("all", "All"),
                            ("asset", "Asset"),
                            ("consumable", "Consumable"),
                            ("discrete_consumable", "Discrete"),
                            ("continuous_consumable", "Continuous"),
                            ("container", "Container"),
                            ("collection", "Collection"),
                            ("stack", "Stack"),
                            ("queue", "Queue"),
                            ("row", "Row"),
                            ("grid", "Grid"),
                            ("pool", "Pool"),
                            ("slot", "Slot"),
                        ],
                        default="all",
                    ),
                ],
                id="resource-filter",
            )

            yield Label("")
            yield DataTable(id="resources-table")
            yield Label("")
            yield DetailPanel(
                placeholder="Select a resource from the table above",
                id="resource-detail-panel",
            )
            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                    ActionDef("n", "New", "new_resource", variant="primary"),
                    ActionDef("d", "Delete", "delete_resource", variant="error"),
                    ActionDef("l", "Lock/Unlock", "toggle_lock", variant="warning"),
                    ActionDef("t", "Tree", "show_tree", variant="primary"),
                ],
                id="resource-action-bar",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up table and load data."""
        table = self.query_one("#resources-table", DataTable)
        table.add_columns(
            "Name", "ID", "Type", "Quantity", "Capacity", "Parent", "Lock"
        )
        table.cursor_type = "row"
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh resource data from the resource manager."""
        self.resources_data.clear()
        self._resource_ids.clear()

        try:
            resource_url = self.get_service_url("resource_manager")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{resource_url.rstrip('/')}/resource/query",
                    json={"multiple": True},
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for res in data:
                            res_id = res.get("resource_id", "")
                            if res_id:
                                self.resources_data[res_id] = res
                                self._resource_ids.append(res_id)
        except Exception:  # noqa: S110
            pass

        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the resources table with filtered data."""
        table = self.query_one("#resources-table", DataTable)

        filtered = [
            res_id
            for res_id in self._resource_ids
            if res_id in self.resources_data
            and _matches_filter(
                self.resources_data[res_id],
                self._current_search,
                self._current_filters,
            )
        ]

        with preserve_cursor(table):
            table.clear()

            for res_id in filtered:
                res = self.resources_data[res_id]
                name = res.get("resource_name", "Unknown")
                res_id_str = res_id or "-"
                base_type = res.get("base_type", "unknown")
                quantity = (
                    str(res.get("quantity", "-"))
                    if res.get("quantity") is not None
                    else "-"
                )
                capacity = (
                    str(res.get("capacity", "-"))
                    if res.get("capacity") is not None
                    else "-"
                )
                parent = str(res.get("parent_id", "")) if res.get("parent_id") else "-"
                lock = ""  # Lock status requires a separate API call
                table.add_row(
                    name, res_id_str, base_type, quantity, capacity, parent, lock
                )

            if not filtered:
                table.add_row(
                    "[dim]No resources found[/dim]", "-", "-", "-", "-", "-", ""
                )

    def on_filter_bar_filter_changed(self, event: FilterBar.FilterChanged) -> None:
        """Handle filter changes from the FilterBar.

        Args:
            event: The filter changed event with search and filters.
        """
        self._current_search = event.search
        self._current_filters = event.filters
        self._populate_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the resources table.

        Args:
            event: The row selected event.
        """
        table = event.data_table
        row_key = event.row_key
        if not row_key:
            return

        row = table.get_row(row_key)
        row_id = str(row[1])

        # Find resource by matching full ID
        for res_id, res_data in self.resources_data.items():
            if res_id == row_id:
                self.selected_resource_id = res_id
                self._update_detail_panel(res_id, res_data)
                break

    def _update_detail_panel(self, resource_id: str, data: dict) -> None:
        """Update the detail panel with resource data.

        Args:
            resource_id: Resource ID.
            data: Resource data dictionary.
        """
        detail_panel = self.query_one("#resource-detail-panel", DetailPanel)
        name = data.get("resource_name", "Unknown")

        sections: list[DetailSection] = [_build_general_section(resource_id, data)]

        state_section = _build_state_section(data)
        if state_section:
            sections.append(state_section)

        hierarchy_section = _build_hierarchy_section(data)
        if hierarchy_section:
            sections.append(hierarchy_section)

        ownership_section = _build_ownership_section(data)
        if ownership_section:
            sections.append(ownership_section)

        timestamps_section = _build_timestamps_section(data)
        if timestamps_section:
            sections.append(timestamps_section)

        attributes_section = _build_attributes_section(data)
        if attributes_section:
            sections.append(attributes_section)

        detail_panel.update_content(title=name, sections=sections)

    async def action_refresh(self) -> None:
        """Refresh resource data."""
        await self.refresh_data()
        self.notify("Resources refreshed", timeout=2)

    async def action_new_resource(self) -> None:
        """Notify user to use CLI for resource creation."""
        self.notify(
            "Use 'madsci resource create' CLI command to create resources",
            timeout=3,
        )

    def action_delete_resource(self) -> None:
        """Prompt for confirmation before deleting the selected resource."""
        if not self.selected_resource_id:
            self.notify("No resource selected", timeout=2)
            return

        res_data = self.resources_data.get(self.selected_resource_id, {})
        name = res_data.get("resource_name", self.selected_resource_id)

        self.app.push_screen(
            ConfirmDeleteScreen(
                resource_id=self.selected_resource_id,
                resource_name=name,
            ),
            callback=self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        """Handle confirmation result from the delete screen."""
        if confirmed:
            self.run_worker(self._perform_delete())

    async def _perform_delete(self) -> None:
        """Execute the resource deletion after confirmation."""
        if not self.selected_resource_id:
            return

        try:
            resource_url = self.get_service_url("resource_manager")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    f"{resource_url.rstrip('/')}/resource/{self.selected_resource_id}"
                )
                if response.status_code == 200:
                    self.notify("Resource deleted", timeout=2)
                    self.selected_resource_id = None
                    detail_panel = self.query_one("#resource-detail-panel", DetailPanel)
                    detail_panel.clear_content()
                    await self.refresh_data()
                else:
                    self.notify(
                        f"Failed to delete resource: HTTP {response.status_code}",
                        timeout=3,
                    )
        except Exception as e:
            self.notify(f"Error deleting resource: {e}", timeout=3)

    async def action_toggle_lock(self) -> None:
        """Toggle lock on the selected resource."""
        if not self.selected_resource_id:
            self.notify("No resource selected", timeout=2)
            return

        try:
            resource_url = self.get_service_url("resource_manager")
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check current lock status
                check_response = await client.get(
                    f"{resource_url.rstrip('/')}/resource/"
                    f"{self.selected_resource_id}/check_lock"
                )
                if check_response.status_code != 200:
                    self.notify("Failed to check lock status", timeout=3)
                    return

                lock_info = check_response.json()
                is_locked = lock_info.get("is_locked", False)

                if is_locked:
                    # Release lock
                    response = await client.delete(
                        f"{resource_url.rstrip('/')}/resource/"
                        f"{self.selected_resource_id}/unlock"
                    )
                    if response.status_code == 200:
                        self.notify("Resource unlocked", timeout=2)
                    else:
                        self.notify(
                            f"Failed to unlock: HTTP {response.status_code}",
                            timeout=3,
                        )
                else:
                    # Acquire lock
                    response = await client.post(
                        f"{resource_url.rstrip('/')}/resource/"
                        f"{self.selected_resource_id}/lock",
                        params={"lock_duration": 300, "client_id": "tui"},
                    )
                    if response.status_code == 200:
                        self.notify("Resource locked", timeout=2)
                    else:
                        self.notify(
                            f"Failed to lock: HTTP {response.status_code}",
                            timeout=3,
                        )
        except Exception as e:
            self.notify(f"Error toggling lock: {e}", timeout=3)

    def action_show_tree(self) -> None:
        """Show the resource tree for the selected resource."""
        if not self.selected_resource_id:
            self.notify("No resource selected", timeout=2)
            return

        resource_url = self.get_service_url("resource_manager")
        self.app.push_screen(
            ResourceTreeScreen(
                resource_id=self.selected_resource_id,
                resource_url=resource_url,
            )
        )

    def on_action_bar_action_triggered(self, event: ActionBar.ActionTriggered) -> None:
        """Route ActionBar button triggers to screen actions."""
        action_map = {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
            "new_resource": self.action_new_resource,
            "delete_resource": self.action_delete_resource,
            "toggle_lock": self.action_toggle_lock,
            "show_tree": self.action_show_tree,
        }
        handler = action_map.get(event.action)
        if handler is not None:
            if asyncio.iscoroutinefunction(handler):
                self.run_worker(handler())
            else:
                handler()

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
