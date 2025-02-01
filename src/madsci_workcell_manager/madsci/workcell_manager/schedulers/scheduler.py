"""the abstract class for schedulers"""

from madsci.common.types.event_types import Event
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler


def send_event(test: Event) -> None:  # TODO: remove placeholder
    """send an event to the server"""


class AbstractScheduler:
    """abstract definition of a scheduler"""

    def __init__(
        self,
        workcell_definition: WorkcellDefinition,
        state_handler: WorkcellRedisHandler,
    ) -> "AbstractScheduler":
        """sets the state handler and workcell definition"""
        self.state_handler = state_handler
        self.workcell_definition = workcell_definition
        self.running = True

    def run_iteration(self) -> None:
        """run an iteration of the scheduler"""
