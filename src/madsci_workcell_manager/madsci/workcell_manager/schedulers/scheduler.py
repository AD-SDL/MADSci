"""the abstract class for schedulers"""

from typing import ClassVar, Optional

from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import SchedulerMetadata, Workflow
from madsci.workcell_manager.state_handler import WorkcellStateHandler


class AbstractScheduler:
    """Abstract Implementation of a MADSci Workcell Scheduler.

    All schedulers should:

    - Take a list of MADSci Workflow objects as input to the run_iteration method
    - Set the ready_to_run flag in each workflow's scheduler metadata, optionally setting a list of reasons why the workflow is not ready to run (this is useful for debugging and understanding why a workflow is not running)
    - Set the priority of the workflows, based on whatever criteria the scheduler uses

    The run_iteration method will be called by the WorkcellManager at a regular interval to determine which workflows are ready to run and in what order they should be run. It will then be up to the WorkcellManager to actually run the workflows in the order determined by the scheduler. The scheduler should not actually run the workflows itself. The scheduler should also not modify the workflows or other state.

    """

    workcell_definition: ClassVar[WorkcellDefinition]
    running: bool
    state_handler: WorkcellStateHandler
    logger: Optional[EventClient]
    resource_client: Optional[ResourceClient]

    def __init__(
        self,
        workcell_definition: WorkcellDefinition,
        state_handler: WorkcellStateHandler,
    ) -> "AbstractScheduler":
        """sets the state handler and workcell definition"""
        self.state_handler = state_handler
        self.workcell_definition = workcell_definition
        self.running = True
        self.logger = EventClient()
        self.resource_client = ResourceClient()

    def run_iteration(self, workflows: list[Workflow]) -> dict[str, SchedulerMetadata]:
        """Run an iteration of the scheduler and return a mapping of workflow IDs to SchedulerMetadata"""
        raise NotImplementedError("Subclasses must implement this method")
