"""Client for performing workcell actions"""

import json
import time
from pathlib import Path, PurePath
from typing import Any, Optional, Union

import requests
from madsci.client.event_client import EventClient
from madsci.common.data_manipulation import (
    check_for_parameters,
    value_substitution,
    walk_and_replace,
)
from madsci.common.exceptions import WorkflowFailedError
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.base_types import PathLike
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import WorkcellState
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
)
from madsci.common.utils import new_ulid_str
from rich import print


class WorkcellClient:
    """A client for interacting with the Workcell Manager to perform various actions."""

    context: MadsciContext

    def __init__(
        self,
        workcell_server_url: Optional[str] = None,
        working_directory: str = "./",
        event_client: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the WorkcellClient.

        Parameters
        ----------
        workcell_server_url : Optional[str]
            The base URL of the Workcell Manager.
        working_directory : str, optional
            The directory to look for relative paths. Defaults to "./".
        """
        self.context = (
            MadsciContext(workcell_server_url=workcell_server_url)
            if workcell_server_url
            else MadsciContext()
        )
        self.logger = event_client or EventClient()
        self.url = self.context.workcell_server_url
        if not self.url:
            raise ValueError(
                "Workcell server URL is not provided and cannot be found in the context."
            )
        self.working_directory = Path(working_directory).expanduser()
        if str(self.url).endswith("/"):
            self.url = str(self.url)[:-1]

    def query_workflow(self, workflow_id: str) -> Optional[Workflow]:
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
        url = f"{self.url}/workflow/{workflow_id}"
        response = requests.get(url, timeout=10)
        if not response.ok and response.content:
            self.logger.error(f"Error querying workflow: {response.content.decode()}")

        response.raise_for_status()
        return Workflow(**response.json())

    def submit_workflow(
        self,
        workflow: Union[PathLike, WorkflowDefinition],
        parameters: Optional[dict[str, Any]] = None,
        validate_only: bool = False,
        await_completion: bool = True,
        prompt_on_error: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
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
        if isinstance(workflow, (Path, str)):
            workflow = WorkflowDefinition.from_yaml(workflow)
        else:
            workflow = WorkflowDefinition.model_validate(workflow)
        insert_parameter_values(
            workflow=workflow, parameters=parameters if parameters else {}
        )
        files = self._extract_files_from_workflow(workflow)
        url = self.url + "/workflow"
        response = requests.post(
            url,
            data={
                "workflow": workflow.model_dump_json(),
                "parameters": json.dumps(parameters) if parameters else None,
                "validate_only": validate_only,
                "ownership_info": get_current_ownership_info().model_dump_json(),
            },
            files={
                (
                    "files",
                    (
                        str(Path(path).name),
                        Path.open(Path(path).expanduser(), "rb"),
                    ),
                )
                for _, path in files.items()
            },
            timeout=10,
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

    start_workflow = submit_workflow

    def _extract_files_from_workflow(
        self, workflow: WorkflowDefinition
    ) -> dict[str, Path]:
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
        files = {}
        for step in workflow.steps:
            if step.files:
                for file, path in step.files.items():
                    if not check_for_parameters(
                        str(path), [param.name for param in workflow.parameters]
                    ):
                        unique_filename = f"{new_ulid_str()}_{file}"
                        files[unique_filename] = path
                        if not Path(files[unique_filename]).is_absolute():
                            files[unique_filename] = (
                                self.working_directory / files[unique_filename]
                            )
                        step.files[file] = Path(files[unique_filename]).name
        return files

    def submit_workflow_sequence(
        self, workflows: list[str], parameters: list[dict[str, Any]]
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
        for i in range(len(workflows)):
            wf = self.submit_workflow(
                workflows[i], parameters[i], await_completion=True
            )
            wfs.append(wf)
        return wfs

    def submit_workflow_batch(
        self, workflows: list[str], parameters: list[dict[str, Any]]
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
        for i in range(len(workflows)):
            response = self.submit_workflow(
                workflows[i], parameters[i], await_completion=False
            )
            id_list.append(response.json()["workflow_id"])
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
        index: int = -1,
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
        url = f"{self.url}/workflow/{workflow_id}/retry"
        response = requests.post(
            url,
            params={
                "workflow_id": workflow_id,
                "index": index,
            },
            timeout=10,
        )
        if await_completion:
            return self.await_workflow(
                workflow_id=workflow_id,
                raise_on_cancelled=raise_on_cancelled,
                raise_on_failed=raise_on_failed,
                prompt_on_error=prompt_on_error,
            )

        return Workflow(**response.json())

    def resubmit_workflow(
        self,
        workflow_id: str,
        await_completion: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
        prompt_on_error: bool = True,
    ) -> Workflow:
        """
        Resubmit a workflow as a new workflow with a new ID.

        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resubmit.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.

        Returns
        -------
        Workflow
            The resubmitted workflow object.
        """
        url = f"{self.url}/workflow/{workflow_id}/resubmit"
        response = requests.get(url, timeout=10)
        new_wf = Workflow(**response.json())
        if await_completion:
            return self.await_workflow(
                new_wf.workflow_id,
                raise_on_failed=raise_on_failed,
                raise_on_cancelled=raise_on_cancelled,
                prompt_on_error=prompt_on_error,
            )
        return new_wf

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

- Resubmit the workflow, from the beginning (resubmit, r)
- Retry from a specific step (Enter the step index, e.g., 1; 0 for the first step; -1 for the current step)
- {"R" if raise_on_failed else "Do not r"}aise an exception and continue (c, enter to continue)
"""
                ).strip()
                if decision in {"resubmit", "r"}:
                    wf = self.resubmit_workflow(
                        wf.workflow_id,
                        await_completion=True,
                        raise_on_failed=raise_on_failed,
                        raise_on_cancelled=raise_on_cancelled,
                        prompt_on_error=prompt_on_error,
                    )
                    break
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
        url = f"{self.url}/nodes"
        response = requests.get(url, timeout=10)
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
        url = f"{self.url}/node/{node_name}"
        response = requests.get(url, timeout=10)
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
        url = f"{self.url}/node"
        response = requests.post(
            url,
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
        url = f"{self.url}/workflows/active"
        response = requests.get(url, timeout=100)
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
        url = f"{self.url}/workflows/archived"
        response = requests.get(url, params={"number": number}, timeout=100)
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
        url = f"{self.url}/workflows/queue"
        response = requests.get(url, timeout=10)
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
        url = f"{self.url}/state"
        response = requests.get(url, timeout=10)
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
        url = f"{self.url}/workflow/{workflow_id}/pause"
        response = requests.post(url, timeout=10)
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
        url = f"{self.url}/workflow/{workflow_id}/resume"
        response = requests.post(url, timeout=10)
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
        url = f"{self.url}/workflow/{workflow_id}/cancel"
        response = requests.post(url, timeout=10)
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
        url = f"{self.url}/locations"
        response = requests.get(url, timeout=10)
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
        url = f"{self.url}/location/{location_id}"
        response = requests.get(url, timeout=10)
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
        url = f"{self.url}/location"
        response = requests.post(
            url,
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
        url = f"{self.url}/location/{location_id}/attach_resource"
        response = requests.post(
            url,
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
        url = f"{self.url}/location/{location_id}"
        response = requests.delete(url, timeout=10)
        response.raise_for_status()


def insert_parameter_values(
    workflow: WorkflowDefinition, parameters: dict[str, Any]
) -> Workflow:
    """Replace the parameter strings in the workflow with the provided values"""
    for param in workflow.parameters:
        if param.name in parameters and (
            param.label is not None
            or param.step_name is not None
            or param.step_index is not None
        ):
            raise ValueError(
                f"{param} looks like it's configured to use data from a previous step, but you provided a value during workflow submission. Either remove the value or change the parameter configuration."
            )
        if param.name not in parameters:
            if param.default:
                parameters[param.name] = param.default
            elif not (
                (param.step_name is not None or param.step_index is not None)
                and param.label is not None
            ):
                raise ValueError(
                    f"Workflow parameter {param.name} is required, but no value was provided and no default is set."
                )
    parameters = {
        key: (str(value) if isinstance(value, PurePath) else value)
        for key, value in parameters.items()
    }
    steps = []
    for step in workflow.steps:
        for key, val in iter(step):
            if type(val) is str:
                setattr(step, key, value_substitution(val, parameters))

        step.args = walk_and_replace(step.args, parameters)
        step.files = walk_and_replace(step.files, parameters)
        step.locations = walk_and_replace(step.locations, parameters)
        steps.append(step)
    workflow.steps = steps
