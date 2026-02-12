Module madsci.workcell_manager.workflow_utils
=============================================
Utility function for the workcell manager.

Functions
---------

`cancel_active_workflows(state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler) ‑> None`
:   Cancels all currently running workflow runs

`cancel_workflow(wf: madsci.common.types.workflow_types.Workflow, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler) ‑> None`
:   Cancels the workflow run

`check_json_parameters(workflow_definition: madsci.common.types.workflow_types.WorkflowDefinition, json_inputs: dict[str, typing.Any] | None) ‑> None`
:   Check that all required JSON parameters are provided

`check_parameters(workflow_definition: madsci.common.types.workflow_types.WorkflowDefinition, json_inputs: dict[str, typing.Any] | None = None, file_input_paths: dict[str, str] | None = None) ‑> None`
:   Check that all required parameters are provided

`copy_workflow_files(working_directory: str, old_id: str, workflow: madsci.common.types.workflow_types.Workflow) ‑> madsci.common.types.workflow_types.Workflow`
:   Saves the files to the workflow run directory,
    and updates the step files to point to the new location

`create_workflow(workflow_def: madsci.common.types.workflow_types.WorkflowDefinition, workcell: madsci.common.types.workcell_types.WorkcellManagerDefinition, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler, json_inputs: dict[str, typing.Any] | None = None, file_input_paths: dict[str, str] | None = None, location_client: madsci.client.location_client.LocationClient | None = None) ‑> madsci.common.types.workflow_types.Workflow`
:   Pulls the workcell and builds a list of dictionary steps to be executed

    Parameters
    ----------
    workflow_def: WorkflowDefintion
        The workflow data file loaded in from the workflow yaml file

    workcell : Workcell
        The Workcell object stored in the database

    parameters: Dict
        The input to the workflow

    ownership_info: OwnershipInfo
        Information on the owner(s) of the workflow

    simulate: bool
        Whether or not to use real robots

    Returns
    -------
    steps: WorkflowRun
        a completely initialized workflow run

`get_workflow_inputs_directory(workflow_id: str | None = None, working_directory: str | None = None) ‑> pathlib.Path`
:   returns a directory name for the workflows inputs

`insert_parameters(step: madsci.common.types.step_types.Step, parameter_values: dict[str, typing.Any]) ‑> madsci.common.types.step_types.Step`
:   Replace parameter values in a provided step

`prepare_workflow_files(step: madsci.common.types.step_types.Step, workflow: madsci.common.types.workflow_types.Workflow, data_client: madsci.client.data_client.DataClient) ‑> madsci.common.types.step_types.Step`
:   Get workflow files ready to upload

`prepare_workflow_step(workcell: madsci.common.types.workcell_types.WorkcellManagerDefinition, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler, step: madsci.common.types.step_types.Step, workflow: madsci.common.types.workflow_types.Workflow, data_client: madsci.client.data_client.DataClient | None = None, location_client: madsci.client.location_client.LocationClient | None = None) ‑> madsci.common.types.step_types.Step`
:   Prepares a step for execution by replacing locations and validating it

`replace_locations(workcell: madsci.common.types.workcell_types.WorkcellManagerDefinition, step: madsci.common.types.step_types.Step, location_client: madsci.client.location_client.LocationClient | None = None) ‑> None`
:   Replaces the location names with the location objects

`save_workflow_files(workflow: madsci.common.types.workflow_types.Workflow, files: list[fastapi.datastructures.UploadFile], data_client: madsci.client.data_client.DataClient) ‑> madsci.common.types.workflow_types.Workflow`
:   Saves the files to the workflow run directory,
    and updates the step files to point to the new location

`validate_node_names(workflow: madsci.common.types.workflow_types.Workflow, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler) ‑> None`
:   Validates that the nodes in the workflow.step are in the workcell's nodes

`validate_step(step: madsci.common.types.step_types.Step, state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler, feedforward_parameters: list[typing.Annotated[madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterInputFile | madsci.common.types.parameter_types.ParameterFeedForwardJson | madsci.common.types.parameter_types.ParameterFeedForwardFile, Discriminator(discriminator='parameter_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)]]) ‑> tuple[bool, str]`
:   Check if a step is valid based on the node's info

`validate_workcell_action_step(step: madsci.common.types.step_types.Step) ‑> tuple[bool, str]`
:   Check if a step calling a workcell action is  valid
