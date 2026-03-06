"""Template browser screen for MADSci TUI.

Provides an interactive template browser for ``madsci new --tui``,
allowing users to browse all 26 built-in templates by category
with search filtering before selecting one for generation.
"""

from __future__ import annotations

from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    Tree,
)


class TemplateSelected(Message):
    """Message sent when a template is selected."""

    def __init__(self, template_id: str) -> None:
        """Initialize with the selected template ID."""
        self.template_id = template_id
        super().__init__()


class CategoryTreeWidget(Static):
    """Tree widget showing template categories."""

    def __init__(
        self, categories: dict[str, list[dict[str, str]]], **kwargs: Any
    ) -> None:
        """Initialize with template categories grouped by name."""
        super().__init__(**kwargs)
        self.categories = categories

    def compose(self) -> ComposeResult:
        """Compose the category tree widget."""
        tree: Tree[str] = Tree("Templates", id="category-tree")
        tree.root.expand()
        for cat_name in sorted(self.categories.keys()):
            cat_node = tree.root.add(cat_name.title(), data=cat_name, expand=True)
            for tmpl in self.categories[cat_name]:
                cat_node.add_leaf(tmpl["name"], data=tmpl["id"])
        yield tree


class TemplateDetailPanel(Static):
    """Panel showing details for the selected template."""

    def compose(self) -> ComposeResult:
        """Compose the detail panel."""
        yield Label("Select a template from the tree or table.", id="detail-text")

    def update_detail(self, tmpl: dict[str, str] | None) -> None:
        """Update the detail panel with template info."""
        label = self.query_one("#detail-text", Label)
        if tmpl is None:
            label.update("Select a template from the tree or table.")
            return

        lines = [
            f"[bold]{tmpl.get('name', '')}[/bold]",
            f"ID: [cyan]{tmpl.get('id', '')}[/cyan]",
            "",
            tmpl.get("description", ""),
            "",
            f"Category: {tmpl.get('category', '')}",
        ]
        if tmpl.get("tags"):
            lines.append(f"Tags: {tmpl['tags']}")
        lines.append("")
        lines.append("[dim]Press Enter to select this template.[/dim]")
        label.update("\n".join(lines))


class TemplateBrowserScreen(Screen):
    """Interactive template browser screen.

    Shows categories in a tree on the left, a searchable table of
    templates on the right, and details for the selected template
    at the bottom.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select_template", "Select"),
        ("/", "focus_search", "Search"),
    ]

    CSS = """
    TemplateBrowserScreen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: auto 1fr auto;
        grid-columns: 1fr 2fr;
    }

    #search-bar {
        column-span: 2;
        height: 3;
        padding: 0 1;
    }

    #category-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #template-table-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #detail-panel {
        column-span: 2;
        height: auto;
        min-height: 8;
        max-height: 12;
        border: solid $primary;
        padding: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the template browser screen."""
        super().__init__(**kwargs)
        self._templates: list[dict[str, str]] = []
        self._by_category: dict[str, list[dict[str, str]]] = {}
        self._selected_id: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the browser layout."""
        yield Header()
        yield Input(placeholder="Search templates...", id="search-bar")
        yield Vertical(id="category-panel")
        yield Vertical(
            DataTable(id="template-table"),
            id="template-table-panel",
        )
        yield TemplateDetailPanel(id="detail-panel")
        yield Footer()

    async def on_mount(self) -> None:
        """Load templates on mount."""
        self._load_templates()
        self._build_category_tree()
        self._populate_table()

    def _load_templates(self) -> None:
        """Load templates from the registry."""
        from madsci.common.templates.registry import TemplateRegistry

        registry = TemplateRegistry()
        templates = registry.list_templates()

        self._templates = []
        self._by_category = {}

        for t in templates:
            tmpl = {
                "id": str(t.id),
                "name": str(t.name),
                "description": str(t.description),
                "category": str(t.category.value) if t.category else "",
                "tags": ", ".join(t.tags) if hasattr(t, "tags") and t.tags else "",
            }
            self._templates.append(tmpl)
            cat = tmpl["category"]
            if cat not in self._by_category:
                self._by_category[cat] = []
            self._by_category[cat].append(tmpl)

    def _build_category_tree(self) -> None:
        """Build the category tree in the left panel."""
        panel = self.query_one("#category-panel", Vertical)
        tree: Tree[str] = Tree("Templates", id="category-tree")
        tree.root.expand()
        for cat_name in sorted(self._by_category.keys()):
            cat_node = tree.root.add(cat_name.title(), data=cat_name, expand=True)
            for tmpl in self._by_category[cat_name]:
                cat_node.add_leaf(tmpl["name"], data=tmpl["id"])
        panel.mount(tree)

    def _populate_table(self, filter_text: str = "") -> None:
        """Populate the template table, optionally filtered."""
        table = self.query_one("#template-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Name", "Description")
        table.cursor_type = "row"

        filter_lower = filter_text.lower()

        for tmpl in self._templates:
            if filter_lower and not any(
                filter_lower in tmpl[field].lower()
                for field in ("id", "name", "description", "category", "tags")
            ):
                continue
            table.add_row(
                tmpl["id"],
                tmpl["name"],
                tmpl["description"][:60],
                key=tmpl["id"],
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter table when search input changes."""
        if event.input.id == "search-bar":
            self._populate_table(filter_text=event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update detail panel when table row is highlighted."""
        if event.row_key is not None:
            row_key = str(event.row_key.value)
            tmpl = next((t for t in self._templates if t["id"] == row_key), None)
            detail = self.query_one("#detail-panel", TemplateDetailPanel)
            detail.update_detail(tmpl)
            self._selected_id = row_key

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node_data = event.node.data
        if node_data and "/" in str(node_data):
            # It's a template ID (category/name)
            tmpl = next((t for t in self._templates if t["id"] == node_data), None)
            detail = self.query_one("#detail-panel", TemplateDetailPanel)
            detail.update_detail(tmpl)
            self._selected_id = str(node_data)
        elif node_data:
            # It's a category - filter the table
            self._populate_table(filter_text=str(node_data))

    def action_cancel(self) -> None:
        """Cancel and dismiss the screen."""
        self.dismiss(None)

    def action_select_template(self) -> None:
        """Select the highlighted template and dismiss."""
        if self._selected_id:
            self.dismiss(self._selected_id)
        else:
            self.notify("No template selected.", severity="warning")

    def action_focus_search(self) -> None:
        """Focus the search input."""
        search = self.query_one("#search-bar", Input)
        search.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle double-click / Enter on table row."""
        if event.row_key is not None:
            self._selected_id = str(event.row_key.value)
            self.dismiss(self._selected_id)
