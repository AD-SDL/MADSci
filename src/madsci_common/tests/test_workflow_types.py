"""Tests for workflow types and validation."""

from pathlib import Path

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
                use_parameters=StepParameters(args={"arg1": inline_param}),
            )
        ],
    )

    # The validator should have promoted the inline parameter
    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "inline_param"
    assert workflow_def.parameters.json_inputs[0].default == "default_value"

    # The step parameter should now be a string key
    assert workflow_def.steps[0].use_parameters.args["arg1"] == "inline_param"


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
                use_parameters=StepParameters(locations={"deck": inline_param}),
            )
        ],
    )

    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "location_param"
    assert workflow_def.steps[0].use_parameters.locations["deck"] == "location_param"


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
                use_parameters=StepParameters(action=inline_param),
            )
        ],
    )

    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "action_param"
    assert workflow_def.steps[0].use_parameters.action == "action_param"


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
                use_parameters=StepParameters(args={"data_input": inline_ff_param}),
            )
        ],
    )

    assert len(workflow_def.parameters.feed_forward) == 1
    assert workflow_def.parameters.feed_forward[0].key == "ff_param"
    assert workflow_def.steps[0].use_parameters.args["data_input"] == "ff_param"


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
                use_parameters=StepParameters(args={"arg1": input_param}),
                files={"file1": file_param},
            ),
            StepDefinition(
                name="step2",
                action="action2",
                node="node2",
                use_parameters=StepParameters(args={"data": ff_param}),
            ),
        ],
    )

    assert len(workflow_def.parameters.json_inputs) == 1
    assert len(workflow_def.parameters.file_inputs) == 1
    assert len(workflow_def.parameters.feed_forward) == 1

    assert workflow_def.parameters.json_inputs[0].key == "input1"
    assert workflow_def.parameters.file_inputs[0].key == "file1"
    assert workflow_def.parameters.feed_forward[0].key == "ff1"

    assert workflow_def.steps[0].use_parameters.args["arg1"] == "input1"
    assert workflow_def.steps[0].files["file1"] == "file1"
    assert workflow_def.steps[1].use_parameters.args["data"] == "ff1"


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
                use_parameters=StepParameters(
                    args={"arg1": "existing_param"}  # String reference, not inline
                ),
            )
        ],
    )

    # Should preserve existing parameters without adding new ones
    assert len(workflow_def.parameters.json_inputs) == 1
    assert workflow_def.parameters.json_inputs[0].key == "existing_param"
    assert workflow_def.steps[0].use_parameters.args["arg1"] == "existing_param"


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


# --- YAML format compatibility tests ---


class TestWorkflowYAMLCompatibility:
    """Test that WorkflowDefinition accepts user-friendly YAML formats."""

    def test_metadata_alias(self):
        """The 'metadata' key should map to 'definition_metadata'."""
        wf = WorkflowDefinition.model_validate(
            {
                "name": "Test",
                "metadata": {"author": "Alice", "version": "2.0"},
                "steps": [],
            }
        )
        assert wf.definition_metadata.author == "Alice"
        assert wf.definition_metadata.version == "2.0"

    def test_info_alias_for_description(self):
        """The 'info' key inside metadata should map to 'description'."""
        wf = WorkflowDefinition.model_validate(
            {
                "name": "Test",
                "metadata": {"info": "A useful workflow"},
                "steps": [],
            }
        )
        assert wf.definition_metadata.description == "A useful workflow"

    def test_root_description_promoted_to_metadata(self):
        """Root-level 'description' should be promoted into definition_metadata."""
        wf = WorkflowDefinition.model_validate(
            {"name": "Test", "description": "Root desc", "steps": []}
        )
        assert wf.definition_metadata.description == "Root desc"

    def test_root_description_does_not_override_metadata_description(self):
        """If metadata already has description, root description is dropped."""
        wf = WorkflowDefinition.model_validate(
            {
                "name": "Test",
                "description": "Root desc",
                "metadata": {"description": "Meta desc"},
                "steps": [],
            }
        )
        assert wf.definition_metadata.description == "Meta desc"

    def test_simplified_parameter_format(self):
        """Simplified [{name, type, default}] parameters should be coerced."""
        wf = WorkflowDefinition.model_validate(
            {
                "name": "Test",
                "parameters": [
                    {
                        "name": "message",
                        "type": "string",
                        "description": "A message",
                        "default": "hello",
                    }
                ],
                "steps": [{"name": "s1", "node": "n1", "action": "a1", "args": {}}],
            }
        )
        assert len(wf.parameters.json_inputs) == 1
        param = wf.parameters.json_inputs[0]
        assert param.key == "message"
        assert param.default == "hello"
        assert param.description == "A message"
        assert param.parameter_type == "json_input"

    def test_simplified_parameters_mixed_with_typed(self):
        """Simplified params can coexist with properly typed params."""
        wf = WorkflowDefinition.model_validate(
            {
                "name": "Test",
                "parameters": [
                    {"name": "simple_param", "default": 42},
                    {
                        "key": "typed_param",
                        "parameter_type": "json_input",
                        "default": "typed",
                    },
                ],
                "steps": [{"name": "s1", "node": "n1", "action": "a1", "args": {}}],
            }
        )
        assert len(wf.parameters.json_inputs) == 2
        assert wf.parameters.json_inputs[0].key == "simple_param"
        assert wf.parameters.json_inputs[1].key == "typed_param"

    def test_canonical_format_still_works(self):
        """The canonical json_inputs/file_inputs dict format still works."""
        wf = WorkflowDefinition.model_validate(
            {
                "name": "Test",
                "parameters": {
                    "json_inputs": [{"key": "param1", "default": 0}],
                    "file_inputs": [{"key": "protocol_file"}],
                },
                "steps": [],
            }
        )
        assert len(wf.parameters.json_inputs) == 1
        assert len(wf.parameters.file_inputs) == 1

    def test_example_workflows_parse(self):
        """All example workflow files should parse with metadata preserved."""
        examples_dir = Path("examples/example_lab/workflows")
        if not examples_dir.exists():
            pytest.skip("Example workflows directory not found")

        for workflow_file in sorted(examples_dir.glob("*.workflow.yaml")):
            wf = WorkflowDefinition.from_yaml(workflow_file)
            assert wf.name, f"{workflow_file.name}: name should not be empty"
            assert wf.definition_metadata.author is not None, (
                f"{workflow_file.name}: author should be parsed from metadata"
            )
