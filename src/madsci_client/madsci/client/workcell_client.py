"""Client for performing workcell actions"""

import json
import time
from pathlib import Path
from typing import Any, Optional, Union

from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.exceptions import WorkflowFailedError
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.base_types import PathLike
from madsci.common.types.client_types import WorkcellClientConfig
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import WorkcellState
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
)
from madsci.common.utils import create_http_session
from madsci.common.workflows import (
    check_parameters_lists,
)
from pydantic import AnyUrl
from rich import print
from ulid import ULID


class WorkcellClient:
    """A client for interacting with the Workcell Manager to perform various actions."""

    workcell_server_url: Optional[AnyUrl]

    def __init__(
        self,
        workcell_server_url: Optional[Union[str, AnyUrl]] = None,
        working_directory: str = "./",
        event_client: Optional[EventClient] = None,
        config: Optional[WorkcellClientConfig] = None,
    ) -> None:
        """
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
        """
        self.workcell_server_url = (
            AnyUrl(workcell_server_url)
            if workcell_server_url
            else get_current_madsci_context().workcell_server_url
        )
        self.logger = event_client or EventClient()
        if not self.workcell_server_url:
            raise ValueError(
                "Workcell server URL was not provided and cannot be found in the context."
            )
        self.working_directory = Path(working_directory).expanduser()

        # Setup HTTP session with standardized configuration
        self.config = config if config is not None else WorkcellClientConfig()
        self.session = create_http_session(config=self.config)

    def query_workflow(
        self, workflow_id: str, timeout: Optional[float] = None
    ) -> Optional[Workflow]:
        """
        Check the status of a workflow using its ID.

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
        """
        url = f"{self.workcell_server_url}workflow/{workflow_id}"
        response = self.session.get(url, timeout=timeout or self.config.timeout_default)

        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return Workflow(**response.json())

    def get_workflow_definition(
        self, workflow_definition_id: str, timeout: Optional[float] = None
    ) -> WorkflowDefinition:
        """
        Get the definition of a workflow.

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
        """
        url = f"{self.workcell_server_url}workflow_definition/{workflow_definition_id}"
        response = self.session.get(url, timeout=timeout or self.config.timeout_default)
        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return WorkflowDefinition.model_validate(response.json())

    def submit_workflow_definition(
        self,
        workflow_definition: Union[PathLike, WorkflowDefinition],
        timeout: Optional[float] = None,
    ) -> str:
        """
        Submit a workflow to the Workcell Manager.

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
        """
        if isinstance(workflow_definition, (Path, str)):
            workflow_definition = WorkflowDefinition.from_yaml(workflow_definition)
        else:
            workflow_definition = WorkflowDefinition.model_validate(workflow_definition)
        workflow_definition.definition_metadata.ownership_info = (
            get_current_ownership_info()
        )
        url = f"{self.workcell_server_url}workflow_definition"
        response = self.session.post(
            url,
            json=workflow_definition.model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )

        if not response.ok and response.content:
            self.logger.error(
                f"Error submitting workflow definition: {response.content.decode()}"
            )
        response.raise_for_status()
        return str(response.json())

    def start_workflow(
        self,
        workflow_definition: Union[str, PathLike, WorkflowDefinition],
        json_inputs: Optional[dict[str, Any]] = None,
        file_inputs: Optional[dict[str, PathLike]] = None,
        await_completion: bool = True,
        prompt_on_error: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
        timeout: Optional[float] = None,
    ) -> Workflow:
        """
        Submit a workflow to the Workcell Manager.

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
        """
        if isinstance(workflow_definition, WorkflowDefinition):
            workflow_definition_id = self.submit_workflow_definition(
                workflow_definition
            )
        else:
            try:
                workflow_definition_id = ULID.from_str(workflow_definition)
            except (ValueError, TypeError):
                workflow_definition = WorkflowDefinition.from_yaml(workflow_definition)
                workflow_definition_id = self.submit_workflow_definition(
                    workflow_definition
                )
        workflow_definition = self.get_workflow_definition(workflow_definition_id)
        files = {}
        if file_inputs:
            files = self.make_paths_absolute(file_inputs)
        url = f"{self.workcell_server_url}workflow"
        data = {
            "workflow_definition_id": workflow_definition_id,
            "json_inputs": json.dumps(json_inputs) if json_inputs else None,
            "ownership_info": get_current_ownership_info().model_dump_json(),
            "file_input_paths": json.dumps(file_inputs) if file_inputs else None,
        }
        files = {
            (
                "files",
                (
                    str(file),
                    Path.open(Path(path).expanduser(), "rb"),
                ),
            )
            for file, path in files.items()
        }
        response = self.session.post(
            url,
            data=data,
            files=files,
            timeout=timeout or self.config.timeout_data_operations,
        )

        if not response.ok and response.content:
            self.logger.error(f"Error submitting workflow: {response.content.decode()}")
        response.raise_for_status()
        if not await_completion:
            return Workflow(**response.json())
        return self.await_workflow(
            response.json()["workflow_id"],
            prompt_on_error=prompt_on_error,
            raise_on_cancelled=raise_on_cancelled,
            raise_on_failed=raise_on_failed,
        )

    submit_workflow = start_workflow

    def make_paths_absolute(self, files: dict[str, PathLike]) -> dict[str, Path]:
        """
        Extract file paths from a workflow definition.

        Parameters
        ----------
        files : dict[str, PathLike]
            A dictionary mapping unique file keys to their paths.

        Returns
        -------
        dict[str, Path]
            A dictionary mapping unique file keys to their paths.
        """

        for file_key, path in files.items():
            if not Path(path).is_absolute():
                files[file_key] = str(self.working_directory / path)
            else:
                files[file_key] = str(path)
        return files

    def submit_workflow_sequence(
        self,
        workflows: list[str],
        json_inputs: list[dict[str, Any]] = [],
        file_inputs: list[dict[str, PathLike]] = [],
    ) -> list[Workflow]:
        """
        Submit a sequence of workflows to run in order.

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
        """
        wfs = []
        json_inputs, file_inputs = check_parameters_lists(
            workflows, json_inputs, file_inputs
        )
        for i in range(len(workflows)):
            wf = self.submit_workflow(
                workflows[i], json_inputs[i], file_inputs[i], await_completion=True
            )
            wfs.append(wf)
        return wfs

    def submit_workflow_batch(
        self,
        workflows: list[str],
        json_inputs: list[dict[str, Any]] = [],
        file_inputs: list[dict[str, PathLike]] = [],
    ) -> list[Workflow]:
        """
        Submit a batch of workflows to run concurrently.

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
        """
        id_list = []
        json_inputs, file_inputs = check_parameters_lists(
            workflows, json_inputs, file_inputs
        )
        for i in range(len(workflows)):
            response = self.submit_workflow(
                workflows[i], json_inputs[i], file_inputs[i], await_completion=False
            )
            id_list.append(response.workflow_id)
        finished = False
        while not finished:
            flag = True
            wfs = []
            for id in id_list:
                wf = self.query_workflow(id)
                flag = flag and (wf.status.terminal)
                wfs.append(wf)
            finished = flag
        return wfs

    def retry_workflow(
        self,
        workflow_id: str,
        index: int = 0,
        await_completion: bool = True,
        raise_on_cancelled: bool = True,
        raise_on_failed: bool = True,
        prompt_on_error: bool = True,
        timeout: Optional[float] = None,
    ) -> Workflow:
        """
        Retry a workflow from a specific step.

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
        """
        url = f"{self.workcell_server_url}workflow/{workflow_id}/retry"
        response = self.session.post(
            url,
            params={
                "workflow_id": workflow_id,
                "index": index,
            },
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        if await_completion:
            return self.await_workflow(
                workflow_id=workflow_id,
                raise_on_cancelled=raise_on_cancelled,
                raise_on_failed=raise_on_failed,
                prompt_on_error=prompt_on_error,
            )

        return Workflow.model_validate(response.json())

    def _handle_workflow_error(
        self,
        wf: Workflow,
        prompt_on_error: bool,
        raise_on_failed: bool,
        raise_on_cancelled: bool,
    ) -> Workflow:
        """
        Handle errors in a workflow by prompting the user for action or raising exceptions.
        Parameters
        ----------
        wf : Workflow
            The workflow object to check for errors.
        prompt_on_error : bool
            If True, prompt the user for action on workflow errors.
        raise_on_failed : bool
            If True, raise an exception if the workflow fails.
        raise_on_cancelled : bool
            If True, raise an exception if the workflow is cancelled.
        Returns
        -------
        Workflow
            The workflow object after handling errors.
        """
        if prompt_on_error:
            while True:
                decision = input(
                    f"""Workflow {"Failed" if wf.status.failed else "Cancelled"}.
Options:
- Retry from a specific step (Enter the step index, e.g., 1; 0 for the first step; -1 for the current step)
- {"R" if raise_on_failed else "Do not r"}aise an exception and continue (c, enter to continue)
"""
                ).strip()
                try:
                    step = int(decision)
                    if step in range(-1, len(wf.steps)):
                        if step == -1:
                            step = wf.status.current_step_index
                        self.logger.info(
                            f"Retrying workflow {wf.workflow_id} from step {step}: '{wf.steps[step]}'."
                        )
                        wf = self.retry_workflow(
                            wf.workflow_id,
                            step,
                            raise_on_cancelled=raise_on_cancelled,
                            await_completion=True,
                            raise_on_failed=raise_on_failed,
                        )
                        break
                except ValueError:
                    pass
                if decision in {"c", "", None}:
                    break
                print("Invalid input. Please try again.")
        if wf.status.failed and raise_on_failed:
            raise WorkflowFailedError(
                f"Workflow {wf.name} ({wf.workflow_id}) failed on step {wf.status.current_step_index}: '{wf.steps[wf.status.current_step_index].name}' with result:\n {wf.steps[wf.status.current_step_index].result}."
            )
        if wf.status.cancelled and raise_on_cancelled:
            raise WorkflowFailedError(
                f"Workflow {wf.name} ({wf.workflow_id}) was cancelled on step {wf.status.current_step_index}: '{wf.steps[wf.status.current_step_index].name}'."
            )
        return wf

    def await_workflow(
        self,
        workflow_id: str,
        prompt_on_error: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
        query_frequency: float = 2.0,
    ) -> Workflow:
        """
        Wait for a workflow to complete.

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
        """
        prior_status = None
        prior_index = None
        while True:
            wf = self.query_workflow(workflow_id)
            status = wf.status
            step_index = wf.status.current_step_index
            if prior_status != status or prior_index != step_index:
                if step_index < len(wf.steps):
                    step_name = wf.steps[step_index].name
                else:
                    step_name = "Workflow End"
                # TODO: Improve progress reporting
                print(
                    f"\n{wf.name}['{step_name}']: {wf.status.description}",
                    end="",
                    flush=True,
                )
            else:
                print(".", end="", flush=True)
            time.sleep(query_frequency)
            if wf.status.terminal:
                print()
                break
            prior_status = status
            prior_index = step_index
        if wf.status.failed or wf.status.cancelled:
            return self._handle_workflow_error(
                wf, prompt_on_error, raise_on_failed, raise_on_cancelled
            )
        return wf

    def get_nodes(self, timeout: Optional[float] = None) -> dict[str, Node]:
        """
        Get all nodes in the workcell.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        dict[str, Node]
            A dictionary of node names and their details.
        """
        response = self.session.get(
            f"{self.workcell_server_url}nodes",
            timeout=timeout or self.config.timeout_default,
        )
        return response.json()

    def get_node(self, node_name: str, timeout: Optional[float] = None) -> Node:
        """
        Get details of a specific node.

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
        """
        response = self.session.get(
            f"{self.workcell_server_url}node/{node_name}",
            timeout=timeout or self.config.timeout_default,
        )
        return response.json()

    def add_node(
        self,
        node_name: str,
        node_url: str,
        node_description: str = "A Node",
        permanent: bool = False,
        timeout: Optional[float] = None,
    ) -> Node:
        """
        Add a node to the workcell.

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
        """
        response = self.session.post(
            f"{self.workcell_server_url}node",
            params={
                "node_name": node_name,
                "node_url": node_url,
                "node_description": node_description,
                "permanent": permanent,
            },
            timeout=timeout or self.config.timeout_default,
        )
        return response.json()

    def get_active_workflows(
        self, timeout: Optional[float] = None
    ) -> dict[str, Workflow]:
        """
        Get all workflows from the Workcell Manager.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.
        """
        response = self.session.get(
            f"{self.workcell_server_url}workflows/active",
            timeout=timeout or self.config.timeout_long_operations,
        )
        response.raise_for_status()
        workflow_dict = response.json()
        if not isinstance(workflow_dict, dict):
            raise ValueError(
                f"Expected a dictionary of workflows, but got {type(workflow_dict)}."
            )
        return {
            key: Workflow.model_validate(value) for key, value in workflow_dict.items()
        }

    def get_archived_workflows(
        self, number: int = 20, timeout: Optional[float] = None
    ) -> dict[str, Workflow]:
        """
        Get all workflows from the Workcell Manager.

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
        """
        response = self.session.get(
            f"{self.workcell_server_url}workflows/archived",
            params={"number": number},
            timeout=timeout or self.config.timeout_long_operations,
        )
        response.raise_for_status()
        workflow_dict = response.json()
        if not isinstance(workflow_dict, dict):
            raise ValueError(
                f"Expected a dictionary of workflows, but got {type(workflow_dict)}."
            )
        return {
            key: Workflow.model_validate(value) for key, value in workflow_dict.items()
        }

    def get_workflow_queue(self, timeout: Optional[float] = None) -> list[Workflow]:
        """
        Get the workflow queue from the workcell.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        list[Workflow]
            A list of queued workflows.
        """
        response = self.session.get(
            f"{self.workcell_server_url}workflows/queue",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [Workflow.model_validate(wf) for wf in response.json()]

    def get_workcell_state(self, timeout: Optional[float] = None) -> WorkcellState:
        """
        Get the full state of the workcell.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.

        Returns
        -------
        WorkcellState
            The current state of the workcell.
        """
        response = self.session.get(
            f"{self.workcell_server_url}state",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return WorkcellState.model_validate(response.json())

    def pause_workflow(
        self, workflow_id: str, timeout: Optional[float] = None
    ) -> Workflow:
        """
        Pause a workflow.

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
        """
        response = self.session.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/pause",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def resume_workflow(
        self, workflow_id: str, timeout: Optional[float] = None
    ) -> Workflow:
        """
        Resume a paused workflow.

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
        """
        response = self.session.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/resume",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def cancel_workflow(
        self, workflow_id: str, timeout: Optional[float] = None
    ) -> Workflow:
        """
        Cancel a workflow.

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
        """
        response = self.session.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/cancel",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())
