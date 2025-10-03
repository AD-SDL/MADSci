"""Automated pytest unit tests for the RestNode class."""

import io
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.action_types import (
    ActionFiles,
    ActionRequest,
    ActionResult,
    ActionStatus,
    RestActionResult,
    create_dynamic_model,
    extract_file_parameters,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import NodeDefinition, NodeInfo, NodeStatus
from madsci.node_module.helpers import action
from pydantic import BaseModel, Field
from ulid import ULID

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


@pytest.fixture
def test_node() -> TestNode:
    """Return a RestNode instance for testing."""
    node_definition = NodeDefinition(
        node_name="Test Node 1",
        module_name="test_node",
        description="A test node module for automated testing.",
    )

    return TestNode(
        node_definition=node_definition,
        node_config=TestNodeConfig(
            test_required_param=1,
        ),
    )


@pytest.fixture
def test_client(test_node: TestNode) -> TestClient:
    """Return a TestClient instance for testing."""

    test_node.start_node(testing=True)

    return TestClient(test_node.rest_api)


def test_lifecycle_handlers(test_node: TestNode) -> None:
    """Test the startup_handler and shutdown_handler methods."""

    assert not hasattr(test_node, "startup_has_run")
    assert not hasattr(test_node, "shutdown_has_run")
    assert test_node.test_interface is None

    test_node.start_node(testing=True)

    with TestClient(test_node.rest_api) as client:
        time.sleep(0.5)
        assert test_node.startup_has_run
        assert not hasattr(test_node, "shutdown_has_run")
        assert test_node.test_interface is not None

        response = client.get("/status")
        assert response.status_code == 200

    time.sleep(0.5)

    assert test_node.startup_has_run
    assert test_node.shutdown_has_run
    assert test_node.test_interface is None


def test_lock_and_unlock(test_client: TestClient) -> None:
    """Test the admin commands."""

    with test_client as client:
        time.sleep(0.1)
        response = client.post("/admin/lock")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors
        response = client.get("/status")
        assert response.status_code == 200
        assert NodeStatus.model_validate(response.json()).ready is False
        assert NodeStatus.model_validate(response.json()).locked is True

        response = client.post("/admin/unlock")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors
        response = client.get("/status")
        assert response.status_code == 200
        assert NodeStatus.model_validate(response.json()).ready is True
        assert NodeStatus.model_validate(response.json()).locked is False


def test_pause_and_resume(test_client: TestClient) -> None:
    """Test the pause and resume commands."""
    with test_client as client:
        time.sleep(0.1)
        response = client.post("/admin/pause")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors
        response = client.get("/status")
        assert response.status_code == 200
        assert NodeStatus.model_validate(response.json()).paused is True
        assert NodeStatus.model_validate(response.json()).ready is False

        response = client.post("/admin/resume")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors
        response = client.get("/status")
        assert response.status_code == 200
        assert NodeStatus.model_validate(response.json()).paused is False
        assert NodeStatus.model_validate(response.json()).ready is True


def test_safety_stop_and_reset(test_client: TestClient) -> None:
    """Test the safety_stop and reset commands."""

    with test_client as client:
        time.sleep(0.1)
        response = client.post("/admin/safety_stop")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors
        response = client.get("/status")
        assert response.status_code == 200
        assert NodeStatus.model_validate(response.json()).stopped is True

        response = client.post("/admin/reset")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors


def test_shutdown(test_node: TestNode) -> None:
    """Test the shutdown command."""
    test_node.start_node(testing=True)

    with TestClient(test_node.rest_api) as client:
        time.sleep(0.5)
        response = client.post("/admin/shutdown")
        assert response.status_code == 200
        validated_response = AdminCommandResponse.model_validate(response.json())
        assert validated_response.success is True
        assert not validated_response.errors
        assert test_node.shutdown_has_run


def test_create_action(test_client: TestClient) -> None:
    """Test creating a new action."""
    with test_client as client:
        time.sleep(0.5)

        # Create action
        response = client.post("/action/test_action", json={"test_param": 1})
        assert response.status_code == 200
        result = response.json()
        assert "action_id" in result
        action_id = result["action_id"]
        assert ULID.from_str(action_id)  # Validate it's a valid ULID


def test_start_action(test_client: TestClient) -> None:
    """Test starting an action."""
    with test_client as client:
        time.sleep(0.5)

        # Create action
        response = client.post("/action/test_action", json={"test_param": 1})
        assert response.status_code == 200
        action_id = response.json()["action_id"]

        # Start action
        response = client.post(f"/action/test_action/{action_id}/start")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.action_id == action_id
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]


def test_run_action_fail(test_client: TestClient) -> None:
    """Test an action that is designed to fail."""
    with test_client as client:
        time.sleep(0.5)

        # Create and start failing action
        response = client.post("/action/test_fail", json={"test_param": 1})
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_fail/{action_id}/start")
        assert response.status_code == 200

        # Check that it fails
        time.sleep(0.1)
        response = client.get(f"/action/test_fail/{action_id}/result")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status == ActionStatus.FAILED
        assert "returned 'False'" in result.errors[0].message


def test_get_status(test_client: TestClient) -> None:
    """Test the get_status command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.get("/status")
        assert response.status_code == 200
        assert NodeStatus.model_validate(response.json()).ready is True


def test_get_state(test_client: TestClient) -> None:
    """Test the get_state command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.get("/state")
        assert response.status_code == 200
        assert response.json() == {"test_status_code": 0}


def test_get_info(test_client: TestClient) -> None:
    """Test the get_info command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.get("/info")
        assert response.status_code == 200
        node_info = NodeInfo.model_validate(response.json())
        assert node_info.node_name == "Test Node 1"
        assert node_info.module_name == "test_node"
        assert len(node_info.actions) == 12
        assert node_info.actions["test_action"].description == "A test action."
        assert node_info.actions["test_action"].args["test_param"].required
        assert (
            node_info.actions["test_action"].args["test_param"].argument_type == "int"
        )
        assert node_info.actions["test_fail"].description == "A test action that fails."
        assert node_info.actions["test_fail"].args["test_param"].required
        assert node_info.actions["test_fail"].args["test_param"].argument_type == "int"
        assert (
            node_info.actions["test_optional_param_action"].args["test_param"].required
        )
        assert (
            node_info.actions["test_optional_param_action"]
            .args["test_param"]
            .argument_type
            == "int"
        )
        assert (
            not node_info.actions["test_optional_param_action"]
            .args["optional_param"]
            .required
        )
        assert (
            node_info.actions["test_optional_param_action"]
            .args["optional_param"]
            .argument_type
            == "str"
        )
        assert (
            node_info.actions["test_optional_param_action"]
            .args["optional_param"]
            .default
            == ""
        )
        assert (
            not node_info.actions["test_annotation_action"].args["test_param"].required
        )
        assert (
            node_info.actions["test_annotation_action"].args["test_param"].argument_type
            == "int"
        )
        assert (
            node_info.actions["test_annotation_action"].args["test_param"].description
            == "Description"
        )
        assert (
            not node_info.actions["test_annotation_action"]
            .args["test_param_2"]
            .required
        )
        assert (
            node_info.actions["test_annotation_action"]
            .args["test_param_2"]
            .argument_type
            == "int"
        )
        assert (
            node_info.actions["test_annotation_action"].args["test_param_2"].description
            == "Description 2"
        )
        assert (
            not node_info.actions["test_annotation_action"]
            .args["test_param_3"]
            .required
        )
        assert (
            node_info.actions["test_annotation_action"]
            .args["test_param_3"]
            .argument_type
            == "int"
        )
        assert (
            node_info.actions["test_annotation_action"].args["test_param_3"].description
            == "Description 3"
        )


def test_get_action_result_by_name(test_client: TestClient) -> None:
    """Test getting action result by action name."""
    with test_client as client:
        time.sleep(0.5)

        # Create and start action
        response = client.post("/action/test_action", json={"test_param": 1})
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_action/{action_id}/start")
        assert response.status_code == 200

        # Get action result
        time.sleep(0.1)  # Give action time to complete
        response = client.get(f"/action/test_action/{action_id}/result")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.action_id == action_id
        assert result.status == ActionStatus.SUCCEEDED


def test_get_action_result(test_client: TestClient) -> None:
    """Test getting action result."""
    with test_client as client:
        time.sleep(0.5)

        # Create and start action
        response = client.post("/action/test_action", json={"test_param": 1})
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_action/{action_id}/start")
        assert response.status_code == 200

        # Get action result
        time.sleep(0.1)  # Give action time to complete
        response = client.get(f"/action/test_action/{action_id}/result")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.action_id == action_id
        assert result.status == ActionStatus.SUCCEEDED


def test_get_nonexistent_action(test_client: TestClient) -> None:
    """Test getting status of a nonexistent action."""
    with test_client as client:
        time.sleep(0.5)

        # Try to get status of nonexistent action
        invalid_id = str(ULID())
        response = client.get(f"/action/test_action/{invalid_id}/result")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status == ActionStatus.UNKNOWN


def test_get_action_history(test_client: TestClient) -> None:
    """Test the get_action_history command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.get("/action")
        assert response.status_code == 200
        action_history = response.json()
        existing_history_length = len(action_history)

        # Create and start an action
        response = client.post("/action/test_action", json={"test_param": 1})
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_action/{action_id}/start")
        assert response.status_code == 200

        # Wait for completion
        time.sleep(0.1)

        # Create and start another action
        response = client.post("/action/test_action", json={"test_param": 1})
        action_id2 = response.json()["action_id"]

        response = client.post(f"/action/test_action/{action_id2}/start")
        assert response.status_code == 200

        # Wait for completion
        time.sleep(0.1)

        response = client.get("/action")
        assert response.status_code == 200
        action_history = response.json()
        assert len(action_history) - existing_history_length == 2
        assert action_id in action_history
        assert action_id2 in action_history
        assert len(action_history[action_id]) == 3
        assert (
            ActionResult.model_validate(action_history[action_id][0]).status
            == ActionStatus.NOT_STARTED
        )
        assert (
            ActionResult.model_validate(action_history[action_id][1]).status
            == ActionStatus.RUNNING
        )
        assert (
            ActionResult.model_validate(action_history[action_id][2]).status
            == ActionStatus.SUCCEEDED
        )

        response = client.get("/action", params={"action_id": action_id2})
        assert response.status_code == 200
        action_history = response.json()
        assert len(action_history) == 1
        assert action_id not in action_history
        assert action_id2 in action_history
        assert len(action_history[action_id2]) == 3
        assert (
            ActionResult.model_validate(action_history[action_id2][0]).status
            == ActionStatus.NOT_STARTED
        )
        assert (
            ActionResult.model_validate(action_history[action_id2][1]).status
            == ActionStatus.RUNNING
        )
        assert (
            ActionResult.model_validate(action_history[action_id2][2]).status
            == ActionStatus.SUCCEEDED
        )


def test_get_log(test_client: TestClient) -> None:
    """Test the get_log command."""
    with test_client as client:
        time.sleep(0.5)

        # Create and start an action to generate log entries
        response = client.post("/action/test_action", json={"test_param": 1})
        assert response.status_code == 200
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_action/{action_id}/start")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]

        response = client.get("/log")
        assert response.status_code == 200
        assert len(response.json()) > 0
        for _, entry in response.json().items():
            Event.model_validate(entry)


def test_optional_param_action(test_client: TestClient) -> None:
    """Test an action with optional parameters."""
    with test_client as client:
        time.sleep(0.5)

        # Test with optional parameter
        response = client.post(
            "/action/test_optional_param_action",
            json={"test_param": 1, "optional_param": "test_value"},
        )
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_optional_param_action/{action_id}/start")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]

        # Test without optional parameter
        response = client.post(
            "/action/test_optional_param_action", json={"test_param": 1}
        )
        action_id = response.json()["action_id"]

        response = client.post(f"/action/test_optional_param_action/{action_id}/start")
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]


def test_action_with_missing_params(test_client: TestClient) -> None:
    """Test creating an action with missing required parameters."""
    with test_client as client:
        time.sleep(0.5)

        # Create action without required parameter - should fail validation
        response = client.post(
            "/action/test_action",
            json={},  # Missing test_param
        )
        # FastAPI validation should reject this with 422
        assert response.status_code == 422
        validation_error = response.json()
        assert "detail" in validation_error
        # Verify the validation error mentions the missing field
        error_details = validation_error["detail"]
        assert any("test_param" in str(error).lower() for error in error_details)


def test_invalid_action_id(test_client: TestClient) -> None:
    """Test starting an action with an invalid action_id."""
    with test_client as client:
        time.sleep(0.5)

        # Try to start action with invalid ID
        invalid_id = str(ULID())
        response = client.post(f"/action/test_action/{invalid_id}/start")
        assert response.status_code == 200  # Should return 200 with failed status
        result = ActionResult.model_validate(response.json())
        assert result.status == ActionStatus.FAILED
        assert "not found" in result.errors[0].message


def test_file_parameter_extraction(test_node: TestNode) -> None:
    """Test that file parameters are correctly extracted from action functions."""
    # Test the file_action method which has file parameters
    file_action_func = test_node.action_handlers.get("file_action")
    assert file_action_func is not None

    file_params = extract_file_parameters(file_action_func)

    # The file_action should have file parameters
    assert "config_file" in file_params
    assert file_params["config_file"]["required"] is True
    assert (
        "config_file: A required configuration file"
        in file_params["config_file"]["description"]
    )

    # Test optional file parameter
    assert "optional_file" in file_params
    assert file_params["optional_file"]["required"] is False
    assert (
        "optional_file: An optional file parameter"
        in file_params["optional_file"]["description"]
    )


def test_openapi_file_documentation(test_client: TestClient) -> None:
    """Test that file upload endpoints include proper documentation in OpenAPI schema."""
    with test_client as client:
        # Get the OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_schema = response.json()

        # Check for specific file parameter endpoints
        config_file_path = "/action/file_action/{action_id}/upload/config_file"
        optional_file_path = "/action/file_action/{action_id}/upload/optional_file"

        assert config_file_path in openapi_schema["paths"]
        assert optional_file_path in openapi_schema["paths"]

        # Test required file endpoint
        config_endpoint = openapi_schema["paths"][config_file_path]["post"]
        assert "summary" in config_endpoint
        assert "config_file" in config_endpoint["summary"]
        assert "description" in config_endpoint
        assert "Required" in config_endpoint["description"]
        assert "file_action" in config_endpoint["tags"]

        # Test optional file endpoint
        optional_endpoint = openapi_schema["paths"][optional_file_path]["post"]
        assert "summary" in optional_endpoint
        assert "optional_file" in optional_endpoint["summary"]
        assert "description" in optional_endpoint
        assert "Optional" in optional_endpoint["description"]
        assert "file_action" in optional_endpoint["tags"]

        # Verify that old generic endpoint patterns no longer exist
        old_generic_path = "/action/file_action/{action_id}/files/{file_arg}"
        old_upload_pattern = "/action/file_action/{action_id}/upload_config_file"
        assert old_generic_path not in openapi_schema["paths"]
        assert old_upload_pattern not in openapi_schema["paths"]


def test_specific_file_upload_endpoints(test_client: TestClient) -> None:
    """Test that specific file upload endpoints work correctly."""
    with test_client as client:
        # Create an action first
        response = client.post("/action/file_action", json={})
        assert response.status_code == 200
        action_id = response.json()["action_id"]

        # Test uploading to specific config_file endpoint
        config_content = b"config content"
        response = client.post(
            f"/action/file_action/{action_id}/upload/config_file",
            files={"file": ("config.txt", io.BytesIO(config_content))},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "uploaded"
        assert result["file_arg"] == "config_file"

        # Test uploading to specific optional_file endpoint
        optional_content = b"optional content"
        response = client.post(
            f"/action/file_action/{action_id}/upload/optional_file",
            files={"file": ("optional.txt", io.BytesIO(optional_content))},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "uploaded"
        assert result["file_arg"] == "optional_file"


def test_file_download_routes(test_client: TestClient) -> None:
    """Test that single ZIP download routes are created for actions that return files."""
    with test_client as client:
        # Get the OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_schema = response.json()

        # Check for single file result action - should have only ZIP download endpoint
        single_file_zip_path = "/action/file_result_action/{action_id}/download"
        assert single_file_zip_path in openapi_schema["paths"]

        single_file_endpoint = openapi_schema["paths"][single_file_zip_path]["get"]
        assert "summary" in single_file_endpoint
        assert "download" in single_file_endpoint["summary"].lower()
        assert "file_result_action" in single_file_endpoint["tags"]
        # Should mention it's a ZIP archive
        assert "ZIP archive" in single_file_endpoint["description"]

        # Check for multiple file result action - should have only ZIP download endpoint
        multi_files_zip_path = (
            "/action/multiple_file_result_action/{action_id}/download"
        )
        assert multi_files_zip_path in openapi_schema["paths"]

        multi_files_endpoint = openapi_schema["paths"][multi_files_zip_path]["get"]
        assert "multiple_file_result_action" in multi_files_endpoint["tags"]
        # Should list expected files in description
        assert "output_file" in multi_files_endpoint["description"]
        assert "log_file" in multi_files_endpoint["description"]

        # Verify individual file endpoints no longer exist
        individual_file_paths = [
            path
            for path in openapi_schema["paths"]
            if "download/" in path
            and path.endswith(("/output_file", "/log_file", "/file"))
        ]
        assert len(individual_file_paths) == 0

        # Verify that ALL actions now have download endpoints (defensive programming)
        test_action_download_path = "/action/test_action/{action_id}/download"
        assert test_action_download_path in openapi_schema["paths"]

        # Verify the endpoint for actions without expected files explains this
        test_action_endpoint = openapi_schema["paths"][test_action_download_path]["get"]
        assert "not expected to return files" in test_action_endpoint["description"]


def test_custom_pydantic_result_processing(test_node: TestNode) -> None:
    """Test that custom pydantic models are properly processed and serialized."""
    # Start the node for testing
    test_node.start_node(testing=True)

    # Use test client to properly wait for node to be ready
    with TestClient(test_node.rest_api):
        time.sleep(0.5)  # Give the node time to initialize

        # Create an action request for the custom pydantic result action
        action_request = ActionRequest(
            action_name="custom_pydantic_result_action",
            args={"test_id": "custom_test_123"},
        )

        # Run the action
        result = test_node.run_action(action_request)

        # Action might be running asynchronously, so wait for completion
        action_id = result.action_id
        max_wait_seconds = 5.0
        wait_time = 0.0
        while result.status == ActionStatus.RUNNING and wait_time < max_wait_seconds:
            time.sleep(0.1)
            wait_time += 0.1
            # Get the latest action history
            history = test_node.get_action_history(action_id)
            if history and action_id in history:
                latest_result = history[action_id][-1]  # Get the most recent result
                result = latest_result

        # Check that the result is successful
        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_result is not None

        # Check that the custom pydantic model was properly serialized to JSON
        json_result = result.json_result
        assert isinstance(json_result, dict)
        assert json_result["test_id"] == "custom_test_123"
        assert json_result["value"] == 42.5
        assert json_result["status"] == "completed"
        assert json_result["metadata"]["instrument"] == "test_instrument"
        assert json_result["metadata"]["operator"] == "test_user"


def test_mixed_pydantic_and_file_result_processing(test_node: TestNode) -> None:
    """Test that mixed returns (pydantic model + file) are properly processed."""
    # Start the node for testing
    test_node.start_node(testing=True)

    # Use test client to properly wait for node to be ready
    with TestClient(test_node.rest_api):
        time.sleep(0.5)  # Give the node time to initialize

        # Create an action request for the mixed result action
        action_request = ActionRequest(
            action_name="mixed_pydantic_and_file_action",
            args={"test_id": "mixed_test_456"},
        )

        # Run the action
        result = test_node.run_action(action_request)

        # Action might be running asynchronously, so wait for completion
        action_id = result.action_id
        max_wait_seconds = 5.0
        wait_time = 0.0
        while result.status == ActionStatus.RUNNING and wait_time < max_wait_seconds:
            time.sleep(0.1)
            wait_time += 0.1
            # Get the latest action history
            history = test_node.get_action_history(action_id)
            if history and action_id in history:
                latest_result = history[action_id][-1]  # Get the most recent result
                result = latest_result

        # Check that the result is successful
        assert result.status == ActionStatus.SUCCEEDED

        # Check that the custom pydantic model was properly serialized to JSON
        assert result.json_result is not None
        json_result = result.json_result
        assert isinstance(json_result, dict)
        assert json_result["test_id"] == "mixed_test_456"
        assert json_result["value"] == 123.45
        assert json_result["status"] == "completed"
        assert json_result["metadata"]["type"] == "mixed_return"
        assert json_result["metadata"]["file_created"] is True

        # Check that the file was also processed
        assert result.files is not None
        # The file should be a Path object
        assert isinstance(result.files, Path)
        assert result.files.suffix == ".json"
        # Verify the file exists and contains expected content
        assert result.files.exists()
        content = result.files.read_text()
        assert "mixed_test_456" in content
        assert "raw_data" in content


# Additional tests for enhanced OpenAPI documentation and result handling features


class TestActionFiles(ActionFiles):
    """Test ActionFiles subclass for testing labeled file returns."""

    log_file: Path
    data_file: Path


class TestResultModel(BaseModel):
    """Test Pydantic model for testing custom return types."""

    sample_id: str = Field(description="Sample identifier")
    value: float = Field(description="Measured value")
    status: str = Field(description="Processing status")


class EnhancedTestNode(TestNode):
    """Extended test node for validating enhanced REST endpoint generation."""

    @action
    def return_int(self) -> int:
        """Returns a simple integer."""
        return 42

    @action
    def return_dict(self) -> dict:
        """Returns a dictionary."""
        return {"key": "value", "number": 123}

    @action
    def return_file(self) -> Path:
        """Returns a single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            return Path(f.name)

    @action
    def return_labeled_files(self) -> TestActionFiles:
        """Returns multiple labeled files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("log content")
            log_file = Path(f.name)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("data content")
            data_file = Path(f.name)
        return TestActionFiles(log_file=log_file, data_file=data_file)

    @action
    def return_custom_model(self) -> TestResultModel:
        """Returns a custom Pydantic model."""
        return TestResultModel(sample_id="SAMPLE_001", value=15.75, status="completed")

    @action
    def return_mixed(self) -> tuple[dict, Path]:
        """Returns both JSON data and a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("mixed content")
            return {"result": "success"}, Path(f.name)

    @action
    def take_file_input(self, input_file: Path, param: str = "default") -> dict:
        """Action that takes a file input."""
        return {"processed": param, "file_size": input_file.stat().st_size}


@pytest.fixture
def enhanced_test_node():
    """Create an enhanced test node instance."""
    node_definition = NodeDefinition(
        node_name="Enhanced Test Node",
        module_name="enhanced_test_node",
        description="An enhanced test node module for automated testing.",
    )

    node = EnhancedTestNode(
        node_definition=node_definition,
        node_config=TestNodeConfig(
            test_required_param=1,
        ),
    )
    node.start_node(testing=True)
    return node


@pytest.fixture
def enhanced_client(enhanced_test_node):
    """Create a test client for the enhanced node."""
    with TestClient(enhanced_test_node.rest_api) as client:
        time.sleep(0.5)  # Wait for startup to complete

        # Verify startup completed
        assert enhanced_test_node.startup_has_run
        yield client


class TestActionDefinitionGeneration:
    """Test that actions generate correct ActionDefinitions with proper result definitions."""

    def test_action_result_definitions_generated(self, enhanced_test_node):
        """Test that @action decorator generates correct result definitions."""
        # Check that result definitions are attached to functions
        return_int_func = enhanced_test_node.action_handlers["return_int"]
        assert hasattr(return_int_func, "__madsci_action_result_definitions__")

        result_defs = return_int_func.__madsci_action_result_definitions__
        assert len(result_defs) == 1
        assert result_defs[0].result_type == "json"
        assert result_defs[0].result_label == "json_result"

    def test_file_result_definitions(self, enhanced_test_node):
        """Test file return types generate correct file result definitions."""
        return_file_func = enhanced_test_node.action_handlers["return_file"]
        result_defs = return_file_func.__madsci_action_result_definitions__

        assert len(result_defs) == 1
        assert result_defs[0].result_type == "file"
        assert result_defs[0].result_label == "file"

    def test_labeled_files_result_definitions(self, enhanced_test_node):
        """Test ActionFiles subclass generates correct labeled file definitions."""
        func = enhanced_test_node.action_handlers["return_labeled_files"]
        result_defs = func.__madsci_action_result_definitions__

        assert len(result_defs) == 2
        file_labels = [rd.result_label for rd in result_defs]
        assert "log_file" in file_labels
        assert "data_file" in file_labels
        assert all(rd.result_type == "file" for rd in result_defs)

    def test_custom_model_result_definitions(self, enhanced_test_node):
        """Test custom Pydantic model generates correct JSON result definition."""
        func = enhanced_test_node.action_handlers["return_custom_model"]
        result_defs = func.__madsci_action_result_definitions__

        assert len(result_defs) == 1
        assert result_defs[0].result_type == "json"
        assert result_defs[0].json_schema is not None
        # Should include the TestResultModel schema
        schema = result_defs[0].json_schema
        assert "properties" in schema
        assert "sample_id" in schema["properties"]

    def test_mixed_return_result_definitions(self, enhanced_test_node):
        """Test tuple return generates multiple result definitions."""
        func = enhanced_test_node.action_handlers["return_mixed"]
        result_defs = func.__madsci_action_result_definitions__

        assert len(result_defs) == 2
        result_types = [rd.result_type for rd in result_defs]
        assert "json" in result_types
        assert "file" in result_types


class TestEnhancedOpenAPIDocumentationGeneration:
    """Test that OpenAPI/Swagger documentation is correctly generated."""

    def test_openapi_schema_generated(self, enhanced_client):
        """Test that OpenAPI schema is available."""
        response = enhanced_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_action_specific_response_models(self, enhanced_client):
        """Test that each action has its own response model in OpenAPI."""
        response = enhanced_client.get("/openapi.json")
        schema = response.json()

        # Check that action-specific result endpoints exist
        paths = schema["paths"]
        assert "/action/return_int/{action_id}/result" in paths
        assert "/action/return_custom_model/{action_id}/result" in paths

        # Check response models are action-specific, not generic ActionResult
        int_result_path = paths["/action/return_int/{action_id}/result"]["get"]
        responses = int_result_path["responses"]["200"]
        content_schema = responses["content"]["application/json"]["schema"]

        # Should reference a specific model, not generic ActionResult
        if "$ref" in content_schema:
            model_name = content_schema["$ref"].split("/")[-1]
            assert "ReturnInt" in model_name or "return_int" in model_name.lower()

    def test_file_download_documentation(self, enhanced_client):
        """Test that ZIP file download endpoints are properly documented."""
        response = enhanced_client.get("/openapi.json")
        schema = response.json()

        paths = schema["paths"]
        # Should have ZIP download endpoint for single file action
        file_download_path = "/action/return_file/{action_id}/download"
        assert file_download_path in paths

        endpoint = paths[file_download_path]["get"]
        assert "responses" in endpoint
        # Should have proper ZIP response documentation
        assert "200" in endpoint["responses"]
        response_200 = endpoint["responses"]["200"]
        assert "content" in response_200
        # Should specify ZIP content type
        assert "application/zip" in response_200["content"]

    def test_labeled_file_download_endpoints(self, enhanced_client):
        """Test that labeled files only get a single ZIP download endpoint."""
        response = enhanced_client.get("/openapi.json")
        schema = response.json()

        paths = schema["paths"]
        # Should NOT have individual endpoints for each labeled file
        assert "/action/return_labeled_files/{action_id}/download/log_file" not in paths
        assert (
            "/action/return_labeled_files/{action_id}/download/data_file" not in paths
        )

        # Should only have single ZIP download endpoint
        zip_endpoint_path = "/action/return_labeled_files/{action_id}/download"
        assert zip_endpoint_path in paths

        # Should list expected files in the description
        zip_endpoint = paths[zip_endpoint_path]["get"]
        assert "log_file" in zip_endpoint["description"]
        assert "data_file" in zip_endpoint["description"]

    def test_file_upload_documentation(self, enhanced_client):
        """Test that file upload endpoints are properly documented."""
        response = enhanced_client.get("/openapi.json")
        schema = response.json()

        paths = schema["paths"]
        # Should have file upload endpoint
        upload_path = "/action/take_file_input/{action_id}/upload/input_file"
        assert upload_path in paths

        endpoint = paths[upload_path]["post"]
        # Should have proper file upload documentation
        assert "requestBody" in endpoint
        request_body = endpoint["requestBody"]
        assert "content" in request_body
        assert "multipart/form-data" in request_body["content"]

    def test_request_model_documentation(self, enhanced_client):
        """Test that request models are properly documented."""
        response = enhanced_client.get("/openapi.json")
        schema = response.json()

        # Should have components section with request models
        assert "components" in schema
        assert "schemas" in schema["components"]

        schemas = schema["components"]["schemas"]
        # Should have action-specific request models
        request_model_names = [name for name in schemas if "Request" in name]
        assert len(request_model_names) > 0

        # Check a specific request model
        take_file_input_models = [
            name
            for name in request_model_names
            if "take_file_input" in name.lower() or "TakeFileInput" in name
        ]
        assert len(take_file_input_models) > 0


class TestEnhancedEndpointBehavior:
    """Test the actual behavior of generated endpoints."""

    def test_simple_action_execution_flow(self, enhanced_client):
        """Test the full flow of executing a simple action."""
        # 1. Create action
        response = enhanced_client.post("/action/return_int", json={})
        assert response.status_code == 200
        action_data = response.json()
        action_id = action_data["action_id"]
        assert action_id

        # 2. Start action (no files to upload)
        response = enhanced_client.post(f"/action/return_int/{action_id}/start")
        assert response.status_code == 200

        # Wait for action to complete
        for _ in range(50):  # Wait up to 5 seconds
            response = enhanced_client.get(f"/action/{action_id}/result")
            if response.status_code == 200:
                result = response.json()
                if result.get("status") in ["succeeded", "failed", "error"]:
                    break
            time.sleep(0.1)

        assert result["status"] == "succeeded"
        assert result["json_result"] == 42

    def test_file_action_execution_flow(self, enhanced_client, tmp_path):
        """Test executing an action that takes a file input."""
        # 1. Create action
        response = enhanced_client.post(
            "/action/take_file_input", json={"param": "test_value"}
        )
        assert response.status_code == 200
        action_data = response.json()
        action_id = action_data["action_id"]

        # 2. Upload file
        test_file = tmp_path / "input.txt"
        test_file.write_text("test file content")

        with test_file.open("rb") as f:
            response = enhanced_client.post(
                f"/action/take_file_input/{action_id}/upload/input_file",
                files={"file": ("input.txt", f, "text/plain")},
            )
        assert response.status_code == 200

        # 3. Start action
        response = enhanced_client.post(f"/action/take_file_input/{action_id}/start")
        assert response.status_code == 200

        # Wait for action to complete
        for _ in range(50):  # Wait up to 5 seconds
            response = enhanced_client.get(f"/action/{action_id}/result")
            if response.status_code == 200:
                result = response.json()
                if result.get("status") in ["succeeded", "failed", "error"]:
                    break
            time.sleep(0.1)

        assert result["status"] == "succeeded"
        assert result["json_result"]["processed"] == "test_value"
        assert result["json_result"]["file_size"] > 0

    def test_file_download_endpoint(self, enhanced_client):
        """Test downloading files from completed actions as ZIP."""
        with enhanced_client as client:
            # Wait for node to be ready
            time.sleep(0.5)

            # Execute action that returns a file
            response = client.post("/action/return_file", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/return_file/{action_id}/start")
            assert response.status_code == 200

            # Download the file as ZIP
            response = client.get(f"/action/return_file/{action_id}/download")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/zip"

            # Verify ZIP contains the expected file content
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                file_list = zip_file.namelist()
                assert len(file_list) >= 1
                # Read the first file in the ZIP
                with zip_file.open(file_list[0]) as f:
                    content = f.read()
                    assert b"test content" in content

    def test_labeled_file_downloads(self, enhanced_client):
        """Test downloading labeled files as ZIP."""
        with enhanced_client as client:
            # Wait for node to be ready
            time.sleep(0.5)

            # Execute action that returns labeled files
            response = client.post("/action/return_labeled_files", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/return_labeled_files/{action_id}/start")
            assert response.status_code == 200

            # Individual file endpoints should not exist
            response = client.get(
                f"/action/return_labeled_files/{action_id}/download/log_file"
            )
            assert response.status_code == 404

            response = client.get(
                f"/action/return_labeled_files/{action_id}/download/data_file"
            )
            assert response.status_code == 404

            # Download ZIP with all files
            response = client.get(f"/action/return_labeled_files/{action_id}/download")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/zip"

            # Verify ZIP contains the expected labeled files
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                file_list = zip_file.namelist()
                assert len(file_list) == 2

                # Files should be named with their labels
                file_contents = {}
                for filename in file_list:
                    with zip_file.open(filename) as f:
                        file_contents[filename] = f.read()

                # Check that we have both expected files with correct content
                log_file_found = any(
                    b"log content" in content for content in file_contents.values()
                )
                data_file_found = any(
                    b"data content" in content for content in file_contents.values()
                )
                assert log_file_found, "Log file content not found in ZIP"
                assert data_file_found, "Data file content not found in ZIP"

    def test_download_endpoint_for_non_file_actions(self, enhanced_client):
        """Test that actions without declared file results still have download endpoints."""
        with enhanced_client as client:
            # Wait for node to be ready
            time.sleep(0.5)

            # Execute action that normally doesn't return files
            response = client.post("/action/return_int", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/return_int/{action_id}/start")
            assert response.status_code == 200

            # Download endpoint should exist but return 404 since no files
            response = client.get(f"/action/return_int/{action_id}/download")
            assert response.status_code == 404  # No files to download


class TestEnhancedActionResultTypeMapping:
    """Test that action return types correctly map to API responses."""

    def test_int_return_maps_to_json_result(self, enhanced_client):
        """Test that int return becomes json_result in API response."""
        response = enhanced_client.post("/action/return_int", json={})
        action_id = response.json()["action_id"]

        response = enhanced_client.post(f"/action/return_int/{action_id}/start")
        assert response.status_code == 200

        # Wait for action to complete
        for _ in range(50):  # Wait up to 5 seconds
            response = enhanced_client.get(f"/action/{action_id}/result")
            if response.status_code == 200:
                result = response.json()
                if result.get("status") in ["succeeded", "failed", "error"]:
                    break
            time.sleep(0.1)

        assert result["status"] == "succeeded"
        assert "json_result" in result
        assert result["json_result"] == 42
        assert result["files"] is None

    def test_custom_model_return_maps_to_json_result(self, enhanced_client):
        """Test that custom Pydantic model becomes structured json_result."""
        response = enhanced_client.post("/action/return_custom_model", json={})
        action_id = response.json()["action_id"]

        response = enhanced_client.post(
            f"/action/return_custom_model/{action_id}/start"
        )
        result = response.json()

        assert "json_result" in result
        json_result = result["json_result"]
        assert json_result["sample_id"] == "SAMPLE_001"
        assert json_result["value"] == 15.75
        assert json_result["status"] == "completed"

    def test_file_return_maps_to_files_field(self, enhanced_client):
        """Test that Path return becomes files field in API response."""
        response = enhanced_client.post("/action/return_file", json={})
        action_id = response.json()["action_id"]

        response = enhanced_client.post(f"/action/return_file/{action_id}/start")
        result = response.json()

        assert "files" in result
        assert result["files"] is not None
        assert result["json_result"] is None

    def test_labeled_files_return_structure(self, enhanced_client):
        """Test that ActionFiles subclass creates proper files structure."""
        with enhanced_client as client:
            time.sleep(0.5)  # Wait for node to be ready

            response = client.post("/action/return_labeled_files", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/return_labeled_files/{action_id}/start")
            result = response.json()

            assert "files" in result
            files = result["files"]
            # Files are now returned as file keys (list) rather than dict
            assert isinstance(files, list)
            assert "log_file" in files
            assert "data_file" in files

    def test_mixed_return_maps_to_both_fields(self, enhanced_client):
        """Test that tuple return populates both json_result and files."""
        response = enhanced_client.post("/action/return_mixed", json={})
        action_id = response.json()["action_id"]

        response = enhanced_client.post(f"/action/return_mixed/{action_id}/start")
        assert response.status_code == 200

        # Wait for action to complete
        for _ in range(50):  # Wait up to 5 seconds
            response = enhanced_client.get(f"/action/{action_id}/result")
            if response.status_code == 200:
                result = response.json()
                if result.get("status") in ["succeeded", "failed", "error"]:
                    break
            time.sleep(0.1)

        assert result["status"] == "succeeded"
        assert "json_result" in result
        assert "files" in result
        assert result["json_result"]["result"] == "success"
        assert result["files"] is not None


class TestEnhancedBackwardCompatibility:
    """Test that changes maintain backward compatibility."""

    def test_generic_action_endpoints_still_work(self, enhanced_client):
        """Test that generic /action/{action_id}/result endpoints still work."""
        response = enhanced_client.post("/action/return_int", json={})
        action_id = response.json()["action_id"]

        response = enhanced_client.post(f"/action/return_int/{action_id}/start")
        assert response.status_code == 200

        # Wait for action to complete
        for _ in range(50):  # Wait up to 5 seconds
            response = enhanced_client.get(f"/action/{action_id}/result")
            if response.status_code == 200:
                result = response.json()
                if result.get("status") in ["succeeded", "failed", "error"]:
                    break
            time.sleep(0.1)

        assert result["status"] == "succeeded"
        assert result["json_result"] == 42

    def test_generic_status_endpoints_work(self, enhanced_client):
        """Test that generic status endpoints continue to work."""
        response = enhanced_client.post("/action/return_int", json={})
        action_id = response.json()["action_id"]

        # Generic status endpoint
        response = enhanced_client.get(f"/action/{action_id}/status")
        assert response.status_code == 200
        status = response.json()
        assert status in ["not_started", "running", "succeeded", "failed", "unknown"]


# Test models to match the proposal example
class ReadSensorValue(BaseModel):
    """Result of reading a sensor, returned by the python action function"""

    value: int
    """Value from the sensor"""
    timestamp: datetime
    """Timestamp for when the sensor read occurred"""


class TestNewActionResults(BaseModel):
    """Test custom pydantic model for new action results"""

    sensor_id: str = Field(description="Sensor identifier")
    temperature: float = Field(description="Temperature measurement")
    humidity: float = Field(description="Humidity measurement")
    status: str = Field(description="Sensor status")


class TestAdvancedFileParameterSupport:
    """Test support for advanced file parameter types: list[Path], Optional[Path], Optional[list[Path]]."""

    def test_list_file_parameter_extraction(self, test_node: TestNode) -> None:
        """Test that list[Path] parameters are correctly extracted."""
        list_file_action_func = test_node.action_handlers.get("list_file_action")
        assert list_file_action_func is not None

        file_params = extract_file_parameters(list_file_action_func)

        # Should detect the list[Path] parameter
        assert "files" in file_params
        assert file_params["files"]["required"] is True
        assert "files: A list of input files" in file_params["files"]["description"]

    def test_optional_file_parameter_extraction(self, test_node: TestNode) -> None:
        """Test that Optional[Path] parameters are correctly extracted."""
        optional_file_action_func = test_node.action_handlers.get(
            "optional_file_action"
        )
        assert optional_file_action_func is not None

        file_params = extract_file_parameters(optional_file_action_func)

        # Should detect the Optional[Path] parameter
        assert "optional_file" in file_params
        assert file_params["optional_file"]["required"] is False
        assert (
            "optional_file: An optional file parameter"
            in file_params["optional_file"]["description"]
        )

    def test_optional_list_file_parameter_extraction(self, test_node: TestNode) -> None:
        """Test that Optional[list[Path]] parameters are correctly extracted."""
        optional_list_action_func = test_node.action_handlers.get(
            "optional_list_file_action"
        )
        assert optional_list_action_func is not None

        file_params = extract_file_parameters(optional_list_action_func)

        # Should detect the Optional[list[Path]] parameter
        assert "optional_files" in file_params
        assert file_params["optional_files"]["required"] is False
        assert (
            "optional_files: An optional list of files"
            in file_params["optional_files"]["description"]
        )

    def test_list_file_upload_endpoints_generated(
        self, test_client: TestClient
    ) -> None:
        """Test that list[Path] parameters generate appropriate upload endpoints."""
        with test_client as client:
            # Get the OpenAPI schema
            response = client.get("/openapi.json")
            assert response.status_code == 200
            openapi_schema = response.json()

            # Should have upload endpoint for list files parameter
            list_upload_path = "/action/list_file_action/{action_id}/upload/files"
            assert list_upload_path in openapi_schema["paths"]

            # Check the endpoint configuration
            upload_endpoint = openapi_schema["paths"][list_upload_path]["post"]
            assert "summary" in upload_endpoint
            assert "files" in upload_endpoint["summary"]
            assert "list_file_action" in upload_endpoint["tags"]

    def test_optional_file_upload_endpoints_generated(
        self, test_client: TestClient
    ) -> None:
        """Test that Optional[Path] parameters generate appropriate upload endpoints."""
        with test_client as client:
            # Get the OpenAPI schema
            response = client.get("/openapi.json")
            assert response.status_code == 200
            openapi_schema = response.json()

            # Should have upload endpoint for optional file parameter
            optional_upload_path = (
                "/action/optional_file_action/{action_id}/upload/optional_file"
            )
            assert optional_upload_path in openapi_schema["paths"]

            # Check the endpoint configuration
            upload_endpoint = openapi_schema["paths"][optional_upload_path]["post"]
            assert "Optional" in upload_endpoint["description"]

    def test_optional_list_file_upload_endpoints_generated(
        self, test_client: TestClient
    ) -> None:
        """Test that Optional[list[Path]] parameters generate appropriate upload endpoints."""
        with test_client as client:
            # Get the OpenAPI schema
            response = client.get("/openapi.json")
            assert response.status_code == 200
            openapi_schema = response.json()

            # Should have upload endpoint for optional list files parameter
            optional_list_upload_path = (
                "/action/optional_list_file_action/{action_id}/upload/optional_files"
            )
            assert optional_list_upload_path in openapi_schema["paths"]

            # Check the endpoint configuration
            upload_endpoint = openapi_schema["paths"][optional_list_upload_path]["post"]
            assert "Optional" in upload_endpoint["description"]

    def test_list_file_action_execution_flow(
        self, test_client: TestClient, tmp_path
    ) -> None:
        """Test executing an action with list[Path] parameter."""
        with test_client as client:
            time.sleep(0.5)

            # Create test files
            file1 = tmp_path / "file1.txt"
            file1.write_text("content of file 1")
            file2 = tmp_path / "file2.txt"
            file2.write_text("content of file 2")

            # Create action
            response = client.post("/action/list_file_action", json={"prefix": "batch"})
            assert response.status_code == 200
            action_id = response.json()["action_id"]

            # Upload multiple files using FastAPI's native list[UploadFile] support
            with file1.open("rb") as f1, file2.open("rb") as f2:
                response = client.post(
                    f"/action/list_file_action/{action_id}/upload/files",
                    files=[
                        ("files", ("file1.txt", f1, "text/plain")),
                        ("files", ("file2.txt", f2, "text/plain")),
                    ],
                )
            assert response.status_code == 200
            upload_result = response.json()
            assert upload_result["status"] == "uploaded"
            assert upload_result["file_arg"] == "files"
            assert upload_result["file_count"] == 2

            # Start action
            response = client.post(f"/action/list_file_action/{action_id}/start")
            assert response.status_code == 200
            result = response.json()

            # Wait for completion if needed
            if result["status"] == "running":
                time.sleep(0.1)
                response = client.get(f"/action/list_file_action/{action_id}/result")
                result = response.json()

            assert result["status"] == "succeeded"
            assert "batch: processed 2 files" in result["json_result"]
            assert "file1.txt, file2.txt" in result["json_result"]

    def test_optional_file_action_execution_without_file(
        self, test_client: TestClient
    ) -> None:
        """Test executing an action with Optional[Path] parameter without providing the file."""
        with test_client as client:
            time.sleep(0.5)

            # Create action without optional file
            response = client.post(
                "/action/optional_file_action", json={"required_param": "test"}
            )
            assert response.status_code == 200
            action_id = response.json()["action_id"]

            # Start action without uploading optional file
            response = client.post(f"/action/optional_file_action/{action_id}/start")
            assert response.status_code == 200
            result = response.json()

            # Should succeed and indicate no optional file was provided
            assert result["status"] in ["succeeded", "running"]
            # Wait for completion if needed
            if result["status"] == "running":
                time.sleep(0.1)
                response = client.get(
                    f"/action/optional_file_action/{action_id}/result"
                )
                result = response.json()

            assert result["status"] == "succeeded"
            assert "no optional file provided" in result["json_result"]

    def test_optional_file_action_execution_with_file(
        self, test_client: TestClient, tmp_path
    ) -> None:
        """Test executing an action with Optional[Path] parameter with providing the file."""
        with test_client as client:
            time.sleep(0.5)

            # Create test file
            test_file = tmp_path / "optional_test.txt"
            test_file.write_text("This is optional content")

            # Create action
            response = client.post(
                "/action/optional_file_action",
                json={"required_param": "test_with_file"},
            )
            assert response.status_code == 200
            action_id = response.json()["action_id"]

            # Upload optional file
            with test_file.open("rb") as f:
                response = client.post(
                    f"/action/optional_file_action/{action_id}/upload/optional_file",
                    files={"file": ("optional_test.txt", f, "text/plain")},
                )
            assert response.status_code == 200

            # Start action
            response = client.post(f"/action/optional_file_action/{action_id}/start")
            assert response.status_code == 200
            result = response.json()

            # Wait for completion if needed
            if result["status"] == "running":
                time.sleep(0.1)
                response = client.get(
                    f"/action/optional_file_action/{action_id}/result"
                )
                result = response.json()

            assert result["status"] == "succeeded"
            assert "processed file with" in result["json_result"]
            assert (
                "24 characters" in result["json_result"]
            )  # Length of "This is optional content"


class TestProposalExampleActionResultHandling:
    """Test the action result handling features as described in the proposal."""

    @pytest.fixture
    def proposal_test_client(self) -> TestClient:
        """Create a test client with actions that match the proposal examples."""

        class ProposalTestNode(TestNode):
            """Test node with actions matching the proposal."""

            @action
            def read_sensor(self) -> ReadSensorValue:
                """Implementation matching the proposal example - returns simple ReadSensorValue."""
                return ReadSensorValue(value=10, timestamp=datetime.now())

            @action
            def get_temperature_reading(self) -> TestNewActionResults:
                """Returns a complex pydantic model."""
                return TestNewActionResults(
                    sensor_id="TEMP_001",
                    temperature=23.5,
                    humidity=45.2,
                    status="active",
                )

            @action
            def return_simple_int(self) -> int:
                """Returns a simple integer."""
                return 42

            @action
            def return_simple_string(self) -> str:
                """Returns a simple string."""
                return "hello world"

            @action
            def return_dict_data(self) -> dict:
                """Returns a dictionary."""
                return {"key": "value", "number": 123}

            @action
            def create_test_file(self) -> Path:
                """Returns a single file."""
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False
                ) as f:
                    f.write("test file content")
                    return Path(f.name)

        node_definition = NodeDefinition(
            node_name="Proposal Test Node",
            module_name="proposal_test_node",
            description="A test node module for testing the action result handling proposal.",
        )

        test_node = ProposalTestNode(
            node_definition=node_definition,
            node_config=TestNodeConfig(
                test_required_param=1,
            ),
        )
        test_node.start_node(testing=True)
        return TestClient(test_node.rest_api)

    def test_proposal_example_read_sensor(self, proposal_test_client: TestClient):
        """Test the exact example from the proposal - read_sensor action."""
        with proposal_test_client as client:
            time.sleep(0.5)  # Wait for node to initialize

            # Check node status first
            status_response = client.get("/status")
            assert status_response.status_code == 200

            # Create action
            response = client.post("/action/read_sensor", json={})
            assert response.status_code == 200
            action_data = response.json()
            action_id = action_data["action_id"]
            assert ULID.from_str(action_id)

            # Start action (no files needed)
            response = client.post(f"/action/read_sensor/{action_id}/start")
            assert response.status_code == 200
            result = response.json()

            # Check that it succeeded
            assert result["status"] == "succeeded"
            assert result["json_result"] is not None

            # Check that the json_result contains the ReadSensorValue data
            json_result = result["json_result"]
            assert "value" in json_result
            assert "timestamp" in json_result
            assert json_result["value"] == 10
            assert isinstance(json_result["timestamp"], str)  # ISO format timestamp

    def test_complex_pydantic_model_return(self, proposal_test_client: TestClient):
        """Test that complex pydantic models are properly handled."""
        with proposal_test_client as client:
            time.sleep(0.5)

            response = client.post("/action/get_temperature_reading", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/get_temperature_reading/{action_id}/start")
            result = response.json()

            assert result["status"] == "succeeded"
            json_result = result["json_result"]
            assert json_result["sensor_id"] == "TEMP_001"
            assert json_result["temperature"] == 23.5
            assert json_result["humidity"] == 45.2
            assert json_result["status"] == "active"

    def test_file_return_with_file_keys(self, proposal_test_client: TestClient):
        """Test that file returns use file keys instead of full paths."""
        with proposal_test_client as client:
            time.sleep(0.5)

            response = client.post("/action/create_test_file", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/create_test_file/{action_id}/start")
            result = response.json()

            assert result["status"] == "succeeded"
            assert result["json_result"] is None  # No JSON data
            assert result["files"] == ["file"]  # File key instead of full path

    def test_openapi_schema_generation(self, proposal_test_client: TestClient):
        """Test that OpenAPI schema is generated with proper types."""
        with proposal_test_client as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            schema = response.json()

            # Check that we have paths for our actions
            paths = schema["paths"]
            assert "/action/read_sensor/{action_id}/result" in paths
            assert "/action/get_temperature_reading/{action_id}/result" in paths

            # Check that components contain our action-specific result models
            components = schema.get("components", {})
            schemas = components.get("schemas", {})

            # Should have action-specific result models
            result_models = [name for name in schemas if "ActionResult" in name]
            assert len(result_models) > 0

    def test_backward_compatibility(self, proposal_test_client: TestClient):
        """Test that the implementation maintains backward compatibility."""
        with proposal_test_client as client:
            time.sleep(0.5)

            # Test that generic endpoints still work
            response = client.post("/action/read_sensor", json={})
            action_id = response.json()["action_id"]

            response = client.post(f"/action/read_sensor/{action_id}/start")
            assert response.status_code == 200

            # Generic result endpoint should still work
            response = client.get(f"/action/{action_id}/result")
            assert response.status_code == 200
            result = response.json()
            assert result["json_result"]["value"] == 10

            # Generic status endpoint should still work
            response = client.get(f"/action/{action_id}/status")
            assert response.status_code == 200


class TestRestActionResultType:
    """Test the RestActionResult type itself."""

    def test_rest_action_result_files_field(self):
        """Test that RestActionResult has the correct files field type."""
        # Create a RestActionResult instance
        result = RestActionResult(
            status=ActionStatus.SUCCEEDED, files=["file1", "file2"]
        )

        assert result.files == ["file1", "file2"]
        assert isinstance(result.files, list)

        # Test serialization
        result_dict = result.model_dump()
        assert result_dict["files"] == ["file1", "file2"]

    def test_rest_action_result_inherits_from_action_result(self):
        """Test that RestActionResult properly inherits from ActionResult."""
        result = RestActionResult(
            status=ActionStatus.SUCCEEDED,
            json_result={"test": "data"},
            files=["test_file"],
        )

        # Should have all ActionResult fields
        assert hasattr(result, "action_id")
        assert hasattr(result, "status")
        assert hasattr(result, "errors")
        assert hasattr(result, "json_result")
        assert hasattr(result, "datapoints")
        assert hasattr(result, "history_created_at")

        # Should have the modified files field
        assert result.files == ["test_file"]


class TestDynamicModelCreation:
    """Test the create_dynamic_model helper function."""

    def test_create_dynamic_model_with_json_type(self):
        """Test creating a dynamic model with a specific JSON result type."""
        # Create a dynamic model for read_sensor action
        dynamic_model = create_dynamic_model(
            action_name="read_sensor", json_result_type=ReadSensorValue
        )

        # Check the model class
        assert dynamic_model.__name__ == "ReadSensorActionResult"
        assert issubclass(dynamic_model, RestActionResult)

        # Create an instance
        instance = dynamic_model(
            status=ActionStatus.SUCCEEDED,
            json_result=ReadSensorValue(value=42, timestamp=datetime.now()),
        )

        assert instance.status == ActionStatus.SUCCEEDED
        assert instance.json_result.value == 42

    def test_create_dynamic_model_without_json_type(self):
        """Test creating a dynamic model without a specific JSON type."""
        dynamic_model = create_dynamic_model(action_name="simple_action")

        assert dynamic_model.__name__ == "SimpleActionActionResult"
        assert issubclass(dynamic_model, RestActionResult)

        # Should still work with any json_result
        instance = dynamic_model(
            status=ActionStatus.SUCCEEDED, json_result={"any": "data"}
        )

        assert instance.json_result == {"any": "data"}
