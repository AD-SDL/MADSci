Module madsci.common.workflows
==============================
Functions related to MADSci Workflows

Functions
---------

`analyze_parameter_types(workflow_definition: madsci.common.types.workflow_types.WorkflowDefinition, json_inputs: dict[str, typing.Any] | None) ‑> None`
:   Check the type of parameter input values

`check_parameters(workflow_definition: madsci.common.types.workflow_types.WorkflowDefinition, json_inputs: dict[str, typing.Any] | None = None) ‑> None`
:   Check that all required parameters are provided

`check_parameters_lists(workflows: list[str], json_inputs: list[dict[str, typing.Any]] = [], file_inputs: list[dict[str, str | pathlib.Path]] = []) ‑> tuple[list[dict[str, typing.Any]], list[dict[str, str | pathlib.Path]]]`
:   Check if the parameter lists are the right length
