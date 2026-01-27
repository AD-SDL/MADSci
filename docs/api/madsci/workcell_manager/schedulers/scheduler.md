Module madsci.workcell_manager.schedulers.scheduler
===================================================
the abstract class for schedulers

Classes
-------

`AbstractScheduler(workcell_definition: madsci.common.types.workcell_types.WorkcellManagerDefinition, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler)`
:   Abstract Implementation of a MADSci Workcell Scheduler.

    All schedulers should:

    - Take a list of MADSci Workflow objects as input to the run_iteration method
    - Set the ready_to_run flag in each workflow's scheduler metadata, optionally setting a list of reasons why the workflow is not ready to run (this is useful for debugging and understanding why a workflow is not running)
    - Set the priority of the workflows, based on whatever criteria the scheduler uses

    The run_iteration method will be called by the WorkcellManager at a regular interval to determine which workflows are ready to run and in what order they should be run. It will then be up to the WorkcellManager to actually run the workflows in the order determined by the scheduler. The scheduler should not actually run the workflows itself. The scheduler should also not modify the workflows or other state.

    sets the state handler and workcell definition

    ### Descendants

    * madsci.workcell_manager.schedulers.default_scheduler.Scheduler

    ### Class variables

    `location_client: madsci.client.location_client.LocationClient | None`
    :

    `logger: madsci.client.event_client.EventClient | None`
    :

    `resource_client: madsci.client.resource_client.ResourceClient | None`
    :

    `running: bool`
    :

    `state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler`
    :

    `workcell_definition: ClassVar[madsci.common.types.workcell_types.WorkcellManagerDefinition]`
    :

    ### Methods

    `run_iteration(self, workflows: list[madsci.common.types.workflow_types.Workflow]) ‑> dict[str, madsci.common.types.workflow_types.SchedulerMetadata]`
    :   Run an iteration of the scheduler and return a mapping of workflow IDs to SchedulerMetadata
