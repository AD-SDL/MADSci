"""Client for performing workcell actions"""

import json
import time
from pathlib import Path
from typing import Any, Optional, Union

import requests
from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.exceptions import WorkflowFailedError
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.base_types import PathLike
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import WorkcellState
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
)
from madsci.common.workflows import (
    analyze_parameter_types,
    check_parameters,
    check_parameters_lists,
)
from pydantic import AnyUrl
from requests.adapters import HTTPAdapter
from rich import print
from ulid import ULID
from urllib3.util.retry import Retry


class WorkcellClient:
    """A client for interacting with the Workcell Manager to perform various actions."""

    workcell_server_url: Optional[AnyUrl]

    def __init__(
        self,
        workcell_server_url: Optional[Union[str, AnyUrl]] = None,
        working_directory: str = "./",
        event_client: Optional[EventClient] = None,
        retry: bool = False,
        retry_total: int = 3,
        retry_backoff_factor: float = 0.3,
        retry_status_forcelist: Optional[list[int]] = None,
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
        retry : bool, optional
            Whether to enable retry by default for all requests. Defaults to False.
        retry_total : int, optional
            Total number of retries to allow. Defaults to 3.
        retry_backoff_factor : float, optional
            Backoff factor for retries. Defaults to 0.3.
        retry_status_forcelist : Optional[list[int]], optional
            HTTP status codes to force a retry on. Defaults to [429, 500, 502, 503, 504].
        """
        self.workcell_server_url = (
            AnyUrl(workcell_server_url)
            if workcell_server_url
            else get_current_madsci_context().workcell_server_url
        )
        self.retry = retry
        self.logger = event_client or EventClient()
        if not self.workcell_server_url:
            raise ValueError(
                "Workcell server URL is not provided and cannot be found in the context."
            )
        self.working_directory = Path(working_directory).expanduser()

        # Setup retry strategy
        if retry_status_forcelist is None:
            retry_status_forcelist = [429, 500, 502, 503, 504]

        retry_strategy = Retry(
            total=retry_total,
            backoff_factor=retry_backoff_factor,
            status_forcelist=retry_status_forcelist,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        )

        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Create a session without retries for when retry=False
        self.session_no_retry = requests.Session()

    def query_workflow(
        self, workflow_id: str, retry: Optional[bool] = None
    ) -> Optional[Workflow]:
        """
        Check the status of a workflow using its ID.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to query.
        retry : Optional[bool]
            Whether to enable retry for this request. Defaults to the client's retry setting.

        Returns
        -------
        Optional[Workflow]
            The workflow object if found, otherwise None.
        """
        if retry is None:
            retry = self.retry
        url = f"{self.workcell_server_url}workflow/{workflow_id}"
        session = self.session if retry else self.session_no_retry
        response = session.get(url, timeout=10)

        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return Workflow(**response.json())

    def get_workflow_definition(
        self, workflow_definition_id: str, retry: Optional[bool] = None
    ) -> WorkflowDefinition:
        """
        Get the definition of a workflow.

        Parameters
        ----------
        workflow_definition_id : str
            The ID of the workflow definition to retrieve.
        retry : Optional[bool]
            Whether to enable retry for this request. Defaults to the client's retry setting.

        Returns
        -------
        WorkflowDefinition
            The workflow definition object.
        """
        url = f"{self.workcell_server_url}workflow_definition/{workflow_definition_id}"
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(url, timeout=10)
        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return WorkflowDefinition.model_validate(response.json())

    def submit_workflow_definition(
        self,
        workflow_definition: Union[PathLike, WorkflowDefinition],
        retry: Optional[bool] = None,
    ) -> str:
        """
        Submit a workflow to the Workcell Manager.

        Parameters
        ----------
        workflow_definition : Union[PathLike, WorkflowDefinition]
            The workflow definition to submit.
        retry : Optional[bool]
            Whether to enable retry for this request. Defaults to the client's retry setting.

        Returns
        -------
        str
            The ID of the submitted workflow.
        """
        if retry is None:
            retry = self.retry
        if isinstance(workflow_definition, (Path, str)):
            workflow_definition = WorkflowDefinition.from_yaml(workflow_definition)
        else:
            workflow_definition = WorkflowDefinition.model_validate(workflow_definition)
        workflow_definition.definition_metadata.ownership_info = (
            get_current_ownership_info()
        )
        url = f"{self.workcell_server_url}workflow_definition"
        session = self.session if retry else self.session_no_retry
        response = session.post(
            url,
            json=workflow_definition.model_dump(mode="json"),
            timeout=10,
        )

        if not response.ok and response.content:
            self.logger.error(
                f"Error submitting workflow definition: {response.content.decode()}"
            )
        response.raise_for_status()
        return str(response.json())

    def start_workflow(
        self,
        workflow_definition: Union[PathLike, WorkflowDefinition],
        input_values: Optional[dict[str, Any]] = None,
        input_files: Optional[dict[str, PathLike]] = None,
        await_completion: bool = True,
        prompt_on_error: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
        retry: Optional[bool] = None,
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

        Returns
        -------
        Workflow
            The submitted workflow object.
        """
        if retry is None:
            retry = self.retry
        if isinstance(workflow_definition, WorkflowDefinition):
            workflow_definition_id = self.submit_workflow_definition(
                workflow_definition
            )
        else:
            try:
                workflow_definition_id = ULID.from_str(workflow_definition)
            except ValueError:
                workflow_definition = WorkflowDefinition.from_yaml(workflow_definition)
                workflow_definition_id = self.submit_workflow_definition(
                    workflow_definition
                )
        workflow_definition = self.get_workflow_definition(workflow_definition_id)
        files = {}
        analyze_parameter_types(workflow_definition, input_values)
        if input_files:
            files = self.make_paths_absolute(input_files)
        check_parameters(workflow_definition, input_values)

        url = f"{self.workcell_server_url}workflow"
        data = {
            "workflow_definition_id": workflow_definition_id,
            "input_values": json.dumps(input_values) if input_values else None,
            "ownership_info": get_current_ownership_info().model_dump_json(),
            "input_file_paths": json.dumps(input_files) if input_files else None,
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
        session = self.session if retry else self.session_no_retry
        response = session.post(url, data=data, files=files, timeout=10)

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
        input_values: list[dict[str, Any]] = [],
        input_files: list[dict[str, PathLike]] = [],
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
        input_values, input_files = check_parameters_lists(
            workflows, input_values, input_files
        )
        for i in range(len(workflows)):
            wf = self.submit_workflow(
                workflows[i], input_values[i], input_files[i], await_completion=True
            )
            wfs.append(wf)
        return wfs

    def submit_workflow_batch(
        self,
        workflows: list[str],
        input_values: list[dict[str, Any]] = [],
        input_files: list[dict[str, PathLike]] = [],
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
        input_values, input_files = check_parameters_lists(
            workflows, input_values, input_files
        )
        for i in range(len(workflows)):
            response = self.submit_workflow(
                workflows[i], input_values[i], input_files[i], await_completion=False
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
        retry: Optional[bool] = None,
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

        Returns
        -------
        dict
            The response from the Workcell Manager.
        """
        if retry is None:
            retry = self.retry
        url = f"{self.workcell_server_url}workflow/{workflow_id}/retry"
        session = self.session if retry else self.session_no_retry
        response = session.post(
            url,
            params={
                "workflow_id": workflow_id,
                "index": index,
            },
            timeout=10,
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
            time.sleep(1)
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

    def get_nodes(self, retry: Optional[bool] = None) -> dict[str, Node]:
        """
        Get all nodes in the workcell.

        Returns
        -------
        dict[str, Node]
            A dictionary of node names and their details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(f"{self.workcell_server_url}nodes", timeout=10)
        return response.json()

    def get_node(self, node_name: str, retry: Optional[bool] = None) -> Node:
        """
        Get details of a specific node.

        Parameters
        ----------
        node_name : str
            The name of the node.

        Returns
        -------
        Node
            The node details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(
            f"{self.workcell_server_url}node/{node_name}", timeout=10
        )
        return response.json()

    def add_node(
        self,
        node_name: str,
        node_url: str,
        node_description: str = "A Node",
        permanent: bool = False,
        retry: Optional[bool] = None,
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

        Returns
        -------
        Node
            The added node details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.post(
            f"{self.workcell_server_url}node",
            params={
                "node_name": node_name,
                "node_url": node_url,
                "node_description": node_description,
                "permanent": permanent,
            },
            timeout=10,
        )
        return response.json()

    def get_active_workflows(self, retry: Optional[bool] = None) -> dict[str, Workflow]:
        """
        Get all workflows from the Workcell Manager.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(
            f"{self.workcell_server_url}workflows/active", timeout=100
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
        self, number: int = 20, retry: Optional[bool] = None
    ) -> dict[str, Workflow]:
        """
        Get all workflows from the Workcell Manager.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(
            f"{self.workcell_server_url}workflows/archived",
            params={"number": number},
            timeout=100,
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

    def get_workflow_queue(self, retry: Optional[bool] = None) -> list[Workflow]:
        """
        Get the workflow queue from the workcell.

        Returns
        -------
        list[Workflow]
            A list of queued workflows.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(f"{self.workcell_server_url}workflows/queue", timeout=10)
        response.raise_for_status()
        return [Workflow.model_validate(wf) for wf in response.json()]

    def get_workcell_state(self, retry: Optional[bool] = None) -> WorkcellState:
        """
        Get the full state of the workcell.

        Returns
        -------
        WorkcellState
            The current state of the workcell.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(f"{self.workcell_server_url}state", timeout=10)
        response.raise_for_status()
        return WorkcellState.model_validate(response.json())

    def pause_workflow(
        self, workflow_id: str, retry: Optional[bool] = None
    ) -> Workflow:
        """
        Pause a workflow.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to pause.

        Returns
        -------
        Workflow
            The paused workflow object.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/pause", timeout=10
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def resume_workflow(
        self, workflow_id: str, retry: Optional[bool] = None
    ) -> Workflow:
        """
        Resume a paused workflow.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resume.

        Returns
        -------
        Workflow
            The resumed workflow object.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/resume", timeout=10
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def cancel_workflow(
        self, workflow_id: str, retry: Optional[bool] = None
    ) -> Workflow:
        """
        Cancel a workflow.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to cancel.

        Returns
        -------
        Workflow
            The cancelled workflow object.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/cancel", timeout=10
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def get_locations(self, retry: Optional[bool] = None) -> list[Location]:
        """
        Get all locations in the workcell.

        Returns
        -------
        list[Location]
            A list of locations.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(f"{self.workcell_server_url}locations", timeout=10)
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json().values()]

    def get_location(self, location_id: str, retry: Optional[bool] = None) -> Location:
        """
        Get details of a specific location.

        Parameters
        ----------
        location_id : str
            The ID of the location.

        Returns
        -------
        Location
            The location details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.get(
            f"{self.workcell_server_url}location/{location_id}", timeout=10
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def add_location(
        self, location: Location, permanent: bool = True, retry: Optional[bool] = None
    ) -> Location:
        """
        Add a location to the workcell.

        Parameters
        ----------
        location : Location
            The location object to add.

        Returns
        -------
        Location
            The added location details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.post(
            f"{self.workcell_server_url}location",
            json=location.model_dump(mode="json"),
            timeout=10,
            params={"permanent": permanent},
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def attach_resource_to_location(
        self, location_id: str, resource_id: str, retry: Optional[bool] = None
    ) -> Location:
        """
        Attach a resource container to a location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        resource_id : str
            The ID of the resource to attach.

        Returns
        -------
        Location
            The updated location details.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.post(
            f"{self.workcell_server_url}location/{location_id}/attach_resource",
            params={
                "resource_id": resource_id,
            },
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def delete_location(self, location_id: str, retry: Optional[bool] = None) -> None:
        """
        Delete a location from the workcell.

        Parameters
        ----------
        location_id : str
            The ID of the location to delete.

        Returns
        -------
        dict
            A dictionary indicating the deletion status.
        """
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry
        response = session.delete(
            f"{self.workcell_server_url}location/{location_id}", timeout=10
        )
        response.raise_for_status()
