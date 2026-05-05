"""Default Error Handler for MADSci Event Manager."""

from event_handler import AbstractErrorHandler
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.event_types import Event


class ErrorHandler(AbstractErrorHandler):
    """Default error handler that pauses workflows for nodes that throw have an error"""

    def __init__(self) -> None:
        """Initialize the error handler."""
        self.workcell_client = WorkcellClient()

    def handle_error(self, event_data: Event) -> None:
        """Handle an error by pausing any active workflows for the node that threw the error."""

        if event_data.source.node_id:
            for id, workflow in self.workcell_client.get_active_workflows().items():
                current_step = workflow.steps[workflow.status.current_step_index]
                node = self.workcell_client.get_node(current_step.node)
                if node.id == event_data.source.node_id:
                    self.workcell_client.pause_workflow(id)
