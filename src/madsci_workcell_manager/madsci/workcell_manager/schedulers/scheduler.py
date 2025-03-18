"""the abstract class for schedulers"""

from typing import ClassVar, Optional

from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.event_types import Event
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler


def send_event(test: Event) -> None:  # TODO: remove placeholder
    """send an event to the server"""


class AbstractScheduler:
    """abstract definition of a scheduler"""

    workcell_definition: ClassVar[WorkcellDefinition]
    running: bool
    state_handler: WorkcellRedisHandler
    logger: Optional[EventClient]
    resource_client: Optional[ResourceClient]

    def __init__(
        self,
        workcell_definition: WorkcellDefinition,
        state_handler: WorkcellRedisHandler,
    ) -> "AbstractScheduler":
        """sets the state handler and workcell definition"""
        self.state_handler = state_handler
        self.workcell_definition = workcell_definition
        self.running = True
        self.logger = EventClient(
            config=self.workcell_definition.config.event_client_config
        )
        if self.workcell_definition.config.resource_server_url is not None:
            self.resource_client = ResourceClient(
                url=self.workcell_definition.config.resource_server_url
            )
        else:
            self.resource_client = None

    def run_iteration(self, workflows: list[Workflow]) -> None:
        """Run an iteration of the scheduler"""
