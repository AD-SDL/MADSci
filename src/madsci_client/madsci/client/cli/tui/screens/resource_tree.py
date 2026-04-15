"""Resource hierarchy tree screen for MADSci TUI.

A pushed screen that visualises the parent-child hierarchy of
a resource using Textual's Tree widget.
"""

from __future__ import annotations

from typing import Any, ClassVar

from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import ResourceDataModels
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Label, Tree


class ResourceTreeScreen(Screen):
    """Screen showing the resource hierarchy as a tree."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(
        self,
        resource_id: str,
        resource_client: ResourceClient,
        **kwargs: Any,
    ) -> None:
        """Initialize the resource tree screen.

        Args:
            resource_id: ID of the resource to display hierarchy for.
            resource_client: ResourceClient instance for API calls.
            **kwargs: Additional keyword arguments forwarded to Screen.
        """
        super().__init__(**kwargs)
        self.resource_id = resource_id
        self._resource_client = resource_client

    def compose(self) -> ComposeResult:
        """Compose the tree screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Resource Hierarchy[/bold blue]")
            yield Label("")
            yield Tree("Loading...")

    async def on_mount(self) -> None:
        """Handle mount - fetch hierarchy and build tree."""
        tree = self.query_one(Tree)
        try:
            # Fetch the resource itself for its name
            resource = await self._resource_client.async_get_resource(self.resource_id)

            # Fetch hierarchy
            hierarchy = await self._resource_client.async_query_resource_hierarchy(
                self.resource_id
            )
            self._build_tree(tree, resource, hierarchy)

        except Exception as e:
            tree.root.set_label(f"Error loading hierarchy: {e}")

    def _build_tree(
        self,
        tree: Tree,
        resource: ResourceDataModels,
        hierarchy: ResourceHierarchy,
    ) -> None:
        """Build the tree widget from hierarchy data.

        Args:
            tree: The Tree widget to populate.
            resource: Resource model instance for the root resource.
            hierarchy: ResourceHierarchy model with ancestor_ids and descendant_ids.
        """
        res_name = resource.resource_name or self.resource_id
        res_type = resource.base_type.value if resource.base_type else ""
        tree.root.set_label(
            f"[bold]{res_name}[/bold] ({res_type}) [{self.resource_id}]"
        )
        tree.root.expand()

        descendant_ids: dict[str, list[str]] = hierarchy.descendant_ids or {}

        # Show ancestor chain if present
        ancestor_ids: list[str] = hierarchy.ancestor_ids or []
        if ancestor_ids:
            ancestors_node = tree.root.add("[dim]Ancestors[/dim]")
            for anc_id in ancestor_ids:
                ancestors_node.add(f"{anc_id}")
            ancestors_node.expand()

        # Add descendants recursively
        self._add_children(tree.root, self.resource_id, descendant_ids)

    def _add_children(
        self,
        parent_node: Any,
        parent_id: str,
        descendant_ids: dict[str, list[str]],
    ) -> None:
        """Recursively add child nodes to the tree.

        Args:
            parent_node: The parent tree node to add children to.
            parent_id: The parent resource ID.
            descendant_ids: Mapping of parent IDs to child ID lists.
        """
        children = descendant_ids.get(parent_id, [])
        for child_id in children:
            node = parent_node.add(f"{child_id}")
            self._add_children(node, child_id, descendant_ids)

    def action_go_back(self) -> None:
        """Go back to the resources screen."""
        self.app.pop_screen()
