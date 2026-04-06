"""Resource hierarchy tree screen for MADSci TUI.

A pushed screen that visualises the parent-child hierarchy of
a resource using Textual's Tree widget.
"""

from typing import Any, ClassVar

import httpx
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
        resource_url: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the resource tree screen.

        Args:
            resource_id: ID of the resource to display hierarchy for.
            resource_url: Base URL of the resource manager.
            **kwargs: Additional keyword arguments forwarded to Screen.
        """
        super().__init__(**kwargs)
        self.resource_id = resource_id
        self._resource_url = resource_url

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
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fetch the resource itself for its name
                res_response = await client.get(
                    f"{self._resource_url.rstrip('/')}/resource/{self.resource_id}"
                )
                resource: dict[str, Any] = {}
                if res_response.status_code == 200:
                    resource = res_response.json()

                # Fetch hierarchy
                hier_response = await client.get(
                    f"{self._resource_url.rstrip('/')}/resource/"
                    f"{self.resource_id}/hierarchy"
                )
                if hier_response.status_code != 200:
                    tree.root.set_label(
                        f"Error loading hierarchy: HTTP {hier_response.status_code}"
                    )
                    return

                hierarchy = hier_response.json()
                self._build_tree(tree, resource, hierarchy)

        except Exception as e:
            tree.root.set_label(f"Error loading hierarchy: {e}")

    def _build_tree(
        self,
        tree: Tree,
        resource: dict[str, Any],
        hierarchy: dict[str, Any],
    ) -> None:
        """Build the tree widget from hierarchy data.

        Args:
            tree: The Tree widget to populate.
            resource: Resource data dictionary for the root resource.
            hierarchy: Hierarchy response with ancestor_ids and descendant_ids.
        """
        res_name = resource.get("resource_name", self.resource_id[:12])
        res_type = resource.get("base_type", "")
        tree.root.set_label(
            f"[bold]{res_name}[/bold] ({res_type}) [{self.resource_id[:12]}]"
        )
        tree.root.expand()

        descendant_ids: dict[str, list[str]] = hierarchy.get("descendant_ids", {})

        # Show ancestor chain if present
        ancestor_ids: list[str] = hierarchy.get("ancestor_ids", [])
        if ancestor_ids:
            ancestors_node = tree.root.add("[dim]Ancestors[/dim]")
            for anc_id in ancestor_ids:
                ancestors_node.add(f"{anc_id[:12]}...")
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
            node = parent_node.add(f"{child_id[:12]}...")
            self._add_children(node, child_id, descendant_ids)

    def action_go_back(self) -> None:
        """Go back to the resources screen."""
        self.app.pop_screen()
