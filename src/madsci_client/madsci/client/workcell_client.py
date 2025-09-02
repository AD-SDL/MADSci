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
        retry: bool = False,
    ) -> None:
        """
        Initialize the WorkcellClient.

        Parameters
        ----------
        workcell_server_url : Optional[Union[str, AnyUrl]]
            The base URL of the Workcell Manager. If not provided, it will be taken from the current MadsciContext.
        working_directory : str, optional
            The directory to look for relative paths. Defaults to "./".
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

    def query_workflow(
        self, workflow_id: str, retry: Optional[bool] = None
    ) -> Optional[Workflow]:
        """
        Check the status of a workflow using its ID.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to query.

        Returns
        -------
        Optional[Workflow]
            The workflow object if found, otherwise None.
        """
        if retry is None:
            retry = self.retry
        url = f"{self.workcell_server_url}workflow/{workflow_id}"
        if not retry:
            response = requests.get(url, timeout=10)
        else:
            response = None
            timeout = 10
            while response is None:
                try:
                    response = requests.get(url, timeout=timeout)
                except requests.exceptions.Timeout:
                    self.logger.error("Request Timed Out, Retrying")
                    timeout *= 2

        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return Workflow(**response.json())

    def get_workflow_definition(
        self, workflow_definition_id: str, retry: Optional[bool] = None
    ) -> WorkflowDefinition:
        """
        get the workflow definition
        """
        url = f"{self.workcell_server_url}workflow_definition/{workflow_definition_id}"
        if retry is None:
            retry = self.retry
        if not retry:
            response = requests.get(url, timeout=10)
        else:
            response = None
            timeout = 10
            while response is None:
                try:
                    response = requests.get(url, timeout=timeout)
                except requests.exceptions.Timeout:
                    self.logger.error("Request Timed Out, Retrying")
                    timeout *= 2
        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return WorkflowDefinition(**response.json())

    def submit_workflow_definition(
        self,
        workflow_definition: Union[PathLike, WorkflowDefinition],
        retry: Optional[bool] = None,
    ) -> Workflow:
        """
        Submit a workflow to the Workcell Manager.

        Parameters
        ----------
        workflow: Union[PathLike, WorkflowDefinition],
            Either a WorkflowDefinition or a path to a YAML file of one.
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
        if isinstance(workflow_definition, (Path, str)):
            workflow_definition = WorkflowDefinition.from_yaml(workflow_definition)
        else:
            workflow_definition = WorkflowDefinition.model_validate(workflow_definition)
        workflow_definition.definition_metadata.ownership_info = (
            get_current_ownership_info()
        )
        url = f"{self.workcell_server_url}workflow_definition"

        if not retry:
            response = requests.post(
                url,
                json=workflow_definition.model_dump(mode="json"),
                timeout=10,
            )
        else:
            response = None
            timeout = 10
            while response is None:
                try:
                    response = requests.post(
                        url,
                        json=workflow_definition.model_dump(mode="json"),
                        timeout=timeout,
                    )
                except requests.exceptions.Timeout:
                    self.logger.error("Request Timed Out, Retrying")
                    timeout *= 2

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
        if input_files:
            files = self.make_paths_absolute(input_files)
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
        if not retry:
            response = requests.post(url, data=data, files=files, timeout=10)
        else:
            response = None
            timeout = 10
            while response is None:
                try:
                    response = requests.post(
                        url, data=data, files=files, timeout=timeout
                    )
                except requests.exceptions.Timeout:
                    self.logger.error("Request Timed Out, Retrying")
                    timeout *= 2

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
        workflow : WorkflowDefinition
            The workflow definition object.

        Returns
        -------
        dict[str, Path]
            A dictionary mapping unique file names to their paths.
        """

        for file, path in files.items():
            if not Path(path).is_absolute():
                files[file] = str(self.working_directory / path)
            else:
                files[file] = str(path)
        return files

    def check_parameters_lists(
        self,
        workflows: list[str],
        input_values: list[dict[str, Any]] = [],
        input_files: list[dict[str, PathLike]] = [],
    ) -> tuple[list[dict[str, Any]], list[dict[str, PathLike]]]:
        """Check if the parameter lists are the right length"""
        if len(input_values) == 0:
            input_values = [{} for _ in workflows]
        if len(input_files) == 0:
            input_files = [{} for _ in workflows]
        if len(workflows) > len(input_values):
            raise ValueError(
                "Must submit input_values, in order, for each workflow, submit empty dictionaries if no input_values"
            )
        if len(workflows) > len(input_files):
            raise ValueError(
                "Must submit input_files, in order, for each workflow, submit empty dictionaries if no input_files"
            )
        return input_values, input_files

    def submit_workflow_sequence(
        self,
        workflows: list[str],
        input_values: list[dict[str, Any]] = [],
        input_files: dict[str, PathLike] = [],
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
        input_values, input_files = self.check_parameters_lists(
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
        input_values, input_files = self.check_parameters_lists(
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
        url = f"{self.workcell_server_url}workflow/{workflow_id}/retry"
        response = requests.post(
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

    def get_nodes(self) -> dict[str, Node]:
        """
        Get all nodes in the workcell.

        Returns
        -------
        dict[str, Node]
            A dictionary of node names and their details.
        """
        response = requests.get(f"{self.workcell_server_url}nodes", timeout=10)
        return response.json()

    def get_node(self, node_name: str) -> Node:
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
        response = requests.get(
            f"{self.workcell_server_url}node/{node_name}", timeout=10
        )
        return response.json()

    def add_node(
        self,
        node_name: str,
        node_url: str,
        node_description: str = "A Node",
        permanent: bool = False,
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
        response = requests.post(
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

    def get_active_workflows(self) -> dict[str, Workflow]:
        """
        Get all workflows from the Workcell Manager.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.
        """
        response = requests.get(
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

    def get_archived_workflows(self, number: int = 20) -> dict[str, Workflow]:
        """
        Get all workflows from the Workcell Manager.

        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.
        """
        response = requests.get(
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

    def get_workflow_queue(self) -> list[Workflow]:
        """
        Get the workflow queue from the workcell.

        Returns
        -------
        list[Workflow]
            A list of queued workflows.
        """
        response = requests.get(
            f"{self.workcell_server_url}workflows/queue", timeout=10
        )
        response.raise_for_status()
        return [Workflow.model_validate(wf) for wf in response.json()]

    def get_workcell_state(self) -> WorkcellState:
        """
        Get the full state of the workcell.

        Returns
        -------
        WorkcellState
            The current state of the workcell.
        """
        response = requests.get(f"{self.workcell_server_url}state", timeout=10)
        response.raise_for_status()
        return WorkcellState.model_validate(response.json())

    def pause_workflow(self, workflow_id: str) -> Workflow:
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
        response = requests.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/pause", timeout=10
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def resume_workflow(self, workflow_id: str) -> Workflow:
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
        response = requests.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/resume", timeout=10
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def cancel_workflow(self, workflow_id: str) -> Workflow:
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
        response = requests.post(
            f"{self.workcell_server_url}workflow/{workflow_id}/cancel", timeout=10
        )
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def get_locations(self) -> list[Location]:
        """
        Get all locations in the workcell.

        Returns
        -------
        list[Location]
            A list of locations.
        """
        response = requests.get(f"{self.workcell_server_url}locations", timeout=10)
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json().values()]

    def get_location(self, location_id: str) -> Location:
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
        response = requests.get(
            f"{self.workcell_server_url}location/{location_id}", timeout=10
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def add_location(self, location: Location, permanent: bool = True) -> Location:
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
        response = requests.post(
            f"{self.workcell_server_url}location",
            json=location.model_dump(mode="json"),
            timeout=10,
            params={"permanent": permanent},
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def attach_resource_to_location(
        self, location_id: str, resource_id: str
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
        response = requests.post(
            f"{self.workcell_server_url}location/{location_id}/attach_resource",
            params={
                "resource_id": resource_id,
            },
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def delete_location(self, location_id: str) -> None:
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
        response = requests.delete(
            f"{self.workcell_server_url}location/{location_id}", timeout=10
        )
        response.raise_for_status()
