"""Tests for workflow types and validation."""

import pytest
from madsci.common.types.parameter_types import (
    ParameterFeedForwardJson,
    ParameterInputFile,
    ParameterInputJson,
)
from madsci.common.types.step_types import StepDefinition, StepParameters
from madsci.common.types.workflow_types import WorkflowDefinition, WorkflowParameters


def test_promote_inline_step_parameters_args():
    """Test that inline parameters in step args get promoted to workflow level."""
    inline_param = ParameterInputJson(
        key="inline_param", description="An inline parameter", default="default_value"
    )

    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(),
        steps=[
            StepDefinition(
                name="test_step",
                action="test_action",
                node="test_node",
                parameters=StepParameters(args={"arg1": inline_param}),
            )
        ],
    )

    # The validator should have promoted the inline parameter
    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "inline_param"
    assert workflow_def.parameters.json_inputs[0].default == "default_value"

    # The step parameter should now be a string key
    assert workflow_def.steps[0].parameters.args["arg1"] == "inline_param"


def test_promote_inline_step_parameters_locations():
    """Test that inline parameters in step locations get promoted."""
    inline_param = ParameterInputJson(
        key="location_param", description="Location parameter"
    )

    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(),
        steps=[
            StepDefinition(
                name="test_step",
                action="test_action",
                node="test_node",
                parameters=StepParameters(locations={"deck": inline_param}),
            )
        ],
    )

    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "location_param"
    assert workflow_def.steps[0].parameters.locations["deck"] == "location_param"


def test_promote_inline_step_parameters_step_fields():
    """Test that inline parameters in step fields get promoted."""
    inline_param = ParameterInputJson(
        key="action_param", description="Action parameter"
    )

    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(),
        steps=[
            StepDefinition(
                name="test_step",
                node="test_node",
                parameters=StepParameters(action=inline_param),
            )
        ],
    )

    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "action_param"
    assert workflow_def.steps[0].parameters.action == "action_param"


def test_promote_inline_file_parameters():
    """Test that inline file parameters get promoted correctly."""
    inline_file_param = ParameterInputFile(
        key="file_input", description="Input file parameter"
    )

    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(),
        steps=[
            StepDefinition(
                name="test_step",
                action="test_action",
                node="test_node",
                files={"file_arg": inline_file_param},
            )
        ],
    )

    assert len(workflow_def.parameters.file_inputs) == 1
    assert workflow_def.parameters.file_inputs[0].key == "file_input"
    assert workflow_def.steps[0].files["file_arg"] == "file_input"


def test_promote_inline_feed_forward_parameters():
    """Test that inline feed forward parameters get promoted correctly."""
    inline_ff_param = ParameterFeedForwardJson(
        key="ff_param",
        description="Feed forward parameter",
        step="previous_step",
        label="output_data",
    )

    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(),
        steps=[
            StepDefinition(
                name="test_step",
                action="test_action",
                node="test_node",
                parameters=StepParameters(args={"data_input": inline_ff_param}),
            )
        ],
    )

    assert len(workflow_def.parameters.feed_forward) == 1
    assert workflow_def.parameters.feed_forward[0].key == "ff_param"
    assert workflow_def.steps[0].parameters.args["data_input"] == "ff_param"


def test_promote_multiple_inline_parameters():
    """Test promoting multiple inline parameters from multiple steps."""
    input_param = ParameterInputJson(key="input1", default="value1")
    file_param = ParameterInputFile(key="file1")
    ff_param = ParameterFeedForwardJson(key="ff1", step="step1", label="out1")

    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(),
        steps=[
            StepDefinition(
                name="step1",
                action="action1",
                node="node1",
                parameters=StepParameters(args={"arg1": input_param}),
                files={"file1": file_param},
            ),
            StepDefinition(
                name="step2",
                action="action2",
                node="node2",
                parameters=StepParameters(args={"data": ff_param}),
            ),
        ],
    )

    assert len(workflow_def.parameters.json_inputs) == 1
    assert len(workflow_def.parameters.file_inputs) == 1
    assert len(workflow_def.parameters.feed_forward) == 1

    assert workflow_def.parameters.json_inputs[0].key == "input1"
    assert workflow_def.parameters.file_inputs[0].key == "file1"
    assert workflow_def.parameters.feed_forward[0].key == "ff1"

    assert workflow_def.steps[0].parameters.args["arg1"] == "input1"
    assert workflow_def.steps[0].files["file1"] == "file1"
    assert workflow_def.steps[1].parameters.args["data"] == "ff1"


def test_no_inline_parameters():
    """Test that workflow with no inline parameters works normally."""
    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        parameters=WorkflowParameters(
            json_inputs=[ParameterInputJson(key="existing_param")]
        ),
        steps=[
            StepDefinition(
                name="test_step",
                action="test_action",
                node="test_node",
                parameters=StepParameters(
                    args={"arg1": "existing_param"}  # String reference, not inline
                ),
            )
        ],
    )

    # Should preserve existing parameters without adding new ones
    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "existing_param"
    assert workflow_def.steps[0].parameters.args["arg1"] == "existing_param"


def test_parameter_key_uniqueness_validation():
    """Test that the uniqueness validator works correctly."""
    with pytest.raises(ValueError, match="Input value keys must be unique"):
        WorkflowDefinition(
            name="Test Workflow",
            parameters=WorkflowParameters(
                json_inputs=[
                    ParameterInputJson(key="duplicate_key"),
                    ParameterInputJson(key="duplicate_key"),  # Duplicate key
                ]
            ),
            steps=[],
        )
