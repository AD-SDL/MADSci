"""TUI screens for MADSci.

This module contains the screen implementations for the MADSci TUI.
"""

from madsci.client.cli.tui.screens.dashboard import DashboardScreen
from madsci.client.cli.tui.screens.logs import LogsScreen
from madsci.client.cli.tui.screens.nodes import NodesScreen
from madsci.client.cli.tui.screens.resource_tree import ResourceTreeScreen
from madsci.client.cli.tui.screens.resources import ResourcesScreen
from madsci.client.cli.tui.screens.status import StatusScreen
from madsci.client.cli.tui.screens.step_detail import StepDetailScreen
from madsci.client.cli.tui.screens.workflows import WorkflowsScreen

__all__ = [
    "DashboardScreen",
    "LogsScreen",
    "NodesScreen",
    "ResourceTreeScreen",
    "ResourcesScreen",
    "StatusScreen",
    "StepDetailScreen",
    "WorkflowsScreen",
]
