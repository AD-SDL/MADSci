"""Functions related to MADSci Workflows"""

from typing import Any, Optional

from madsci.common.types.base_types import PathLike
from madsci.common.types.workflow_types import WorkflowDefinition


def analyze_parameter_types(
    workflow_definition: WorkflowDefinition,
    input_values: Optional[dict[str, Any]],
) -> None:
    """Check the type of parameter input values"""
    if input_values:
        for parameter in workflow_definition.parameters.input_values:
            if (
                parameter.input_key in input_values
                and parameter.parameter_type
                and not (
                    type(input_values[parameter.input_key]).__name__
                    == parameter.parameter_type
                    or (
                        "Union" in parameter.parameter_type
                        and type(input_values[parameter.input_key]).__name__
                        in parameter.parameter_type
                    )
                )
            ):
                raise TypeError(
                    f"Input Value {parameter.input_key} has wrong type, must be type {parameter.parameter_type}"
                )


def check_parameters(
    workflow_definition: WorkflowDefinition,
    input_values: Optional[dict[str, Any]] = None,
) -> None:
    """Check that all required parameters are provided"""
    if input_values is not None:
        for input_value in workflow_definition.parameters.input_values:
            if input_value.input_key not in input_values:
                if input_value.default is not None:
                    input_values[input_value.input_key] = input_value.default
                else:
                    raise ValueError(
                        f"Required value {input_value.input_key} not provided"
                    )
    for ffv in workflow_definition.parameters.feed_forward_values:
        if ffv.name in input_values:
            raise ValueError(
                f"{ffv.name} is a Feed Forward Value and will be calculated during execution"
            )


def check_parameters_lists(
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
