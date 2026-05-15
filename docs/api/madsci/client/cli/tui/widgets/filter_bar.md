Module madsci.client.cli.tui.widgets.filter_bar
===============================================
FilterBar widget for MADSci TUI.

Search input with optional dropdown filters. Emits :class:`FilterChanged`
messages when any filter value changes.

Classes
-------

`FilterBar(*, search_placeholder: str = 'Search...', filters: list[FilterDef] | None = None, **kwargs: Any)`
:   Search input with optional dropdown filters.
    
    Emits :class:`FilterChanged` whenever the search text is submitted
    or any dropdown selection changes.
    
    Usage::
    
        yield FilterBar(
            search_placeholder="Search events...",
            filters=[
                FilterDef(
                    name="level",
                    label="Level",
                    options=[("all", "All"), ("info", "Info"), ("error", "Error")],
                    default="all",
                ),
            ],
        )
    
    Initialize the filter bar.
    
    Args:
        search_placeholder: Placeholder text for the search input.
        filters: Optional list of dropdown filter definitions.
        **kwargs: Additional keyword arguments forwarded to ``Widget``.

    ### Ancestors (in MRO)

    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `DEFAULT_CSS`
    :

    `FilterChanged`
    :   Posted when any filter value changes.
        
        Attributes:
            search: Current search text.
            filters: Mapping of filter names to their selected values.

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the filter bar layout.

    `get_filter_values(self) ‑> dict[str, typing.Any]`
    :   Get the current values of all dropdown filters.
        
        Returns:
            Mapping of filter names to selected values.

    `get_search_text(self) ‑> str`
    :   Get the current search input text.
        
        Returns:
            Current text in the search input.

    `on_input_submitted(self, _event: Input.Submitted) ‑> None`
    :   Handle search text submission.

    `on_select_changed(self, _event: Select.Changed) ‑> None`
    :   Handle dropdown filter changes.

`FilterDef(name: ForwardRef('str'), label: ForwardRef('str'), options: ForwardRef('list[tuple[str, str]]'), default: ForwardRef('str') = '')`
:   Definition for a dropdown filter in the :class:`FilterBar`.
    
    Attributes:
        name: Internal name used as key in the filters dict.
        label: Display label for the dropdown (used as the first
            option when ``default`` is empty).
        options: List of ``(value, display_text)`` tuples.
        default: Default selected value. Empty string means no selection.

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `default: str`
    :   Alias for field number 3

    `label: str`
    :   Alias for field number 1

    `name: str`
    :   Alias for field number 0

    `options: list[tuple[str, str]]`
    :   Alias for field number 2