"""TUI widgets for MADSci.

Reusable Textual widgets extracted from duplicated patterns across TUI
screens. Each widget has a single responsibility and can be composed
into any screen.

Widgets:
    :class:`StatusBadge` -- Coloured status indicator icon with optional text.
    :class:`DetailPanel` -- Key-value detail display with titled sections.
    :class:`DetailSection` -- Named tuple for DetailPanel sections.
    :class:`ServiceAwareContainer` -- Container gated behind service health checks.
    :class:`DataTableView` -- Enhanced DataTable with declarative columns.
    :class:`ColumnDef` -- Column definition for DataTableView.
    :class:`ActionBar` -- Row of keyboard-bound actions.
    :class:`ActionDef` -- Action definition for ActionBar.
    :class:`FilterBar` -- Search input with dropdown filters.
    :class:`FilterDef` -- Filter definition for FilterBar.
    :class:`LogViewer` -- Rich log viewer with follow mode and deduplication.
"""

from madsci.client.cli.tui.widgets.action_bar import ActionBar, ActionDef
from madsci.client.cli.tui.widgets.data_table_view import ColumnDef, DataTableView
from madsci.client.cli.tui.widgets.detail_panel import DetailPanel, DetailSection
from madsci.client.cli.tui.widgets.filter_bar import FilterBar, FilterDef
from madsci.client.cli.tui.widgets.log_viewer import LogViewer
from madsci.client.cli.tui.widgets.service_aware import ServiceAwareContainer
from madsci.client.cli.tui.widgets.status_badge import StatusBadge

__all__ = [
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
]
