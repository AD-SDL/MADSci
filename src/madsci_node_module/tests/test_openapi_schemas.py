"""Comprehensive OpenAPI schema validation tests."""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.action_types import ActionFiles
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import NodeDefinition
from madsci.node_module.helpers import action
from pydantic import BaseModel, Field

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig
from madsci_node_module.tests.test_rest_utils import execute_action_and_wait


# Test result models for schema validation
class SimpleTestResult(BaseModel):
    """Simple test result model."""

    value: int = Field(description="Simple integer value")
    message: str = Field(description="Status message")


class ComplexTestResult(BaseModel):
    """Complex test result model with nested data."""

    id: str = Field(description="Unique identifier")
    measurements: List[float] = Field(description="List of measurement values")
    metadata: Dict[str, Any] = Field(description="Additional metadata")
    timestamp: datetime = Field(description="Processing timestamp")


class NestedTestResult(BaseModel):
    """Test result with nested models."""

    primary: SimpleTestResult = Field(description="Primary result data")
    secondary: Optional[SimpleTestResult] = Field(
        default=None, description="Optional secondary data"
    )
    status: str = Field(description="Overall status")


class OptionalFieldsResult(BaseModel):
    """Test result with various optional field types."""

    required_field: str = Field(description="Always present field")
    optional_string: Optional[str] = Field(
        default=None, description="Optional string field"
    )
    optional_int: Optional[int] = Field(
        default=None, description="Optional integer field"
    )
    optional_list: Optional[List[str]] = Field(
        default=None, description="Optional list field"
    )
    optional_dict: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional dict field"
    )


class SampleProcessingRequest(BaseModel):
    """Example complex input model for testing pydantic argument handling"""

    sample_ids: list[str] = Field(description="List of sample identifiers to process")
    processing_type: str = Field(description="Type of processing to perform")
    parameters: dict[str, Union[str, int, float]] = Field(
        description="Processing parameters"
    )
    priority: int = Field(description="Processing priority (1-10)", ge=1, le=10)
    notify_on_completion: bool = Field(
        default=False, description="Whether to send notifications"
    )


class AnalysisResult(BaseModel):
    """Example custom pydantic model for analysis results"""

    sample_id: str = Field(description="Unique identifier for the sample")
    concentration: float = Field(description="Measured concentration in mg/mL")
    ph_level: float = Field(description="pH level of the sample")
    temperature: float = Field(description="Temperature in Celsius during measurement")
    quality_score: int = Field(description="Quality score from 0-100", ge=0, le=100)
    notes: str = Field(default="", description="Additional notes about the analysis")


class TestFileOutput(ActionFiles):
    """Test file output model for argument testing"""

    log_file_1: Path
    log_file_2: Path


class TestFiles(ActionFiles):
    """Test file result model."""

    data_file: Path
    config_file: Path


class OpenAPISchemaTestNode(TestNode):
    """Test node for OpenAPI schema validation."""

    @action
    def test_action(self, test_param: int) -> None:
        """A test action with required parameter for validation testing."""
        result = self.test_interface.run_command(
            f"Test action with param {test_param}."
        )
        if result:
            return
        raise ValueError(f"`run_command` returned '{result}'. Expected 'True'.")

    @action
    def return_int(self) -> int:
        """Action that returns a simple integer."""
        return 42

    @action
    def return_string(self) -> str:
        """Action that returns a simple string."""
        return "test_string"

    @action
    def return_float(self) -> float:
        """Action that returns a simple float."""
        return 3.14159

    @action
    def return_bool(self) -> bool:
        """Action that returns a simple boolean."""
        return True

    @action
    def return_dict(self) -> dict:
        """Action that returns a dictionary."""
        return {"key": "value", "number": 123, "flag": True}

    @action
    def return_list(self) -> list:
        """Action that returns a list."""
        return [1, 2, 3, "four", 5.0]

    @action
    def return_simple_model(self) -> SimpleTestResult:
        """Action that returns a simple Pydantic model."""
        return SimpleTestResult(value=42, message="success")

    @action
    def return_complex_model(self) -> ComplexTestResult:
        """Action that returns a complex Pydantic model."""
        return ComplexTestResult(
            id="test_001",
            measurements=[1.0, 2.5, 3.7],
            metadata={"instrument": "test", "operator": "user"},
            timestamp=datetime.now(),
        )

    @action
    def return_single_file(self) -> Path:
        """Action that returns a single file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test file content")
            return Path(f.name)

    @action
    def return_multiple_files(self) -> TestFiles:
        """Action that returns multiple files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".dat") as f1:
            f1.write("data content")
            data_path = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".cfg") as f2:
            f2.write("config content")
            config_path = Path(f2.name)

        return TestFiles(data_file=data_path, config_file=config_path)

    @action
    def return_nested_model(self) -> NestedTestResult:
        """Action that returns a nested Pydantic model."""
        primary = SimpleTestResult(value=10, message="primary")
        secondary = SimpleTestResult(value=20, message="secondary")
        return NestedTestResult(
            primary=primary, secondary=secondary, status="completed"
        )

    @action
    def return_optional_fields_model(self) -> OptionalFieldsResult:
        """Action that returns a model with optional fields."""
        return OptionalFieldsResult(
            required_field="always_present",
            optional_string="present_string",
            optional_int=42,
            optional_list=["item1", "item2"],
            optional_dict={"key": "value"},
        )

    @action
    def mixed_return(self) -> tuple[SimpleTestResult, Path]:
        """Action that returns both a model and a file."""
        result = SimpleTestResult(value=100, message="mixed")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("mixed return file")
            file_path = Path(f.name)

        return result, file_path

    # ============================================================================
    # Argument Testing Actions
    # ============================================================================

    @action
    def test_simple_string_arg(self, message: str) -> str:
        """Test action with a simple string argument"""
        return f"Processed: {message}"

    @action
    def test_simple_int_arg(self, number: int) -> int:
        """Test action with a simple integer argument"""
        return number * 2

    @action
    def test_simple_float_arg(self, value: float) -> float:
        """Test action with a simple float argument"""
        return round(value * 3.14, 2)

    @action
    def test_simple_bool_arg(self, flag: bool) -> bool:
        """Test action with a simple boolean argument"""
        return not flag

    @action
    def test_multiple_simple_args(
        self, name: str, age: int, height: float, active: bool
    ) -> dict:
        """Test action with multiple simple arguments of different types"""
        return {
            "name": name.upper(),
            "age_doubled": age * 2,
            "height_cm": height * 100,
            "status": "active" if active else "inactive",
        }

    @action
    def test_optional_string_arg(
        self, message: str, prefix: Optional[str] = None
    ) -> str:
        """Test action with optional string argument"""
        return f"{prefix}: {message}" if prefix else message

    @action
    def test_optional_with_defaults(
        self,
        required_param: str,
        optional_int: Optional[int] = None,
        default_string: str = "default_value",
        default_float: float = 1.0,
        default_bool: bool = False,
    ) -> dict:
        """Test action with various optional parameters and defaults"""
        return {
            "required": required_param,
            "optional_int": optional_int
            if optional_int is not None
            else "not_provided",
            "default_string": default_string,
            "default_float": default_float,
            "default_bool": default_bool,
        }

    @action
    def test_annotated_args(
        self,
        annotated_int: Annotated[int, "An annotated integer parameter"] = 42,
        annotated_str: Annotated[str, "An annotated string parameter"] = "default",
        optional_annotated: Optional[
            Annotated[float, "Optional annotated float"]
        ] = None,
    ) -> dict:
        """Test action with annotated type parameters"""
        return {
            "annotated_int": annotated_int,
            "annotated_str": annotated_str,
            "optional_annotated": optional_annotated,
        }

    @action
    def test_list_args(self, string_list: list[str], number_list: list[int]) -> dict:
        """Test action with list arguments"""
        return {
            "string_count": len(string_list),
            "strings_upper": [s.upper() for s in string_list],
            "number_sum": sum(number_list),
            "number_max": max(number_list) if number_list else 0,
        }

    @action
    def test_dict_args(self, config: dict[str, Union[str, int, float]]) -> dict:
        """Test action with dictionary argument"""
        processed_config = {}
        for key, value in config.items():
            if isinstance(value, str):
                processed_config[f"{key}_processed"] = value.upper()
            elif isinstance(value, (int, float)):
                processed_config[f"{key}_doubled"] = value * 2
        return processed_config

    @action
    def test_pydantic_input(self, request: SampleProcessingRequest) -> dict:
        """Test action with pydantic model as input"""
        # Handle case where framework passes dict instead of pydantic model
        if isinstance(request, dict):
            request = SampleProcessingRequest(**request)

        return {
            "processing_type": request.processing_type,
            "sample_count": len(request.sample_ids),
            "priority": request.priority,
            "estimated_time": len(request.sample_ids) * request.priority * 5,
            "notifications_enabled": request.notify_on_completion,
        }

    @action
    def test_file_input(self, input_file: Path) -> str:
        """Test action with file path input"""
        # Handle case where framework passes string instead of Path
        if isinstance(input_file, str):
            input_file = Path(input_file)
        if input_file.exists():
            with input_file.open("r") as f:
                content = f.read()
            return f"File content length: {len(content)} characters"
        return f"File not found: {input_file}"

    @action
    def test_location_input(self, target_location: LocationArgument) -> dict:
        """Test action with location argument"""
        return {
            "location_representation": str(target_location.representation),
            "location_name": target_location.location_name,
            "resource_id": target_location.resource_id,
            "has_reservation": target_location.reservation is not None,
        }

    # ============================================================================
    # Variable Arguments Tests (*args, **kwargs)
    # ============================================================================

    @action
    def test_var_args_only(self, required_param: str, *args) -> dict:
        """Action that accepts additional positional arguments."""
        return {
            "required_param": required_param,
            "var_args": list(args),
            "var_args_count": len(args),
        }

    @action
    def test_var_kwargs_only(self, required_param: str, **kwargs) -> dict:
        """Action that accepts additional keyword arguments."""
        return {
            "required_param": required_param,
            "var_kwargs": kwargs,
            "var_kwargs_count": len(kwargs),
        }

    @action
    def test_var_args_and_kwargs(self, required_param: str, *args, **kwargs) -> dict:
        """Action that accepts both additional positional and keyword arguments."""
        return {
            "required_param": required_param,
            "var_args": list(args),
            "var_kwargs": kwargs,
            "total_extra_params": len(args) + len(kwargs),
        }

    @action
    def test_mixed_params_with_var_args(
        self,
        required_param: str,
        optional_param: int = 10,
        *args,
    ) -> dict:
        """Action with required, optional, and variable positional arguments."""
        return {
            "required_param": required_param,
            "optional_param": optional_param,
            "var_args": list(args),
        }

    @action
    def test_mixed_params_with_var_kwargs(
        self,
        required_param: str,
        optional_param: int = 10,
        **kwargs,
    ) -> dict:
        """Action with required, optional, and variable keyword arguments."""
        return {
            "required_param": required_param,
            "optional_param": optional_param,
            "var_kwargs": kwargs,
        }


@pytest.fixture
def openapi_test_node() -> OpenAPISchemaTestNode:
    """Create an OpenAPI test node instance."""
    node_definition = NodeDefinition(
        node_name="OpenAPI Schema Test Node",
        module_name="openapi_schema_test_node",
        description="Test node for OpenAPI schema validation.",
    )

    node = OpenAPISchemaTestNode(
        node_definition=node_definition,
        node_config=TestNodeConfig(test_required_param=1),
    )
    node.start_node(testing=True)
    return node


@pytest.fixture
def openapi_test_client(openapi_test_node) -> TestClient:
    """Create test client for OpenAPI test node."""
    with TestClient(openapi_test_node.rest_api) as client:
        time.sleep(0.5)  # Wait for startup to complete
        yield client


class TestSchemaGeneration:
    """Test OpenAPI schema generation for different return types."""

    @pytest.mark.parametrize(
        "return_type,expected_schema_type,action_name",
        [
            (int, "integer", "return_int"),
            (str, "string", "return_string"),
            (float, "number", "return_float"),
            (bool, "boolean", "return_bool"),
            (dict, "object", "return_dict"),
            (list, "array", "return_list"),
        ],
    )
    def test_basic_type_schema_generation(
        self,
        openapi_test_client: TestClient,
        return_type,  # noqa: ARG002
        expected_schema_type,
        action_name,
    ):
        """Test schema generation for basic return types."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})
        action_path = f"/action/{action_name}"

        assert action_path in paths

        # Check the response schema
        post_spec = paths[action_path]["post"]
        responses = post_spec.get("responses", {})
        success_response = responses.get("200", {})
        content = success_response.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})

        # For basic types, check the result field type
        properties = schema.get("properties", {})
        if "result" in properties:
            result_schema = properties["result"]
            assert (
                result_schema.get("type") == expected_schema_type
                or result_schema.get("$ref") is not None
            )  # For complex types

    @pytest.mark.parametrize(
        "model_action,expected_properties",
        [
            ("return_simple_model", ["value", "message"]),
            ("return_complex_model", ["id", "measurements", "metadata", "timestamp"]),
        ],
    )
    def test_pydantic_model_schema_generation(
        self,
        openapi_test_client: TestClient,
        model_action,  # noqa: ARG002
        expected_properties,
    ):
        """Test schema generation for Pydantic model returns."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()

        # Check that model schemas are defined in components
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})

        # Find the model schema (exact name may vary)
        model_schemas = [
            s
            for name, s in schemas.items()
            if isinstance(s, dict) and "properties" in s
        ]

        # Should have at least one model schema with expected properties
        found_matching_schema = False
        for schema in model_schemas:
            schema_props = set(schema.get("properties", {}).keys())
            if all(prop in schema_props for prop in expected_properties):
                found_matching_schema = True
                break

        assert found_matching_schema, (
            f"No schema found with properties {expected_properties}"
        )

    def test_file_return_schema_generation(self, openapi_test_client: TestClient):
        """Test schema generation for file returns."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # Check single file return
        single_file_path = "/action/return_single_file"
        assert single_file_path in paths

        # Check multiple file return
        multiple_files_path = "/action/return_multiple_files"
        assert multiple_files_path in paths

    def test_mixed_return_schema_generation(self, openapi_test_client: TestClient):
        """Test schema generation for mixed returns (model + file)."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        mixed_path = "/action/mixed_return"
        assert mixed_path in paths

        # The action creation endpoint should exist and have proper structure
        post_spec = paths[mixed_path]["post"]
        assert "responses" in post_spec
        assert "200" in post_spec["responses"]

        # Also check that the result endpoint exists for this action
        result_path = "/action/mixed_return/{action_id}/result"
        assert result_path in paths


class TestSchemaValidation:
    """Test schema validation accuracy and consistency."""

    @pytest.mark.parametrize(
        "action_name,test_params",
        [
            ("return_int", {}),
            ("return_string", {}),
            ("return_float", {}),
            ("return_bool", {}),
            ("return_dict", {}),
            ("return_list", {}),
            ("return_simple_model", {}),
            ("return_complex_model", {}),
            ("return_single_file", {}),
            ("return_multiple_files", {}),
            ("mixed_return", {}),
        ],
    )
    def test_action_execution_matches_schema(
        self, openapi_test_client: TestClient, action_name, test_params
    ):
        """Test that action execution results match the generated schema."""
        # Create and execute action with RestActionRequest structure
        request_data = {"args": test_params}
        response = openapi_test_client.post(f"/action/{action_name}", json=request_data)
        assert response.status_code == 200
        action_id = response.json()["action_id"]

        # Start action
        response = openapi_test_client.post(f"/action/{action_name}/{action_id}/start")
        assert response.status_code == 200

        # Wait for completion and get result
        time.sleep(0.5)
        response = openapi_test_client.get(f"/action/{action_id}/result")
        assert response.status_code == 200

        result = response.json()
        assert "status" in result
        assert result["status"] in ["succeeded", "failed", "running"]

        # If succeeded, should have result and/or files based on action type
        if result["status"] == "succeeded" and action_name.startswith("return_"):
            # Should have some kind of result
            assert "result" in result or "files" in result

    def test_openapi_spec_validity(self, openapi_test_client: TestClient):
        """Test that the generated OpenAPI spec is valid."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()

        # Basic OpenAPI spec structure
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

        # Should have action paths
        paths = openapi_schema["paths"]
        action_paths = [path for path in paths if path.startswith("/action/")]
        assert len(action_paths) > 0

        # Action creation paths (without {action_id}) should have a POST method
        action_creation_paths = [
            path
            for path in action_paths
            if "{action_id}" not in path and path != "/action"
        ]
        assert len(action_creation_paths) > 0

        for action_path in action_creation_paths:
            path_spec = paths[action_path]
            assert "post" in path_spec

            post_spec = path_spec["post"]
            assert "responses" in post_spec
            assert "200" in post_spec["responses"]

    def test_schema_consistency_across_endpoints(self, openapi_test_client: TestClient):
        """Test that schema definitions are consistent across different endpoints."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # Check that action creation endpoints have consistent schema structures
        action_creation_paths = [
            path
            for path in paths
            if path.startswith("/action/")
            and "{action_id}" not in path
            and path != "/action"
        ]

        for action_path in action_creation_paths:
            path_spec = paths[action_path]
            if "post" not in path_spec:
                continue  # Skip non-POST endpoints

            post_spec = path_spec["post"]

            # All actions should have consistent response structure
            responses = post_spec.get("responses", {})
            success_response = responses.get("200")
            assert success_response is not None

            # Should have content defined
            content = success_response.get("content", {})
            assert "application/json" in content


class TestParameterValidation:
    """Test parameter validation in OpenAPI schemas."""

    def test_required_parameters_validation(self, openapi_test_client: TestClient):
        """Test that required parameters are properly validated."""
        # Test action with missing required parameters (using base TestNode actions)
        response = openapi_test_client.post("/action/test_action", json={"args": {}})
        assert response.status_code == 422  # Validation error

        # Test with correct parameters
        response = openapi_test_client.post(
            "/action/test_action", json={"args": {"test_param": 1}}
        )
        assert response.status_code == 200

    def test_parameter_type_validation(self, openapi_test_client: TestClient):
        """Test that parameter types are properly validated."""
        # Test with wrong parameter type
        response = openapi_test_client.post(
            "/action/test_action", json={"args": {"test_param": "not_int"}}
        )
        assert response.status_code == 422  # Validation error

        # Test with correct type
        response = openapi_test_client.post(
            "/action/test_action", json={"args": {"test_param": 42}}
        )
        assert response.status_code == 200


class TestDocumentationGeneration:
    """Test that proper documentation is generated in the OpenAPI schema."""

    def test_action_descriptions_present(self, openapi_test_client: TestClient):
        """Test that action descriptions are included in the schema."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # Check that at least some actions have descriptions
        described_actions = 0
        for path, spec in paths.items():
            if path.startswith("/action/"):
                post_spec = spec.get("post", {})
                if "summary" in post_spec or "description" in post_spec:
                    described_actions += 1

        # Should have at least some documented actions
        assert described_actions > 0

    def test_parameter_documentation(self, openapi_test_client: TestClient):
        """Test that parameters are properly documented."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # Check test_action documentation
        test_action_path = "/action/test_action"
        if test_action_path in paths:
            post_spec = paths[test_action_path]["post"]
            request_body = post_spec.get("requestBody", {})
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema", {})
            properties = schema.get("properties", {})

            # Should have args field with test_param documented inside
            if "args" in properties:
                args_schema = properties["args"]
                # args should be an object with properties
                if "$ref" in args_schema:
                    # If it's a reference, we'd need to follow it to components/schemas
                    # For now, just verify the reference exists
                    assert args_schema["$ref"] is not None
                elif "properties" in args_schema:
                    # Direct properties in args
                    args_properties = args_schema["properties"]
                    if "test_param" in args_properties:
                        param_schema = args_properties["test_param"]
                        assert "type" in param_schema


class TestArgumentSchemaGeneration:
    """Test that OpenAPI schemas accurately represent action argument types."""

    def _get_schema_props(self, schema_ref_or_props, components):
        """Helper to get properties from either a $ref or direct properties"""
        if "$ref" in schema_ref_or_props:
            ref_path = schema_ref_or_props["$ref"]
            model_name = ref_path.split("/")[-1]
            assert model_name in components
            return components[model_name]["properties"]
        return schema_ref_or_props["properties"]

    def _get_schema_required(self, schema_ref_or_props, components):
        """Helper to get required fields from either a $ref or direct properties"""
        if "$ref" in schema_ref_or_props:
            ref_path = schema_ref_or_props["$ref"]
            model_name = ref_path.split("/")[-1]
            assert model_name in components
            return components[model_name].get("required", [])
        return schema_ref_or_props.get("required", [])

    @pytest.mark.parametrize(
        "action_name,param_name,expected_type",
        [
            ("test_simple_string_arg", "message", "string"),
            ("test_simple_int_arg", "number", "integer"),
            ("test_simple_float_arg", "value", "number"),
            ("test_simple_bool_arg", "flag", "boolean"),
        ],
    )
    def test_simple_argument_schemas_are_generated(
        self, openapi_test_client, action_name, param_name, expected_type
    ):
        """Test that simple argument types generate correct OpenAPI parameter schemas."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

        paths = schema.get("paths", {})
        components = schema.get("components", {}).get("schemas", {})

        # Check argument schema
        action_path = f"/action/{action_name}"
        assert action_path in paths
        post_spec = paths[action_path]["post"]
        request_schema = post_spec["requestBody"]["content"]["application/json"][
            "schema"
        ]

        # With RestActionRequest structure, parameters are in the args field
        props = self._get_schema_props(request_schema, components)
        assert "args" in props
        args_schema = props["args"]
        args_props = self._get_schema_props(args_schema, components)
        assert param_name in args_props
        param_prop = args_props[param_name]
        assert param_prop["type"] == expected_type

    def test_multiple_arguments_schema_generation(self, openapi_test_client):
        """Test that actions with multiple arguments generate correct schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        paths = schema.get("paths", {})
        components = schema.get("components", {}).get("schemas", {})
        multi_arg_path = "/action/test_multiple_simple_args"
        assert multi_arg_path in paths

        multi_schema = paths[multi_arg_path]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        props = self._get_schema_props(multi_schema, components)

        # With RestActionRequest structure, parameters are in the args field
        assert "args" in props
        args_schema = props["args"]
        args_props = self._get_schema_props(args_schema, components)

        # Should have all four arguments
        assert "name" in args_props
        assert "age" in args_props
        assert "height" in args_props
        assert "active" in args_props

        # Check types
        assert args_props["name"]["type"] == "string"
        assert args_props["age"]["type"] == "integer"
        assert args_props["height"]["type"] == "number"
        assert args_props["active"]["type"] == "boolean"

        # Should mark all as required - check in the args schema
        args_required = self._get_schema_required(args_schema, components)
        assert "name" in args_required
        assert "age" in args_required
        assert "height" in args_required
        assert "active" in args_required

    def test_pydantic_model_arguments_schema_generation(self, openapi_test_client):
        """Test that pydantic model arguments generate detailed schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})
        paths = schema.get("paths", {})

        pydantic_path = "/action/test_pydantic_input"
        assert pydantic_path in paths

        pydantic_schema = paths[pydantic_path]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        props = self._get_schema_props(pydantic_schema, components)

        # With RestActionRequest structure, parameters are in the args field
        assert "args" in props
        args_schema = props["args"]
        args_props = self._get_schema_props(args_schema, components)

        assert "request" in args_props
        request_prop = args_props["request"]

        # Should reference the SampleProcessingRequest model
        if "$ref" in request_prop:
            ref_path = request_prop["$ref"]
            model_name = ref_path.split("/")[-1]
            assert model_name in components

            # Check the referenced model has expected fields
            referenced_model = components[model_name]
            model_props = referenced_model["properties"]
            assert "sample_ids" in model_props
            assert "processing_type" in model_props
            assert "parameters" in model_props
            assert "priority" in model_props
            assert "notify_on_completion" in model_props


class TestRuntimeValidation:
    """Test that schemas match actual runtime behavior."""

    def test_simple_arguments_runtime_validation(self, openapi_test_client):
        """Test that simple arguments work correctly at runtime."""
        # Test string argument
        result = execute_action_and_wait(
            openapi_test_client, "test_simple_string_arg", {"message": "hello world"}
        )
        assert result["status"] == "succeeded"
        assert "hello world" in result["json_result"]

        # Test int argument
        result = execute_action_and_wait(
            openapi_test_client, "test_simple_int_arg", {"number": 21}
        )
        assert result["status"] == "succeeded"
        assert result["json_result"] == 42  # 21 * 2

        # Test float argument
        result = execute_action_and_wait(
            openapi_test_client, "test_simple_float_arg", {"value": 1.0}
        )
        assert result["status"] == "succeeded"
        assert abs(result["json_result"] - 3.14) < 0.01

        # Test bool argument
        result = execute_action_and_wait(
            openapi_test_client, "test_simple_bool_arg", {"flag": True}
        )
        assert result["status"] == "succeeded"
        assert result["json_result"] is False

    def test_optional_arguments_runtime_validation(self, openapi_test_client):
        """Test that optional arguments work correctly."""
        # Test with optional argument provided
        result = execute_action_and_wait(
            openapi_test_client,
            "test_optional_string_arg",
            {"message": "test", "prefix": "INFO"},
        )
        assert result["status"] == "succeeded"
        assert result["json_result"] == "INFO: test"

        # Test with optional argument omitted
        result = execute_action_and_wait(
            openapi_test_client, "test_optional_string_arg", {"message": "test"}
        )
        assert result["status"] == "succeeded"
        assert result["json_result"] == "test"

    def test_list_arguments_runtime_validation(self, openapi_test_client):
        """Test that list arguments work correctly."""
        result = execute_action_and_wait(
            openapi_test_client,
            "test_list_args",
            {"string_list": ["hello", "world"], "number_list": [1, 2, 3, 4, 5]},
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["string_count"] == 2
        assert json_result["strings_upper"] == ["HELLO", "WORLD"]
        assert json_result["number_sum"] == 15
        assert json_result["number_max"] == 5

    def test_pydantic_arguments_runtime_validation(self, openapi_test_client):
        """Test that pydantic model arguments work correctly."""
        request_data = {
            "sample_ids": ["S001", "S002", "S003"],
            "processing_type": "analysis",
            "parameters": {"temperature": 25.0, "ph": 7.0},
            "priority": 5,
            "notify_on_completion": True,
        }

        result = execute_action_and_wait(
            openapi_test_client, "test_pydantic_input", {"request": request_data}
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["processing_type"] == "analysis"
        assert json_result["sample_count"] == 3
        assert json_result["priority"] == 5
        assert json_result["estimated_time"] == 75  # 3 * 5 * 5
        assert json_result["notifications_enabled"] is True

    def test_location_arguments_runtime_validation(self, openapi_test_client):
        """Test that location arguments work correctly."""
        location_data = {
            "representation": {"x": 10, "y": 20, "z": 5},
            "location_name": "test_location",
            "resource_id": "resource_123",
        }

        result = execute_action_and_wait(
            openapi_test_client,
            "test_location_input",
            {"target_location": location_data},
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["location_name"] == "test_location"
        assert json_result["resource_id"] == "resource_123"
        assert json_result["has_reservation"] is False


class TestVariableArgumentsSupport:
    """Test support for *args and **kwargs in action definitions."""

    def _get_schema_props(self, schema: dict, components: dict) -> dict:
        """Helper to get properties from schema, handling $ref resolution."""
        if "$ref" in schema:
            ref_path = schema["$ref"]
            model_name = ref_path.split("/")[-1]
            if model_name in components:
                referenced_schema = components[model_name]
                return referenced_schema.get("properties", {})
            return {}
        return schema.get("properties", {})

    def _get_schema_required(self, schema: dict, components: dict) -> list:
        """Helper to get required fields from schema, handling $ref resolution."""
        if "$ref" in schema:
            ref_path = schema["$ref"]
            model_name = ref_path.split("/")[-1]
            if model_name in components:
                referenced_schema = components[model_name]
                return referenced_schema.get("required", [])
            return []
        return schema.get("required", [])

    def test_var_args_schema_generation(self, openapi_test_client):
        """Test that *args support is correctly reflected in OpenAPI schema."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        components = schema.get("components", {}).get("schemas", {})

        # Check if the var_args actions exist
        var_args_path = "/action/test_var_args_only"
        if var_args_path not in paths:
            pytest.skip(
                f"Test action {var_args_path} not found in OpenAPI schema. This test requires the OpenAPISchemaTestNode to include *args actions."
            )

        var_args_schema = paths[var_args_path]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        props = self._get_schema_props(var_args_schema, components)

        # Should have var_args field
        assert "var_args" in props
        var_args_prop = props["var_args"]

        # var_args is nullable, so it uses anyOf structure
        assert "anyOf" in var_args_prop
        # One of the anyOf options should be an array
        array_option = next(
            (opt for opt in var_args_prop["anyOf"] if opt.get("type") == "array"), None
        )
        assert array_option is not None, "var_args should allow array type"
        assert var_args_prop["title"] == "Variable Arguments"

    def test_var_args_runtime_execution(self, openapi_test_client):
        """Test that actions with *args execute correctly at runtime."""
        # Test with no extra args
        result = execute_action_and_wait(
            openapi_test_client,
            "test_var_args_only",
            {"required_param": "test"},
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["required_param"] == "test"
        assert json_result["var_args"] == []
        assert json_result["var_args_count"] == 0

        # Test with extra args
        result = execute_action_and_wait(
            openapi_test_client,
            "test_var_args_only",
            {"required_param": "test", "var_args": ["arg1", "arg2", 123]},
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["required_param"] == "test"
        assert json_result["var_args"] == ["arg1", "arg2", 123]
        assert json_result["var_args_count"] == 3

    def test_var_kwargs_runtime_execution(self, openapi_test_client):
        """Test that actions with **kwargs execute correctly at runtime."""
        # Test with no extra kwargs
        result = execute_action_and_wait(
            openapi_test_client,
            "test_var_kwargs_only",
            {"required_param": "test"},
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["required_param"] == "test"
        assert json_result["var_kwargs"] == {}
        assert json_result["var_kwargs_count"] == 0

        # Test with extra kwargs
        result = execute_action_and_wait(
            openapi_test_client,
            "test_var_kwargs_only",
            {
                "required_param": "test",
                "var_kwargs": {"extra1": "value1", "extra2": 42, "extra3": True},
            },
        )
        assert result["status"] == "succeeded"
        json_result = result["json_result"]
        assert json_result["required_param"] == "test"
        assert json_result["var_kwargs"] == {
            "extra1": "value1",
            "extra2": 42,
            "extra3": True,
        }
        assert json_result["var_kwargs_count"] == 3


class TestErrorHandling:
    """Test error handling in schema generation and validation."""

    def test_invalid_action_schema_handling(self, openapi_test_client: TestClient):
        """Test handling of requests to invalid actions."""
        response = openapi_test_client.post("/action/nonexistent_action", json={})
        assert response.status_code == 404

    def test_malformed_request_handling(self, openapi_test_client: TestClient):
        """Test handling of malformed requests."""
        # Test with invalid JSON structure
        response = openapi_test_client.post(
            "/action/return_int",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422]  # Bad request or validation error

    def test_argument_validation_errors(self, openapi_test_client):
        """Test that invalid arguments produce appropriate errors."""
        # Test missing required argument
        response = openapi_test_client.post(
            "/action/test_simple_string_arg",
            json={"args": {}},  # Missing required 'message'
        )
        assert response.status_code == 422  # Validation error

        # Test wrong type
        response = openapi_test_client.post(
            "/action/test_simple_int_arg", json={"args": {"number": "not_int"}}
        )
        assert response.status_code == 422  # Validation error
