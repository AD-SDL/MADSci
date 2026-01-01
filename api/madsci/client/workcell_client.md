Module madsci.client.workcell_client
====================================
Client for performing workcell actions

Classes
-------

`WorkcellClient(workcell_server_url: str | pydantic.networks.AnyUrl | None = None, working_directory: str = './', event_client: madsci.client.event_client.EventClient | None = None, config: madsci.common.types.client_types.WorkcellClientConfig | None = None)`
:   A client for interacting with the Workcell Manager to perform various actions.

    Initialize the WorkcellClient.

    Parameters
    ----------
    workcell_server_url : Optional[Union[str, AnyUrl]]
        The base URL of the Workcell Manager. If not provided, it will be taken from the current MadsciContext.
    working_directory : str, optional
        The directory to look for relative paths. Defaults to "./".
    event_client : Optional[EventClient], optional
        Event client for logging. If not provided, a new one will be created.
    config : Optional[WorkcellClientConfig], optional
        Client configuration for retry strategies, timeouts, and connection pooling.
        If not provided, uses default WorkcellClientConfig settings.

    ### Class variables

    `workcell_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Methods

    `add_node(self, node_name: str, node_url: str, node_description: str = 'A Node', permanent: bool = False, timeout: float | None = None) ‑> madsci.common.types.node_types.Node`
    :   Add a node to the workcell.

        Parameters
        ----------
        node_name : str
            The name of the node.
        node_url : str
            The URL of the node.
        node_description : str, optional
            A description of the node, by default "A Node".
        permanent : bool, optional
            If True, add the node permanently, by default False.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Node
            The added node details.

    `await_workflow(self, workflow_id: str, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, query_frequency: float = 2.0) ‑> madsci.common.types.workflow_types.Workflow`
    :   Wait for a workflow to complete.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to wait for.
        prompt_on_error : bool, optional
            If True, prompt the user for action on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        query_frequency : float, optional
            How often to query the workflow status in seconds, by default 2.0.

        Returns
        -------
        Workflow
            The completed workflow object.

    `cancel_workflow(self, workflow_id: str, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Cancel a workflow.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to cancel.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Workflow
            The cancelled workflow object.

    `get_active_workflows(self, timeout: float | None = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all workflows from the Workcell Manager.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.

    `get_archived_workflows(self, number: int = 20, timeout: float | None = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all workflows from the Workcell Manager.

        Parameters
        ----------
        number : int
            Number of archived workflows to retrieve.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.

    `get_node(self, node_name: str, timeout: float | None = None) ‑> madsci.common.types.node_types.Node`
    :   Get details of a specific node.

        Parameters
        ----------
        node_name : str
            The name of the node.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Node
            The node details.

    `get_nodes(self, timeout: float | None = None) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Get all nodes in the workcell.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        dict[str, Node]
            A dictionary of node names and their details.

    `get_workcell_state(self, timeout: float | None = None) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Get the full state of the workcell.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        WorkcellState
            The current state of the workcell.

    `get_workflow_definition(self, workflow_definition_id: str, timeout: float | None = None) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Get the definition of a workflow.

        Parameters
        ----------
        workflow_definition_id : str
            The ID of the workflow definition to retrieve.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        WorkflowDefinition
            The workflow definition object.

    `get_workflow_queue(self, timeout: float | None = None) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Get the workflow queue from the workcell.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        list[Workflow]
            A list of queued workflows.

    `make_paths_absolute(self, files: dict[str, str | pathlib.Path]) ‑> dict[str, pathlib.Path]`
    :   Extract file paths from a workflow definition.

        Parameters
        ----------
        files : dict[str, PathLike]
            A dictionary mapping unique file keys to their paths.

        Returns
        -------
        dict[str, Path]
            A dictionary mapping unique file keys to their paths.

    `pause_workflow(self, workflow_id: str, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Pause a workflow.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to pause.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Workflow
            The paused workflow object.

    `query_workflow(self, workflow_id: str, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Check the status of a workflow using its ID.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to query.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Optional[Workflow]
            The workflow object if found, otherwise None.

    `resume_workflow(self, workflow_id: str, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resume a paused workflow.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resume.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Workflow
            The resumed workflow object.

    `retry_workflow(self, workflow_id: str, index: int = 0, await_completion: bool = True, raise_on_cancelled: bool = True, raise_on_failed: bool = True, prompt_on_error: bool = True, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Retry a workflow from a specific step.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to retry.
        index : int, optional
            The step index to retry from, by default -1 (retry the entire workflow).
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        dict
            The response from the Workcell Manager.

    `start_workflow(self, workflow_definition: str | pathlib.Path | madsci.common.types.workflow_types.WorkflowDefinition, json_inputs: dict[str, typing.Any] | None = None, file_inputs: dict[str, str | pathlib.Path] | None = None, await_completion: bool = True, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Submit a workflow to the Workcell Manager.

        Parameters
        ----------
        workflow_definition: Optional[Union[PathLike, WorkflowDefinition]],
            Either a workflow definition ID, WorkflowDefinition or a path to a YAML file of one.
        parameters: Optional[dict[str, Any]] = None,
            Parameters to be inserted into the workflow.
        validate_only : bool, optional
            If True, only validate the workflow without submitting, by default False.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Workflow
            The submitted workflow object.

    `submit_workflow(self, workflow_definition: str | pathlib.Path | madsci.common.types.workflow_types.WorkflowDefinition, json_inputs: dict[str, typing.Any] | None = None, file_inputs: dict[str, str | pathlib.Path] | None = None, await_completion: bool = True, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, timeout: float | None = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Submit a workflow to the Workcell Manager.

        Parameters
        ----------
        workflow_definition: Optional[Union[PathLike, WorkflowDefinition]],
            Either a workflow definition ID, WorkflowDefinition or a path to a YAML file of one.
        parameters: Optional[dict[str, Any]] = None,
            Parameters to be inserted into the workflow.
        validate_only : bool, optional
            If True, only validate the workflow without submitting, by default False.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        Workflow
            The submitted workflow object.

    `submit_workflow_batch(self, workflows: list[str], json_inputs: list[dict[str, typing.Any]] = [], file_inputs: list[dict[str, str | pathlib.Path]] = []) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Submit a batch of workflows to run concurrently.

        Parameters
        ----------
        workflows : list[str]
            A list of workflow definitions in YAML format.
        parameters : list[dict[str, Any]]
            A list of parameter dictionaries for each workflow.

        Returns
        -------
        list[Workflow]
            A list of completed workflow objects.

    `submit_workflow_definition(self, workflow_definition: str | pathlib.Path | madsci.common.types.workflow_types.WorkflowDefinition, timeout: float | None = None) ‑> str`
    :   Submit a workflow to the Workcell Manager.

        Parameters
        ----------
        workflow_definition : Union[PathLike, WorkflowDefinition]
            The workflow definition to submit.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        str
            The ID of the submitted workflow.

    `submit_workflow_sequence(self, workflows: list[str], json_inputs: list[dict[str, typing.Any]] = [], file_inputs: list[dict[str, str | pathlib.Path]] = []) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Submit a sequence of workflows to run in order.

        Parameters
        ----------
        workflows : list[str]
            A list of workflow definitions in YAML format.
        parameters : list[dict[str, Any]]
            A list of parameter dictionaries for each workflow.

        Returns
        -------
        list[Workflow]
            A list of submitted workflow objects.
