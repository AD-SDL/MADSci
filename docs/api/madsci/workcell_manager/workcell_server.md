Module madsci.workcell_manager.workcell_server
==============================================
MADSci Workcell Manager using AbstractManagerBase.

Classes
-------

`WorkcellManager(settings: madsci.common.types.workcell_types.WorkcellManagerSettings | None = None, definition: madsci.common.types.workcell_types.WorkcellManagerDefinition | None = None, redis_connection: Any | None = None, mongo_connection: pymongo.synchronous.database.Database | None = None, start_engine: bool = True, **kwargs: Any)`
:   MADSci Workcell Manager using the new AbstractManagerBase pattern.

    This manager uses MadsciClientMixin (via AbstractManagerBase) for client management.
    Required clients: data, location

    Initialize the WorkcellManager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition of a MADSci Workcell.

    `REQUIRED_CLIENTS: ClassVar[list[str]]`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the MADSci Workcell Manager.

    ### Methods

    `add_node(self, node_name: str, node_url: str, permanent: bool = False) ‑> madsci.common.types.node_types.Node | str`
    :   Add a node to the workcell's node list

    `cancel_workflow(self, workflow_id: str) ‑> madsci.common.types.workflow_types.Workflow`
    :   Cancel a specific workflow.

    `create_server(self, **kwargs: Any) ‑> fastapi.applications.FastAPI`
    :   Create the FastAPI server application with lifespan.

    `get_active_workflows(self) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get active workflows.

    `get_archived_workflows(self, number: int = 20) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get archived workflows.

    `get_health(self) ‑> madsci.common.types.workcell_types.WorkcellManagerHealth`
    :   Get the health status of the Workcell Manager.

    `get_node(self, node_name: str) ‑> madsci.common.types.node_types.Node | str`
    :   Get information about about a specific node.

    `get_nodes(self) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Get info on the nodes in the workcell.

    `get_state(self) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Get the current state of the workcell.

    `get_workcell(self) ‑> madsci.common.types.workcell_types.WorkcellManagerDefinition`
    :   Get the currently running workcell (backward compatibility).

    `get_workflow(self, workflow_id: str) ‑> madsci.common.types.workflow_types.Workflow`
    :   Get info on a specific workflow.

    `get_workflow_definition(self, workflow_definition_id: str) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Parses the payload and workflow files, and then pushes a workflow job onto the redis queue

        Parameters
        ----------
        Workflow Definition ID: str
        - the workflow definition ID

        Returns
        -------
        response: WorkflowDefinition
        - a workflow run object for the requested run_id

    `get_workflow_queue(self) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Get all queued workflows.

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

        This method sets up the workcell-specific state handler and clients.
        Client initialization is handled by MadsciClientMixin via setup_clients().

    `pause_workflow(self, workflow_id: str) ‑> madsci.common.types.workflow_types.Workflow`
    :   Pause a specific workflow.

    `resume_workflow(self, workflow_id: str) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resume a paused workflow.

    `retry_workflow(self, workflow_id: str, index: int = -1) ‑> madsci.common.types.workflow_types.Workflow`
    :   Retry an existing workflow from a specific step.

    `send_admin_command(self, command: str) ‑> list`
    :   Send an admin command to all capable nodes.

    `send_admin_command_to_node(self, command: str, node: str) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Send admin command to a node.

    `start_workflow(self, workflow_definition_id: Annotated[str, Form(PydanticUndefined)], ownership_info: Annotated[str | None, Form(PydanticUndefined)] = None, json_inputs: Annotated[str | None, Form(PydanticUndefined)] = None, file_input_paths: Annotated[str | None, Form(PydanticUndefined)] = None, files: list[fastapi.datastructures.UploadFile] = []) ‑> madsci.common.types.workflow_types.Workflow`
    :   Parses the payload and workflow files, and then pushes a workflow job onto the redis queue

        Parameters
        ----------
        workflow: YAML string
        - The workflow yaml file
        parameters: Optional[Dict[str, Any]] = {}
        - Dynamic values to insert into the workflow file
        ownership_info: Optional[OwnershipInfo]
        - Information about the experiments, users, etc. that own this workflow
        simulate: bool
        - whether to use real robots or not
        validate_only: bool
        - whether to validate the workflow without queueing it

        Returns
        -------
        response: Workflow
        - a workflow run object for the requested run_id

    `submit_workflow_definition(self, workflow_definition: madsci.common.types.workflow_types.WorkflowDefinition) ‑> str`
    :   Parses the payload and workflow files, and then pushes a workflow job onto the redis queue

        Parameters
        ----------
        workflow_definition: YAML string
        - The workflow_definition yaml file


        Returns
        -------
        response: Workflow Definition ID
        - the workflow definition ID
