Module madsci.workcell_manager.condition_checks
===============================================
Functions for checking conditions on a step

Functions
---------

`check_resource_field(resource: madsci.common.types.resource_types.Resource, condition: madsci.common.types.condition_types.Condition) ‑> bool`
:   check if a resource meets a condition

`evaluate_condition_checks(step: madsci.common.types.step_types.Step, scheduler: madsci.workcell_manager.schedulers.scheduler.AbstractScheduler, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> madsci.common.types.workflow_types.SchedulerMetadata`
:   Check if the specified conditions for the step are met

`evaluate_no_resource_in_location_condition(condition: madsci.common.types.condition_types.NoResourceInLocationCondition, scheduler: madsci.workcell_manager.schedulers.scheduler.AbstractScheduler, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> madsci.common.types.workflow_types.SchedulerMetadata`
:   Check if a resource is not present in a specified location

`evaluate_resource_child_field_check_condition(condition: madsci.common.types.condition_types.ResourceChildFieldCheckCondition, scheduler: madsci.workcell_manager.schedulers.scheduler.AbstractScheduler, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> madsci.common.types.workflow_types.SchedulerMetadata`
:   evalutates a resource childe field condition

`evaluate_resource_field_check_condition(condition: madsci.common.types.condition_types.ResourceFieldCheckCondition, scheduler: madsci.workcell_manager.schedulers.scheduler.AbstractScheduler, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> madsci.common.types.workflow_types.SchedulerMetadata`
:   evaluates a resource field condition

`evaluate_resource_in_location_condition(condition: madsci.common.types.condition_types.ResourceInLocationCondition, scheduler: madsci.workcell_manager.schedulers.scheduler.AbstractScheduler, metadata: madsci.common.types.workflow_types.SchedulerMetadata) ‑> madsci.common.types.workflow_types.SchedulerMetadata`
:   Check if a resource is present in a specified location

`get_resource_from_condition(condition: madsci.common.types.condition_types.Condition, scheduler: madsci.workcell_manager.schedulers.scheduler.AbstractScheduler) ‑> madsci.common.types.resource_types.Resource`
:   gets a resource by the identifiers provided in the condition
