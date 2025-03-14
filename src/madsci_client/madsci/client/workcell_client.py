"""Client for performing workcell actions"""

import json
import time
from pathlib import Path
from typing import Any, Optional

import requests
from madsci.common.data_manipulation import value_substitution, walk_and_replace
from madsci.common.exceptions import WorkflowFailedError
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowStatus,
)


class WorkcellClient:
    """a client for running workflows"""

    def __init__(
        self,
        workcell_manager_url: str,
        working_directory: str = "~/.MADsci/temp",
        ownership_info: Optional[OwnershipInfo] = None,
    ) -> "WorkcellClient":
        """initialize the client"""
        self.url = workcell_manager_url
        self.working_directory = Path(working_directory).expanduser()
        self.ownership_info = ownership_info

    def query_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Checks on a workflow run using the id given

        Parameters
        ----------

        workflow_id : str
           The id returned by the start_workflow function for this run

        Returns
        -------

        response: Dict
           The JSON portion of the response from the server"""

        url = f"{self.url}/workflows/{workflow_id}"
        response = requests.get(url, timeout=10)

        if response.ok:
            return Workflow(**response.json())
        response.raise_for_status()
        return None

    def submit_workflow(
        self,
        workflow: str,
        parameters: dict,
        validate_only: bool = False,
        blocking: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
    ) -> Workflow:
        """Send a workflow to the workcell manager"""
        workflow = WorkflowDefinition.from_yaml(workflow)
        WorkflowDefinition.model_validate(workflow)
        insert_parameter_values(workflow=workflow, parameters=parameters)
        files = self._extract_files_from_workflow(workflow)
        url = self.url + "/workflows/start"
        response = requests.post(
            url,
            data={
                "workflow": workflow.model_dump_json(),
                "parameters": json.dumps(parameters),
                "validate_only": validate_only,
                "ownership_info": self.ownership_info.model_dump(mode="json")
                if self.ownership_info
                else None,
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
        if not blocking:
            return Workflow(**response.json())
        return self.await_workflow(
            response.json()["workflow_id"],
            raise_on_cancelled=raise_on_cancelled,
            raise_on_failed=raise_on_failed,
        )

    def _extract_files_from_workflow(
        self, workflow: WorkflowDefinition
    ) -> dict[str, Any]:
        """
        Returns a dictionary of files from a workflow
        """
        files = {}
        for step in workflow.steps:
            if step.files:
                for file, path in step.files.items():
                    unique_filename = f"{step.step_id}_{file}"
                    files[unique_filename] = path
                    if not Path(files[unique_filename]).is_absolute():
                        files[unique_filename] = (
                            self.working_directory / files[unique_filename]
                        )
                    step.files[file] = Path(files[unique_filename]).name
        return files

    def submit_workflow_sequence(
        self, workflows: list[str], parameters: list[dict[str:Any]]
    ) -> list[Workflow]:
        """Submit a list of workflows to run in a specific order"""
        wfs = []
        for i in range(len(workflows)):
            wf = self.submit_workflow(workflows[i], parameters[i], blocking=True)
            wfs.append(wf)
        return wfs

    def submit_workflow_batch(
        self, workflows: list[str], parameters: list[dict[str:Any]]
    ) -> list[Workflow]:
        """Submit a batch of workflows to run in no particular order"""
        id_list = []
        for i in range(len(workflows)):
            response = self.submit_workflow(workflows[i], parameters[i], blocking=False)
            id_list.append(response.json()["workflow_id"])
        finished = False
        while not finished:
            flag = True
            wfs = []
            for id in id_list:
                wf = self.query_workflow(id)
                flag = flag and (wf.status in ["completed", "failed"])
                wfs.append(wf)
            finished = flag
        return wfs

    def retry_workflow(self, workflow_id: str, index: int = -1) -> dict:
        """rerun an exisiting wf using the same wf id"""
        url = f"{self.url}/workflows/retry"
        response = requests.post(
            url,
            params={
                "workflow_id": workflow_id,
                "index": index,
            },
            timeout=10,
        )
        return response.json()

    def resubmit_workflow(
        self,
        workflow_id: str,
        blocking: bool = True,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
    ) -> Workflow:
        """resubmit an existing workflows as a new workflow with a new id"""
        url = f"{self.url}/workflows/resubmit/{workflow_id}"
        response = requests.get(url, timeout=10)
        new_wf = Workflow(**response.json())
        if blocking:
            return self.await_workflow(
                new_wf.workflow_id,
                raise_on_failed=raise_on_failed,
                raise_on_cancelled=raise_on_cancelled,
            )
        return new_wf

    def await_workflow(
        self,
        workflow_id: str,
        raise_on_failed: bool = True,
        raise_on_cancelled: bool = True,
    ) -> Workflow:
        """await a workflows completion"""
        prior_status = None
        prior_index = None
        while True:
            wf = self.query_workflow(workflow_id)
            status = wf.status
            step_index = wf.step_index
            if prior_status != status or prior_index != step_index:
                if step_index < len(wf.steps):
                    step_name = wf.steps[step_index].name
                else:
                    step_name = "Workflow End"
                # TODO: Improve progress reporting
                print(  # noqa: T201
                    f"\n{wf.name} [{step_index}]: {step_name} ({wf.status})",
                    end="",
                    flush=True,
                )
            else:
                print(".", end="", flush=True)  # noqa: T201
            time.sleep(1)
            if wf.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            ]:
                break
            prior_status = status
            prior_index = step_index
        if wf.status == WorkflowStatus.FAILED and raise_on_failed:
            raise WorkflowFailedError(
                f"Workflow {wf.name} ({wf.workflow_id}) failed on step {wf.step_index}: '{wf.steps[wf.step_index].name}'."
            )
        if wf.status == WorkflowStatus.CANCELLED and raise_on_cancelled:
            raise WorkflowFailedError(
                f"Workflow {wf.name} ({wf.workflow_id}) was cancelled on step {wf.step_index}: '{wf.steps[wf.step_index].name}'."
            )
        return wf

    def get_all_nodes(self) -> dict:
        """get all nodes in the workcell"""
        url = f"{self.url}/nodes"
        response = requests.get(url, timeout=10)
        return response.json()

    def get_node(self, node_name: str) -> dict:
        """get a single node from a workcell"""
        url = f"{self.url}/nodes/{node_name}"
        response = requests.get(url, timeout=10)
        return response.json()

    def add_node(
        self,
        node_name: str,
        node_url: str,
        node_description: str = "A Node",
        permanent: bool = False,
    ) -> dict:
        """add a node to a workcell"""
        url = f"{self.url}/nodes/add_node"
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

    def get_all_workflows(self) -> dict:
        """get all workflows from a workcell manager"""
        url = f"{self.url}/workflows"
        response = requests.get(url, timeout=100)
        return response.json()

    def get_workcell_state(self) -> dict:
        """Get the full state of the workcell"""
        url = f"{self.url}/state"
        response = requests.get(url, timeout=10)
        return response.json()


def insert_parameter_values(
    workflow: WorkflowDefinition, parameters: dict[str, Any]
) -> Workflow:
    """Replace the parameter strings in the workflow with the provided values"""
    for param in workflow.parameters:
        if param.name not in parameters:
            if param.default:
                parameters[param.name] = param.default
            else:
                raise ValueError(
                    "Workflow parameter: "
                    + param.name
                    + " not provided, and no default value is defined."
                )
    steps = []
    for step in workflow.steps:
        for key, val in iter(step):
            if type(val) is str:
                setattr(step, key, value_substitution(val, parameters))

        step.args = walk_and_replace(step.args, parameters)
        steps.append(step)
    workflow.steps = steps
