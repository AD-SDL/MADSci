Module madsci.workcell_manager.workcell_engine
==============================================
Engine Class and associated helpers and data

Classes
-------

`Engine(state_handler: madsci.workcell_manager.state_handler.WorkcellStateHandler, data_client: madsci.client.data_client.DataClient)`
:   Handles scheduling workflows and executing steps on the workcell.
    Pops incoming workflows off a redis-based queue and executes them.

    Initialize the scheduler.

    ### Methods

    `finalize_step(self, workflow_id: str, step: madsci.common.types.step_types.Step) ‑> None`
    :   Finalize the step, updating the workflow based on the results (setting status, updating index, etc.)

    `handle_data_and_files(self, step: madsci.common.types.step_types.Step, wf: madsci.common.types.workflow_types.Workflow, response: madsci.common.types.action_types.ActionResult) ‑> madsci.common.types.action_types.ActionResult`
    :   Upload non-datapoint results as datapoints and consolidate all datapoint IDs.

        This method ensures that all results (JSON data, files) are stored as datapoints
        in the data manager, following the principle of getting data into the data manager ASAP.
        The response datapoints field will contain only ULID strings for efficient storage.

    `handle_response(self, wf: madsci.common.types.workflow_types.Workflow, step: madsci.common.types.step_types.Step, response: madsci.common.types.action_types.ActionResult) ‑> madsci.common.types.action_types.ActionResult | None`
    :   Handle the response from the node

    `monitor_action_progress(self, wf: madsci.common.types.workflow_types.Workflow, step: madsci.common.types.step_types.Step, node: madsci.common.types.node_types.Node, client: madsci.client.node.abstract_node_client.AbstractNodeClient, response: madsci.common.types.action_types.ActionResult, request: madsci.common.types.action_types.ActionRequest, action_id: str) ‑> None`
    :   Monitor the progress of the action, querying the action result until it is terminal

    `reset_disconnects(self) ‑> None`
    :   Reset all disconnected nodes to initializing state.

    `run_next_step(self, await_step_completion: bool = False) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Runs the next step in the workflow with the highest priority. Returns information about the workflow it ran, if any.

    `run_step(self, workflow_id: str) ‑> None`
    :   Run a step in a standalone thread, updating the workflow as needed

    `run_workcell_action(self, step: madsci.common.types.step_types.Step) ‑> madsci.common.types.step_types.Step`
    :   Runs one of the built-in workcell actions

    `spin(self) ‑> None`
    :   Continuously loop, updating node states every Config.update_interval seconds.
        If the state of the workcell has changed, update the active modules and run the scheduler.

    `update_active_nodes(self, state_manager: madsci.workcell_manager.state_handler.WorkcellStateHandler, update_info: bool = False) ‑> None`
    :   Update all active nodes in the workcell.

        Args:
            state_manager: The workcell state handler
            update_info: Whether to update node info in addition to status and state (default: False)

    `update_node(self, node_name: str, node: madsci.common.types.node_types.Node, state_manager: madsci.workcell_manager.state_handler.WorkcellStateHandler, update_info: bool = False) ‑> None`
    :   Update a single node's status, state, and optionally info.

        Args:
            node_name: The name of the node to update
            node: The node object to update
            state_manager: The workcell state handler
            update_info: Whether to update node info (default: False). Node info changes
                        infrequently, so it's updated less often to reduce network overhead.

    `update_param_value_from_datapoint(self, wf: madsci.common.types.workflow_types.Workflow, datapoint: madsci.common.types.datapoint_types.DataPoint, parameter: madsci.common.types.parameter_types.ParameterFeedForwardJson | madsci.common.types.parameter_types.ParameterFeedForwardFile) ‑> madsci.common.types.workflow_types.Workflow`
    :   Updates the parameters in a workflow

    `update_step(self, wf: madsci.common.types.workflow_types.Workflow, step: madsci.common.types.step_types.Step) ‑> None`
    :   Update the step in the workflow
