"""Functions related to MADSci Workflows"""

from typing import Any, Optional

from madsci.common.types.base_types import PathLike
from madsci.common.types.workflow_types import WorkflowDefinition


def analyze_parameter_types(
    workflow_definition: WorkflowDefinition,
    json_inputs: Optional[dict[str, Any]],
) -> None:
    """Check the type of parameter input values"""
    if json_inputs:
        for parameter in workflow_definition.parameters.json_inputs:
            if (
                parameter.input_key in json_inputs
                and parameter.parameter_type
                and not (
                    type(json_inputs[parameter.input_key]).__name__
                    == parameter.parameter_type
                    or (
                        "Union" in parameter.parameter_type
                        and type(json_inputs[parameter.input_key]).__name__
                        in parameter.parameter_type
                    )
                )
            ):
                raise TypeError(
                    f"Input Value {parameter.input_key} has wrong type, must be type {parameter.parameter_type}"
                )


def check_parameters(
    workflow_definition: WorkflowDefinition,
    json_inputs: Optional[dict[str, Any]] = None,
) -> None:
    """Check that all required parameters are provided"""
    if json_inputs is not None:
        for json_input in workflow_definition.parameters.json_inputs:
            if json_input.input_key not in json_inputs:
                if json_input.default is not None:
                    json_inputs[json_input.input_key] = json_input.default
                else:
                    raise ValueError(
                        f"Required value {json_input.input_key} not provided"
                    )
    for ffv in workflow_definition.parameters.feed_forward:
        if ffv.name in json_inputs:
            raise ValueError(
                f"{ffv.name} is a Feed Forward Value and will be calculated during execution"
            )


def check_parameters_lists(
    workflows: list[str],
    json_inputs: list[dict[str, Any]] = [],
    file_inputs: list[dict[str, PathLike]] = [],
) -> tuple[list[dict[str, Any]], list[dict[str, PathLike]]]:
    """Check if the parameter lists are the right length"""
    if len(json_inputs) == 0:
        json_inputs = [{} for _ in workflows]
    if len(file_inputs) == 0:
        file_inputs = [{} for _ in workflows]
    if len(workflows) > len(json_inputs):
        raise ValueError(
            "Must submit json_inputs, in order, for each workflow, submit empty dictionaries if no json_inputs"
        )
    if len(workflows) > len(file_inputs):
        raise ValueError(
            "Must submit file_inputs, in order, for each workflow, submit empty dictionaries if no file_inputs"
        )
    return json_inputs, file_inputs
