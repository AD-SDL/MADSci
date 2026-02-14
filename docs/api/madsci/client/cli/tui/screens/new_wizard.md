Module madsci.client.cli.tui.screens.new_wizard
===============================================
Template browser screen for MADSci TUI.

Provides an interactive template browser for ``madsci new --tui``,
allowing users to browse all 26 built-in templates by category
with search filtering before selecting one for generation.

Classes
-------

`CategoryTreeWidget(categories: dict[str, list[dict[str, str]]], **kwargs: Any)`
:   Tree widget showing template categories.

    Initialize with template categories grouped by name.

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the category tree widget.

`TemplateBrowserScreen(**kwargs: Any)`
:   Interactive template browser screen.

    Shows categories in a tree on the left, a searchable table of
    templates on the right, and details for the selected template
    at the bottom.

    Initialize the template browser screen.

    ### Ancestors (in MRO)

    * textual.screen.Screen
    * typing.Generic
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `BINDINGS: ClassVar[list[BindingType]]`
    :

    `CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `action_cancel(self) ‑> None`
    :   Cancel and dismiss the screen.

    `action_focus_search(self) ‑> None`
    :   Focus the search input.

    `action_select_template(self) ‑> None`
    :   Select the highlighted template and dismiss.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the browser layout.

    `on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) ‑> None`
    :   Update detail panel when table row is highlighted.

    `on_data_table_row_selected(self, event: DataTable.RowSelected) ‑> None`
    :   Handle double-click / Enter on table row.

    `on_input_changed(self, event: Input.Changed) ‑> None`
    :   Filter table when search input changes.

    `on_mount(self) ‑> None`
    :   Load templates on mount.

    `on_tree_node_selected(self, event: Tree.NodeSelected) ‑> None`
    :   Handle tree node selection.

`TemplateDetailPanel(content: VisualType = '', *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False)`
:   Panel showing details for the selected template.

    Initialize a Widget.

    Args:
        *children: Child widgets.
        name: The name of the widget.
        id: The ID of the widget in the DOM.
        classes: The CSS classes for the widget.
        disabled: Whether the widget is disabled or not.
        markup: Enable content markup?

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the detail panel.

    `update_detail(self, tmpl: dict[str, str] | None) ‑> None`
    :   Update the detail panel with template info.

`TemplateSelected(template_id: str)`
:   Message sent when a template is selected.

    Initialize with the selected template ID.

    ### Ancestors (in MRO)

    * textual.message.Message

    ### Class variables

    `bubble: ClassVar[bool]`
    :

    `handler_name: ClassVar[str]`
    :

    `no_dispatch: ClassVar[bool]`
    :

    `verbose: ClassVar[bool]`
    :
