"""the abstract class for schedulers"""

from madsci.common.types.event_types import Event
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.workcell_manager_types import WorkcellManagerDefinition


def send_event(test: Event) -> None:  # TODO: remove placeholder
    """send an event to the server"""


class AbstractScheduler:
    """abstract definition of a scheduler"""

    def __init__(
        self,
        workcell_manager_definition: WorkcellManagerDefinition,
        state_handler: WorkcellRedisHandler,
    ) -> "AbstractScheduler":
        """sets the state handler and workcell definition"""
        self.state_handler = state_handler
        self.workcell_manager_definition = workcell_manager_definition
        self.running = True

    def run_iteration(self) -> None:
        """run an iteration of the scheduler"""
