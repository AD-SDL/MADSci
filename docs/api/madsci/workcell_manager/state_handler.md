Module madsci.workcell_manager.state_handler
============================================
State management for the WorkcellManager

Classes
-------

`WorkcellStateHandler(workcell_definition: madsci.common.types.workcell_types.WorkcellManagerDefinition | None = None, workcell_settings: madsci.common.types.workcell_types.WorkcellManagerSettings | None = None, redis_connection: Any | None = None, mongo_connection: pymongo.synchronous.database.Database | None = None)`
:   Manages state for a MADSci Workcell, providing transactional access to reading and writing state with
    optimistic check-and-set and locking.

    Initialize a StateManager for a given workcell.

    ### Class variables

    `shutdown: bool`
    :

    `state_change_marker`
    :

    ### Methods

    `archive_terminal_workflows(self) ‑> None`
    :   Move all completed workflows from redis to mongo

    `archive_workflow(self, workflow_id: str) ‑> None`
    :   Move a workflow from redis to mongo

    `clear_workcell_definition(self) ‑> None`
    :   Empty the workcell definition

    `delete_active_workflow(self, workflow_id: str) ‑> None`
    :   Deletes an active workflow by ID

    `delete_archived_workflow(self, workflow_id: str) ‑> None`
    :   delete an archived workflow

    `delete_node(self, node_name: str) ‑> None`
    :   Deletes a node by name

    `delete_workflow_definition(self, workflow_definition_id: str) ‑> None`
    :   Deletes an active workflow by ID

    `enqueue_workflow(self, workflow_id: str) ‑> None`
    :   add a workflow to the workflow queue

    `get_active_workflow(self, workflow_id: str) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Returns a workflow by ID, if it exists in the active workflows.

    `get_active_workflows(self) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Returns all active workflowS

    `get_archived_workflows(self, number: int = 20) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get the latest experiments.

    `get_node(self, node_name: str) ‑> madsci.common.types.node_types.Node`
    :   Returns a node by name

    `get_nodes(self) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Returns all nodes

    `get_workcell_definition(self) ‑> madsci.common.types.workcell_types.WorkcellManagerDefinition`
    :   Returns the current workcell definition as a WorkcellDefinition object

    `get_workcell_state(self) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Return the current state of the workcell.

    `get_workcell_status(self) ‑> madsci.common.types.workcell_types.WorkcellStatus`
    :   Return the current status of the workcell

    `get_workflow(self, workflow_id: str) ‑> madsci.common.types.workflow_types.Workflow`
    :   Get an experiment by ID.

    `get_workflow_definition(self, workflow_definition_id: str) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Returns a workflow definition by ID

    `get_workflow_definitions(self, number: int = 20) ‑> dict[str, madsci.common.types.workflow_types.WorkflowDefinition]`
    :   Get the latest experiments.

    `get_workflow_queue(self) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Returns the workflow queue

    `has_state_changed(self) ‑> bool`
    :   Returns True if the state has changed since the last time this method was called

    `initialize_workcell_state(self) ‑> None`
    :   Initializes the state of the workcell from the workcell definition.

    `mark_state_changed(self) ‑> int`
    :   Marks the state as changed and returns the current state change counter

    `node_lock(self, node_name: str) ‑> pottery.redlock.Redlock`
    :   Gets a lock on a specific node's state. This should be called before any state updates are made to a node,
        or where we don't want the node's state to be changing underneath us (i.e., in the engine).

    `save_workflow_definition(self, workflow_definition: madsci.common.types.workflow_types.WorkflowDefinition) ‑> None`
    :   move a workflow from redis to mongo

    `set_active_workflow(self, wf: madsci.common.types.workflow_types.Workflow, mark_state_changed: bool = True) ‑> None`
    :   Sets a workflow by ID

    `set_node(self, node_name: str, node: madsci.common.types.node_types.Node | madsci.common.types.node_types.NodeDefinition | dict[str, typing.Any]) ‑> None`
    :   Sets a node by name

    `set_workcell_definition(self, workcell: madsci.common.types.workcell_types.WorkcellManagerDefinition) ‑> None`
    :   Sets the active workcell

    `set_workcell_status(self, status: madsci.common.types.workcell_types.WorkcellStatus) ‑> None`
    :   Set the status of the workcell

    `update_active_workflow(self, workflow_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any) ‑> None`
    :   Updates the state of a workflow.

    `update_node(self, node_name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) ‑> None`
    :   Updates the state of a node.

    `update_workcell_definition(self, func: Callable[..., Any], *args: Any, **kwargs: Any) ‑> None`
    :   Updates the workcell definition

    `update_workcell_status(self, func: Callable[..., Any], *args: Any, **kwargs: Any) ‑> None`
    :   Update the status of the workcell

    `update_workflow_queue(self) ‑> None`
    :   Sets the workflow queue based on the current state of the workflows

    `wc_state_lock(self) ‑> pottery.redlock.Redlock`
    :   Gets a lock on the workcell's state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us (i.e., in the engine).
