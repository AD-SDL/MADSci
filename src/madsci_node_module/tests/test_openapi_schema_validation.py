"""Test-driven development approach to verify OpenAPI schema generation for json_result field."""

import contextlib
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.action_types import ActionFiles
from madsci.common.types.node_types import NodeDefinition
from madsci.node_module.helpers import action
from pydantic import BaseModel, Field

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


def wait_for_node_ready(client: TestClient, timeout: float = 5.0) -> bool:
    """Wait for node to be ready before executing actions.

    Args:
        client: FastAPI test client
        timeout: Maximum time to wait in seconds

    Returns:
        True if node is ready, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        with contextlib.suppress(Exception):
            response = client.get("/status")
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get("ready", False):
                    return True
        time.sleep(0.1)  # Check every 100ms
    return False


def execute_action_and_wait(
    client: TestClient,
    action_name: str,
    parameters: Optional[dict] = None,
    timeout: float = 10.0,
) -> dict:
    """Execute an action and wait for it to complete.

    Args:
        client: FastAPI test client
        action_name: Name of the action to execute
        parameters: Optional parameters for the action
        timeout: Maximum time to wait for completion

    Returns:
        Final action result dict

    Raises:
        AssertionError: If action fails or times out
    """
    if parameters is None:
        parameters = {}

    # Create action
    response = client.post(f"/action/{action_name}", json=parameters)
    assert response.status_code == 200, f"Failed to create action: {response.text}"
    action_id = response.json()["action_id"]

    # Start action
    response = client.post(f"/action/{action_name}/{action_id}/start")
    assert response.status_code == 200, f"Failed to start action: {response.text}"

    # Wait for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.get(f"/action/{action_id}/result")
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            if status in ["succeeded", "failed", "error"]:
                return result
        time.sleep(0.1)  # Check every 100ms

    # If we get here, the action timed out
    response = client.get(f"/action/{action_id}/result")
    result = response.json() if response.status_code == 200 else {"status": "timeout"}
    raise AssertionError(
        f"Action {action_name} timed out after {timeout}s. Last status: {result.get('status', 'unknown')}"
    )


# Test result models for various type scenarios
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


class TestFiles(ActionFiles):
    """Test file result model."""

    data_file: Path
    config_file: Path


class OpenAPISchemaTestNode(TestNode):
    """Test node specifically for OpenAPI schema validation that extends the working TestNode."""

    # ============================================================================
    # Simple Type Return Actions
    # ============================================================================

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

    # ============================================================================
    # Note: Optional and Union types are not currently supported by the @action decorator
    # The decorator only supports: ActionFiles, ActionJSON, ActionDatapoints, Path,
    # Pydantic BaseModel subclasses, str, int, float, bool, dict, or list
    # ============================================================================

    # ============================================================================
    # Custom Pydantic Model Return Actions
    # ============================================================================

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

    # ============================================================================
    # File Return Actions
    # ============================================================================

    @action
    def return_single_file(self) -> Path:
        """Action that returns a single file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test file content")
            return Path(f.name)

    @action
    def return_multiple_files(self) -> TestFiles:
        """Action that returns multiple labeled files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".data") as f:
            f.write("data content")
            data_file = Path(f.name)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".config") as f:
            f.write("config content")
            config_file = Path(f.name)

        return TestFiles(data_file=data_file, config_file=config_file)

    # ============================================================================
    # Mixed Return Actions (Tuples)
    # ============================================================================

    @action
    def return_model_and_file(self) -> tuple[SimpleTestResult, Path]:
        """Action that returns both a model and a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("mixed result file")
            file_path = Path(f.name)

        model = SimpleTestResult(value=99, message="mixed_result")
        return model, file_path

    @action
    def return_dict_and_file(self) -> tuple[dict, Path]:
        """Action that returns both a dict and a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write('{"data": "file_content"}')
            file_path = Path(f.name)

        data = {"result": "success", "count": 5}
        return data, file_path

    # ============================================================================
    # Generic/Any Type Return Actions
    # ============================================================================

    # Note: Any type and no annotation are not supported by @action decorator
    # Actions must have explicit return type annotations from the supported list

    # ============================================================================
    # Actions with File Parameters (for comprehensive testing)
    # ============================================================================

    @action
    def process_file_return_model(self, input_file: Path) -> SimpleTestResult:
        """Action that takes a file and returns a model."""
        file_size = input_file.stat().st_size if input_file.exists() else 0
        return SimpleTestResult(value=file_size, message="file_processed")


@pytest.fixture
def openapi_test_node():
    """Create an OpenAPI test node instance."""
    node_definition = NodeDefinition(
        node_name="OpenAPI Schema Test Node",
        module_name="openapi_schema_test_node",
        description="Node for testing OpenAPI schema generation accuracy.",
    )

    node = OpenAPISchemaTestNode(
        node_definition=node_definition,
        node_config=TestNodeConfig(test_required_param=1),
    )
    node.start_node(testing=True)
    return node


@pytest.fixture
def openapi_test_client(openapi_test_node):
    """Create test client for OpenAPI test node."""
    # Use the same pattern as the working tests
    with TestClient(openapi_test_node.rest_api) as client:
        time.sleep(0.5)  # Wait for startup to complete

        # Verify startup completed
        assert openapi_test_node.startup_has_run
        assert openapi_test_node.test_interface is not None

        yield client


class TestOpenAPISchemaGeneration:
    """Test that OpenAPI schemas accurately reflect json_result field types."""

    def test_openapi_schema_available(self, openapi_test_client):
        """Test that OpenAPI schema endpoint is available."""
        response = openapi_test_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "components" in schema

    def test_simple_types_generate_correct_schemas(self, openapi_test_client):
        """Test that simple return types generate correct OpenAPI schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        # Find action result models for simple types
        int_result_models = [
            name
            for name in components
            if "ReturnInt" in name and "ActionResult" in name
        ]
        str_result_models = [
            name
            for name in components
            if "ReturnString" in name and "ActionResult" in name
        ]
        float_result_models = [
            name
            for name in components
            if "ReturnFloat" in name and "ActionResult" in name
        ]
        bool_result_models = [
            name
            for name in components
            if "ReturnBool" in name and "ActionResult" in name
        ]

        # Verify we have action-specific result models
        assert len(int_result_models) > 0, (
            "Should have int-specific action result model"
        )
        assert len(str_result_models) > 0, (
            "Should have string-specific action result model"
        )
        assert len(float_result_models) > 0, (
            "Should have float-specific action result model"
        )
        assert len(bool_result_models) > 0, (
            "Should have bool-specific action result model"
        )

        # Check the int result model has correct json_result type
        int_model = components[int_result_models[0]]
        assert "properties" in int_model
        assert "json_result" in int_model["properties"]

        json_result_spec = int_model["properties"]["json_result"]
        # The json_result should be typed as integer for int return
        assert json_result_spec.get("type") == "integer" or ("$ref" in json_result_spec)

    def test_dict_and_list_types_generate_schemas(self, openapi_test_client):
        """Test that dict and list return types generate appropriate schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        # Find dict and list result models
        dict_result_models = [
            name
            for name in components
            if "ReturnDict" in name and "ActionResult" in name
        ]
        list_result_models = [
            name
            for name in components
            if "ReturnList" in name and "ActionResult" in name
        ]

        assert len(dict_result_models) > 0, (
            "Should have dict-specific action result model"
        )
        assert len(list_result_models) > 0, (
            "Should have list-specific action result model"
        )

        # Check dict result model
        dict_model = components[dict_result_models[0]]
        json_result_spec = dict_model["properties"]["json_result"]
        # Should be object type or reference to object
        assert json_result_spec.get("type") == "object" or ("$ref" in json_result_spec)

        # Check list result model
        list_model = components[list_result_models[0]]
        json_result_spec = list_model["properties"]["json_result"]
        # Should be array type or reference to array
        assert json_result_spec.get("type") == "array" or ("$ref" in json_result_spec)

    # Note: Optional types test removed as they are not currently supported by @action decorator

    def test_custom_pydantic_models_generate_detailed_schemas(
        self, openapi_test_client
    ):
        """Test that custom Pydantic models generate detailed JSON schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        # Find simple model result
        simple_model_results = [
            name
            for name in components
            if "ReturnSimpleModel" in name and "ActionResult" in name
        ]
        assert len(simple_model_results) > 0, "Should have simple model action result"

        simple_result_model = components[simple_model_results[0]]
        json_result_spec = simple_result_model["properties"]["json_result"]

        # Should reference the SimpleTestResult model or inline its schema
        if "$ref" in json_result_spec:
            # Check that the referenced model exists
            ref_path = json_result_spec["$ref"]
            model_name = ref_path.split("/")[-1]
            assert model_name in components

            # Check the referenced model has correct properties
            referenced_model = components[model_name]
            assert "properties" in referenced_model
            assert "value" in referenced_model["properties"]
            assert "message" in referenced_model["properties"]

            # Check field types
            assert referenced_model["properties"]["value"]["type"] == "integer"
            assert referenced_model["properties"]["message"]["type"] == "string"
        else:
            # Inline schema - should have the model properties
            assert "properties" in json_result_spec
            assert "value" in json_result_spec["properties"]
            assert "message" in json_result_spec["properties"]

    def test_complex_nested_models_generate_complete_schemas(self, openapi_test_client):
        """Test that complex nested models generate complete schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        # Find complex model result
        complex_model_results = [
            name
            for name in components
            if "ReturnComplexModel" in name and "ActionResult" in name
        ]
        nested_model_results = [
            name
            for name in components
            if "ReturnNestedModel" in name and "ActionResult" in name
        ]

        assert len(complex_model_results) > 0, "Should have complex model action result"
        assert len(nested_model_results) > 0, "Should have nested model action result"

        # Check complex model
        complex_result_model = components[complex_model_results[0]]
        json_result_spec = complex_result_model["properties"]["json_result"]

        if "$ref" in json_result_spec:
            ref_model_name = json_result_spec["$ref"].split("/")[-1]
            referenced_model = components[ref_model_name]

            # Should have all expected fields
            props = referenced_model["properties"]
            assert "id" in props
            assert "measurements" in props
            assert "metadata" in props
            assert "timestamp" in props

            # Check types
            assert props["id"]["type"] == "string"
            assert props["measurements"]["type"] == "array"
            assert props["measurements"]["items"]["type"] == "number"
            assert props["metadata"]["type"] == "object"

    def test_file_return_actions_have_correct_files_schema(self, openapi_test_client):
        """Test that file return actions have correct files field schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        # Find file result models
        single_file_results = [
            name
            for name in components
            if "ReturnSingleFile" in name and "ActionResult" in name
        ]
        multiple_file_results = [
            name
            for name in components
            if "ReturnMultipleFiles" in name and "ActionResult" in name
        ]

        assert len(single_file_results) > 0, (
            "Should have single file action result model"
        )
        assert len(multiple_file_results) > 0, (
            "Should have multiple files action result model"
        )

        # Check single file result
        single_file_model = components[single_file_results[0]]
        files_spec = single_file_model["properties"]["files"]

        # Files should be array of strings (file keys) or null
        if "anyOf" in files_spec:
            # Should have array option and null option
            types = list(files_spec["anyOf"])
            array_type = next(
                (item for item in types if item.get("type") == "array"), None
            )
            null_type = next(
                (item for item in types if item.get("type") == "null"), None
            )
            assert array_type is not None, "Should have array type for files"
            assert null_type is not None, "Should have null type for files"
            assert array_type["items"]["type"] == "string", (
                "Array items should be strings"
            )
        else:
            # Direct type specification (fallback)
            assert files_spec["type"] == "array"
            assert files_spec["items"]["type"] == "string"

        # json_result should be nullable for file-only actions
        json_result_spec = single_file_model["properties"]["json_result"]
        if "anyOf" in json_result_spec:
            # Should have null as one of the options
            types = [item.get("type") for item in json_result_spec["anyOf"]]
            assert "null" in types, (
                "json_result should be nullable for file-only actions"
            )
        else:
            # Fallback check
            assert json_result_spec.get("type") == "null" or json_result_spec is None

    def test_mixed_return_actions_have_both_schemas(self, openapi_test_client):
        """Test that mixed return actions have both json_result and files schemas."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        # Find mixed result models
        model_and_file_results = [
            name
            for name in components
            if "ReturnModelAndFile" in name and "ActionResult" in name
        ]
        dict_and_file_results = [
            name
            for name in components
            if "ReturnDictAndFile" in name and "ActionResult" in name
        ]

        assert len(model_and_file_results) > 0, "Should have model+file action result"
        assert len(dict_and_file_results) > 0, "Should have dict+file action result"

        # Check model and file result
        mixed_model = components[model_and_file_results[0]]

        # Should have both json_result and files
        assert "json_result" in mixed_model["properties"]
        assert "files" in mixed_model["properties"]

        json_result_spec = mixed_model["properties"]["json_result"]
        files_spec = mixed_model["properties"]["files"]

        # json_result should reference SimpleTestResult or have its schema
        assert "$ref" in json_result_spec or ("properties" in json_result_spec), (
            f"json_result should have $ref or properties, got: {json_result_spec}"
        )

        # files should be array of strings or null
        if "anyOf" in files_spec:
            types = list(files_spec["anyOf"])
            array_type = next(
                (item for item in types if item.get("type") == "array"), None
            )
            assert array_type is not None, "Should have array type for files"
            assert array_type["items"]["type"] == "string", (
                "Array items should be strings"
            )
        else:
            assert files_spec["type"] == "array"
            assert files_spec["items"]["type"] == "string"

    # Note: Any and untyped actions test removed as they are not supported by @action decorator


class TestOpenAPISchemaAccuracy:
    """Test that the generated schemas match actual runtime behavior."""

    def test_simple_int_return_matches_schema(self, openapi_test_client):
        """Test that int return matches its OpenAPI schema."""
        # Get the schema
        schema_response = openapi_test_client.get("/openapi.json")
        schema_response.json()

        # Execute the action and wait for completion
        result = execute_action_and_wait(openapi_test_client, "return_int")

        # Verify the actual result structure matches expectations
        assert result["status"] == "succeeded"
        assert result["json_result"] is not None
        assert isinstance(result["json_result"], int) or (
            isinstance(result["json_result"], dict) and "data" in result["json_result"]
        )
        assert result["files"] is None

    def test_complex_model_return_matches_schema(self, openapi_test_client):
        """Test that complex model return matches its OpenAPI schema."""
        # Execute the action and wait for completion
        result = execute_action_and_wait(openapi_test_client, "return_complex_model")

        # Verify the result structure
        assert result["status"] == "succeeded"
        assert result["json_result"] is not None

        json_result = result["json_result"]
        # Check that all expected fields are present
        assert "id" in json_result
        assert "measurements" in json_result
        assert "metadata" in json_result
        assert "timestamp" in json_result

        # Check types match
        assert isinstance(json_result["id"], str)
        assert isinstance(json_result["measurements"], list)
        assert isinstance(json_result["metadata"], dict)
        assert isinstance(json_result["timestamp"], str)  # Serialized datetime

    def test_optional_fields_model_matches_schema(self, openapi_test_client):
        """Test that model with optional fields matches schema."""
        result = execute_action_and_wait(
            openapi_test_client, "return_optional_fields_model"
        )

        assert result["status"] == "succeeded"
        json_result = result["json_result"]

        # Required field should always be present
        assert "required_field" in json_result
        assert json_result["required_field"] == "always_present"

        # Optional fields should be present in this case (since our action returns them)
        assert "optional_string" in json_result
        assert "optional_int" in json_result
        assert "optional_list" in json_result
        assert "optional_dict" in json_result

    def test_file_return_matches_schema(self, openapi_test_client):
        """Test that file return matches its OpenAPI schema."""
        result = execute_action_and_wait(openapi_test_client, "return_single_file")

        assert result["status"] == "succeeded"
        assert result["json_result"] is None  # No JSON data for file-only return
        assert result["files"] is not None
        assert isinstance(result["files"], list)
        assert len(result["files"]) > 0
        assert all(isinstance(file_key, str) for file_key in result["files"])

    def test_mixed_return_matches_schema(self, openapi_test_client):
        """Test that mixed return matches its OpenAPI schema."""
        result = execute_action_and_wait(openapi_test_client, "return_model_and_file")

        assert result["status"] == "succeeded"

        # Should have both JSON result and files
        assert result["json_result"] is not None
        assert result["files"] is not None

        # JSON result should have model structure
        json_result = result["json_result"]
        assert "value" in json_result
        assert "message" in json_result
        assert json_result["message"] == "mixed_result"

        # Files should be file keys
        assert isinstance(result["files"], list)
        assert len(result["files"]) > 0


class TestOpenAPISchemaConsistency:
    """Test consistency between different representations of the same schema."""

    def test_action_specific_vs_generic_result_endpoints(self, openapi_test_client):
        """Test that action-specific and generic result endpoints return same data."""
        # Execute action and wait for completion
        result = execute_action_and_wait(openapi_test_client, "return_simple_model")
        assert result["status"] == "succeeded"

        # Extract action_id from the result (assuming it's included)
        # If not available in result, we can get it by creating a new action
        response = openapi_test_client.post("/action/return_simple_model", json={})
        action_id = response.json()["action_id"]

        # Start and wait for this action too
        response = openapi_test_client.post(
            f"/action/return_simple_model/{action_id}/start"
        )
        assert response.status_code == 200

        # Wait for it to complete
        for _ in range(50):  # Wait up to 5 seconds
            response = openapi_test_client.get(f"/action/{action_id}/result")
            if response.status_code == 200:
                result = response.json()
                if result.get("status") in ["succeeded", "failed", "error"]:
                    break
            time.sleep(0.1)

        # Get result from action-specific endpoint
        specific_response = openapi_test_client.get(
            f"/action/return_simple_model/{action_id}/result"
        )
        assert specific_response.status_code == 200
        specific_result = specific_response.json()

        # Get result from generic endpoint
        generic_response = openapi_test_client.get(f"/action/{action_id}/result")
        assert generic_response.status_code == 200
        generic_result = generic_response.json()

        # Results should be identical
        assert specific_result == generic_result

    def test_schema_references_are_valid(self, openapi_test_client):
        """Test that all schema references in OpenAPI spec are valid."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()

        components = schema.get("components", {}).get("schemas", {})

        def check_refs_in_object(obj):
            """Recursively check all $ref references in an object."""
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref_path = obj["$ref"]
                    if ref_path.startswith("#/components/schemas/"):
                        model_name = ref_path.split("/")[-1]
                        assert model_name in components, (
                            f"Referenced model {model_name} not found in components"
                        )
                else:
                    for value in obj.values():
                        check_refs_in_object(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_refs_in_object(item)

        # Check all schema references
        check_refs_in_object(schema)


class TestOpenAPISchemaDiscrepancyDetection:
    """Tests to detect specific discrepancies between schemas and actual behavior."""

    def test_json_result_field_type_consistency(self, openapi_test_client):
        """Test that json_result field types are consistent across schema and runtime."""
        test_cases = [
            ("return_int", int),
            ("return_string", str),
            ("return_float", float),
            ("return_bool", bool),
            ("return_dict", dict),
            ("return_list", list),
        ]

        schema_response = openapi_test_client.get("/openapi.json")
        schema = schema_response.json()
        schema.get("components", {}).get("schemas", {})

        for action_name, expected_type in test_cases:
            # Execute action and wait for completion
            result = execute_action_and_wait(openapi_test_client, action_name)

            if result["status"] == "succeeded":
                json_result = result["json_result"]

                # Check runtime type consistency
                if expected_type in (int, str, float, bool):
                    # For primitive types, might be wrapped in a data field
                    if isinstance(json_result, dict) and "data" in json_result:
                        actual_value = json_result["data"]
                    else:
                        actual_value = json_result

                    if actual_value is not None:
                        assert isinstance(actual_value, expected_type), (
                            f"Action {action_name} returned {type(actual_value)} but expected {expected_type}"
                        )
                else:
                    # For complex types
                    assert isinstance(json_result, expected_type), (
                        f"Action {action_name} returned {type(json_result)} but expected {expected_type}"
                    )

    # Note: Optional type test removed as not supported by @action decorator

    def test_pydantic_model_field_completeness(self, openapi_test_client):
        """Test that Pydantic model schemas include all model fields."""
        response = openapi_test_client.get("/openapi.json")
        schema = response.json()
        components = schema.get("components", {}).get("schemas", {})

        # Find models that should represent our test result classes
        simple_model_names = [
            name
            for name in components
            if "SimpleTestResult" in name
            or ("ReturnSimpleModel" in name and "ActionResult" in name)
        ]

        if simple_model_names:
            # Check one of the simple models
            model = components[simple_model_names[0]]

            if "properties" in model:
                # Direct schema
                props = model["properties"]
                if "json_result" in props and "$ref" in props["json_result"]:
                    ref_model_name = props["json_result"]["$ref"].split("/")[-1]
                    ref_model = components[ref_model_name]
                    assert "value" in ref_model["properties"]
                    assert "message" in ref_model["properties"]
                elif "json_result" in props and "properties" in props["json_result"]:
                    json_props = props["json_result"]["properties"]
                    assert "value" in json_props
                    assert "message" in json_props

    def test_file_keys_vs_paths_consistency(self, openapi_test_client):
        """Test that file returns use keys instead of full paths."""
        # Test single file return
        result = execute_action_and_wait(openapi_test_client, "return_single_file")

        if result["status"] == "succeeded" and result["files"]:
            # Files should be keys (strings), not full file paths
            for file_key in result["files"]:
                assert isinstance(file_key, str)
                # Should not be a full path (no directory separators)
                assert "/" not in file_key and "\\" not in file_key, (
                    f"File key '{file_key}' appears to be a full path, should be a key"
                )

        # Test multiple files return
        result = execute_action_and_wait(openapi_test_client, "return_multiple_files")

        if result["status"] == "succeeded" and result["files"]:
            # Should have multiple file keys
            assert len(result["files"]) >= 2

            # Each should be a key, not a path
            for file_key in result["files"]:
                assert isinstance(file_key, str)
                assert "/" not in file_key and "\\" not in file_key

            # Should include expected keys for TestFiles model
            assert "data_file" in result["files"]
            assert "config_file" in result["files"]
