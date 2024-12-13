from madsci.common.types.workflow_types import Workflow, WorkflowDefinition
from typing import Any

from pathlib import Path
import re
import copy
import requests
import json

class WorkflowClient:
    """a client for running workflows"""
    def __init__(self, workcell_manager_url: str, working_directory: str="~/.MADsci/temp") -> "WorkflowClient":
        """initialize the client"""
        self.url = workcell_manager_url
        self.working_directory = Path(working_directory)

    def send_workflow(self, workflow: str, parameters: dict, validate_only: bool = False) -> Workflow:
        """send a workflow to the workcell manager"""
        workflow = WorkflowDefinition.from_yaml(workflow)
        WorkflowDefinition.model_validate(workflow)
        insert_parameter_values(workflow=workflow, parameters=parameters)
        files = self._extract_files_from_workflow(workflow)
        url = self.url + "/start_workflow"
        response = requests.post(
            url,
            data={
                "workflow": workflow.model_dump_json(),
                "parameters": json.dumps(parameters),
                "validate_only": validate_only
                },
            files={
                ("files", (str(Path(path).name), Path.open(Path(path), "rb")))
                for _, path in files.items()
            },
            )
    def _extract_files_from_workflow(
        self, workflow: WorkflowDefinition
    ) -> dict[str, Any]:
        """
        Returns a dictionary of files from a workflow
        """
        files = {}
        for step in workflow.flowdef:
            if step.files:
                for file, path in step.files.items():
                    # * Try to get the file from the payload, if applicable
                    unique_filename = f"{step.step_id}_{file}"
                    files[unique_filename] = path
                    if not Path(files[unique_filename]).is_absolute():
                        files[unique_filename] = (
                            self.working_directory / files[unique_filename]
                        )
                    step.files[file] = Path(files[unique_filename]).name
        return files


def insert_parameter_values(workflow: WorkflowDefinition, parameters: dict[str, Any]) -> Workflow:
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
    for step in workflow.flowdef:
        for key, val in iter(step):
            if type(val) is str:
                setattr(step, key, value_substitution(val, parameters))

        step.args = walk_and_replace(step.args, parameters)
        steps.append(step)
    workflow.flowdef = steps


def walk_and_replace(args: dict[str, Any], input_parameters: dict[str, Any]) -> dict[str, Any]:
    """Recursively walk the arguments and replace all parameters"""
    new_args = copy.deepcopy(args)
    for key, val in args.items():
        if type(val) is str:
            new_args[key] = value_substitution(val, input_parameters)
        elif type(args[key]) is dict:
            new_args[key] = walk_and_replace(val, input_parameters)
        if type(key) is str:
            new_key = value_substitution(key, input_parameters)
            new_args[new_key] = new_args[key]
            if key is not new_key:
                new_args.pop(key, None)
    return new_args


def value_substitution(input_string: str, input_parameters: dict[str, Any]) -> str:
    """Perform $-string substitution on input string, returns string with substituted values"""
    # * Check if the string is a simple parameter reference
    if type(input_string) is str and re.match(r"^\$[A-z0-9_\-]*$", input_string):
        if input_string.strip("$") in input_parameters:
            input_string = input_parameters[input_string.strip("$")]
        else:
            raise ValueError(
                "Unknown parameter:"
                + input_string
                + ", please define it in the parameters section of the Workflow Definition."
            )
    else:
        # * Replace all parameter references contained in the string
        working_string = input_string
        for match in re.findall(r"((?<!\$)\$(?!\$)[A-z0-9_\-\{]*)(\})", input_string):
            if match[0][1] == "{":
                param_name = match[0].strip("$")
                param_name = param_name.strip("{")
                working_string = re.sub(
                    r"((?<!\$)\$(?!\$)[A-z0-9_\-\{]*)(\})",
                    str(input_parameters[param_name]),
                    working_string,
                )
                input_string = working_string
            else:
                raise SyntaxError(
                    "forgot opening { in parameter insertion: " + match[0] + "}"
                )
        for match in re.findall(
            r"((?<!\$)\$(?!\$)[A-z0-9_\-]*)(?![A-z0-9_\-])", input_string
        ):
            param_name = match.strip("$")
            if param_name in input_parameters:
                working_string = re.sub(
                    r"((?<!\$)\$(?!\$)[A-z0-9_\-]*)(?![A-z0-9_\-])",
                    str(input_parameters[param_name]),
                    working_string,
                )
                input_string = working_string
            else:
                raise ValueError(
                    "Unknown parameter:"
                    + param_name
                    + ", please define it in the parameters section of the Workflow Definition."
                )
    return input_string




