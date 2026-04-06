Module madsci.client.cli.tui.screens.experiments
================================================
Experiment management screen for MADSci TUI.

Provides experiment browsing with filtering by name and status,
a detail panel for selected experiments, and actions for pause,
continue, and cancel operations.

Classes
-------

`ExperimentsScreen(**kwargs: Any)`
:   Screen showing experiment management and monitoring.
    
    Initialize the screen.

    ### Ancestors (in MRO)

    * madsci.client.cli.tui.mixins.AutoRefreshMixin
    * madsci.client.cli.tui.mixins.ServiceURLMixin
    * textual.screen.Screen
    * typing.Generic
    * textual.widget.Widget
    * textual.dom.DOMNode
    * textual.message_pump.MessagePump

    ### Class variables

    `BINDINGS: ClassVar[list['Binding | tuple[str, str] | tuple[str, str, str]']]`
    :

    `can_focus`
    :

    `can_focus_children`
    :

    ### Methods

    `action_cancel_experiment(self) ‑> None`
    :   Cancel the selected experiment.

    `action_continue_experiment(self) ‑> None`
    :   Continue the selected experiment.

    `action_go_back(self) ‑> None`
    :   Go back to the dashboard.

    `action_pause_experiment(self) ‑> None`
    :   Pause the selected experiment.

    `action_refresh(self) ‑> None`
    :   Refresh experiment data.

    `compose(self) ‑> Iterable[textual.widget.Widget]`
    :   Compose the experiments screen layout.

    `on_data_table_row_selected(self, event: textual.widgets._data_table.DataTable.RowSelected) ‑> None`
    :   Handle row selection in the experiments table.
        
        Args:
            event: The row selected event.

    `on_filter_bar_filter_changed(self, event: madsci.client.cli.tui.widgets.filter_bar.FilterBar.FilterChanged) ‑> None`
    :   Handle filter changes from the FilterBar.
        
        Args:
            event: The filter changed event with search and filters.

    `on_mount(self) ‑> None`
    :   Handle screen mount - set up table and load data.

    `refresh_data(self) ‑> None`
    :   Refresh experiment data from the experiment manager.