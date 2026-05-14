Module madsci.client.cli.tui.widgets.detail_panel
=================================================
DetailPanel widget for MADSci TUI.

Key-value detail display with titled sections. Replaces the duplicated
ServiceDetailPanel, WorkflowDetailPanel, and node detail rendering patterns
found across the existing TUI screens.

Classes
-------

`DetailPanel(*, placeholder: str = 'Select an item to view details', **kwargs: object)`
:   Key-value detail display with titled sections.
    
    Provides a standard pattern for detail panels throughout the TUI:
    a title, followed by one or more sections each containing indented
    key-value pairs.
    
    Usage::
    
        panel = DetailPanel()
        panel.update_content(
            title="Node: robot_arm",
            sections=[
                DetailSection("General", {
                    "URL": "http://localhost:2000/",
                    "Status": "[green]connected[/green]",
                }),
                DetailSection("Actions", {
                    "pick": "Pick up an item",
                    "place": "Place an item",
                }),
            ],
        )
        panel.clear_content()
    
    Initialize the detail panel.
    
    Args:
        placeholder: Text shown when no content has been set.
        **kwargs: Additional keyword arguments forwarded to ``Static``.

    ### Ancestors (in MRO)

    * textual.widgets._static.Static
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `clear_content(self) ‑> None`
    :   Reset the panel to its placeholder state.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the panel with a content label.

    `update_content(self, title: str, sections: list[DetailSection]) ‑> None`
    :   Update the panel with new content.
        
        Args:
            title: Main title displayed at the top of the panel.
            sections: List of sections to display below the title.

`DetailSection(title: ForwardRef('str'), fields: ForwardRef('dict[str, str]'))`
:   A titled section containing key-value pairs.
    
    Attributes:
        title: Section heading text.
        fields: Mapping of field labels to their formatted display values.
            Values may contain Rich markup for coloured output.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `fields: dict[str, str]`
    :   Alias for field number 1

    `title: str`
    :   Alias for field number 0