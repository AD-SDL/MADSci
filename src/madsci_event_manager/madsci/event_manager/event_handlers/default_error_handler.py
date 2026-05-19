"""Default Error Handler for MADSci Event Manager."""

from event_handler import AbstractEventHandler
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.event_types import Event, EventLogLevel, EventManagerSettings


class ErrorHandler(AbstractEventHandler):
    """Default error handler that pauses workflows for nodes that throw an error"""

    def __init__(self, settings: EventManagerSettings) -> None:
        """Initialize the Error handler."""
        super().__init__(settings)
        self.workcell_client = WorkcellClient()

    def handle_event(self, event: Event) -> None:
        """Handle an event by pausing any active workflows for the node that threw the error."""
        if event.log_level >= EventLogLevel.ERROR and event.source.node_id:
            for id, workflow in self.workcell_client.get_active_workflows().items():
                current_step = workflow.steps[workflow.status.current_step_index]
                node = self.workcell_client.get_node(current_step.node)
                if node.id == event.source.node_id:
                    self.workcell_client.pause_workflow(id)
