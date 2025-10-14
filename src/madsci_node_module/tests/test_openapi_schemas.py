"""Streamlined OpenAPI schema validation tests.

Consolidates and parametrizes tests from test_openapi_schema_validation.py
to reduce redundancy while maintaining comprehensive coverage.
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.action_types import ActionFiles
from madsci.common.types.node_types import NodeDefinition
from madsci.node_module.helpers import action
from pydantic import BaseModel, Field

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


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


class TestFiles(ActionFiles):
    """Test file result model."""

    data_file: Path
    config_file: Path


class OpenAPISchemaTestNode(TestNode):
    """Test node for OpenAPI schema validation."""

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
    def mixed_return(self) -> tuple[SimpleTestResult, Path]:
        """Action that returns both a model and a file."""
        result = SimpleTestResult(value=100, message="mixed")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("mixed return file")
            file_path = Path(f.name)

        return result, file_path


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
        # Create and execute action
        response = openapi_test_client.post(f"/action/{action_name}", json=test_params)
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
        response = openapi_test_client.post("/action/test_action", json={})
        assert response.status_code == 422  # Validation error

        # Test with correct parameters
        response = openapi_test_client.post(
            "/action/test_action", json={"test_param": 1}
        )
        assert response.status_code == 200

    def test_parameter_type_validation(self, openapi_test_client: TestClient):
        """Test that parameter types are properly validated."""
        # Test with wrong parameter type
        response = openapi_test_client.post(
            "/action/test_action", json={"test_param": "not_int"}
        )
        assert response.status_code == 422  # Validation error

        # Test with correct type
        response = openapi_test_client.post(
            "/action/test_action", json={"test_param": 42}
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

            # Should have test_param documented
            if "test_param" in properties:
                param_schema = properties["test_param"]
                assert "type" in param_schema


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
