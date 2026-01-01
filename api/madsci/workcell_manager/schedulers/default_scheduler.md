Module madsci.workcell_manager.schedulers.default_scheduler
===========================================================
Default MADSci Workcell scheduler

Classes
-------

`Scheduler(workcell_definition: madsci.common.types.workcell_types.WorkcellManagerDefinition, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler)`
:   This is the default scheduler for the MADSci Workcell Manager. It is a simple FIFO scheduler that checks if the workflow is ready to run.

    - It checks a variety of conditions to determine if a workflow is ready to run. If the workflow is not ready to run, it will add a reason to the scheduler metadata for the workflow.
    - It sets the priority of the workflow based on the order in which the workflows were submitted.

    sets the state handler and workcell definition

    ### Ancestors (in MRO)

    * madsci.workcell_manager.schedulers.scheduler.AbstractScheduler

    ### Methods

    `check_workflow_status(self, wf: madsci.common.types.workflow_types.Workflow, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> None`
    :   Check if the workflow is ready to run (i.e. not paused, not completed, etc.)

    `location_checks(self, step: madsci.common.types.step_types.Step, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> None`
    :   Check if the location(s) for the step are ready

    `node_checks(self, step: madsci.common.types.step_types.Step, wf: madsci.common.types.workflow_types.Workflow, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> None`
    :   Check if the node used in the step currently has a "ready" status

    `resource_checks(self, step: madsci.common.types.step_types.Step, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> None`
    :   Check if the resources for the step are ready TODO: actually check

    `run_iteration(self, workflows: list[madsci.common.types.workflow_types.Workflow]) ‑> dict[str, madsci.common.types.workflow_types.SchedulerMetadata]`
    :   Run an iteration of the scheduling algorithm and return a mapping of workflow IDs to SchedulerMetadata

    `step_checks(self, step: madsci.common.types.step_types.Step, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> None`
    :   Check if the step was not ready recently mark the workflow as not active
