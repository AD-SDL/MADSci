"""Automated pytest unit tests for the RestNode class."""

import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
    ActionStatus,
    extract_file_parameters,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import NodeDefinition, NodeInfo, NodeStatus
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
        assert len(node_info.actions) == 9
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
    """Test that file download routes are created for actions that return files."""
    with test_client as client:
        # Get the OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_schema = response.json()

        # Check for single file result action
        file_result_path = "/action/file_result_action/{action_id}/download/file"
        assert file_result_path in openapi_schema["paths"]

        file_endpoint = openapi_schema["paths"][file_result_path]["get"]
        assert "summary" in file_endpoint
        assert "download" in file_endpoint["summary"].lower()
        assert "file_result_action" in file_endpoint["tags"]

        # Check for multiple file result action
        output_file_path = (
            "/action/multiple_file_result_action/{action_id}/download/output_file"
        )
        log_file_path = (
            "/action/multiple_file_result_action/{action_id}/download/log_file"
        )
        all_files_path = "/action/multiple_file_result_action/{action_id}/download"

        assert output_file_path in openapi_schema["paths"]
        assert log_file_path in openapi_schema["paths"]
        assert all_files_path in openapi_schema["paths"]

        # All should use the same tag for grouping
        output_endpoint = openapi_schema["paths"][output_file_path]["get"]
        log_endpoint = openapi_schema["paths"][log_file_path]["get"]
        all_files_endpoint = openapi_schema["paths"][all_files_path]["get"]

        assert "multiple_file_result_action" in output_endpoint["tags"]
        assert "multiple_file_result_action" in log_endpoint["tags"]
        assert "multiple_file_result_action" in all_files_endpoint["tags"]

        # Verify actions without file results don't have download endpoints
        test_action_paths = [
            path
            for path in openapi_schema["paths"]
            if "test_action" in path and "download" in path
        ]
        assert len(test_action_paths) == 0


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
