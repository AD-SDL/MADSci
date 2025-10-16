"""Shared utilities for MADSci node module tests."""

import contextlib
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from madsci.common.types.action_types import ActionResult, ActionStatus
from starlette.testclient import TestClient


def wait_for_node_ready(
    client: TestClient, timeout: float = 10.0, allow_initializing: bool = False
) -> bool:
    """Wait for node to be ready before executing actions.

    Args:
        client: FastAPI test client
        timeout: Maximum time to wait in seconds (increased default to 10s)
        allow_initializing: If True, accept nodes that are initializing but responsive

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
                # If we allow initializing nodes and it's not errored, consider it usable
                if (
                    allow_initializing
                    and status_data.get("initializing", False)
                    and not status_data.get("errored", False)
                ):
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

    # Wait for node to be ready first
    assert wait_for_node_ready(client, timeout=timeout), "Node failed to become ready"

    # Create action with RestActionRequest structure
    # Extract var_args and var_kwargs from parameters if present
    args = dict(parameters) if parameters else {}
    var_args = args.pop("var_args", None)
    var_kwargs = args.pop("var_kwargs", None)

    request_data = {"args": args}
    if var_args is not None:
        request_data["var_args"] = var_args
    if var_kwargs is not None:
        request_data["var_kwargs"] = var_kwargs
    response = client.post(f"/action/{action_name}", json=request_data)
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
            if result.get("status") in ["succeeded", "failed", "cancelled"]:
                return result
        time.sleep(0.1)  # Check every 100ms

    raise AssertionError(f"Action {action_name} timed out after {timeout} seconds")


def execute_action_with_validation(
    client: TestClient,
    action_name: str,
    parameters: Optional[dict] = None,
    expected_status: ActionStatus = ActionStatus.SUCCEEDED,
    timeout: float = 10.0,
) -> ActionResult:
    """Execute action and validate result in one call.

    Args:
        client: FastAPI test client
        action_name: Name of the action to execute
        parameters: Optional parameters for the action
        expected_status: Expected final status of the action
        timeout: Maximum time to wait for completion

    Returns:
        ActionResult: The final action result

    Raises:
        AssertionError: If action doesn't reach expected status
    """
    result = execute_action_and_wait(client, action_name, parameters, timeout)

    # Convert string status to enum if needed
    actual_status = result.get("status")
    if isinstance(actual_status, str):
        actual_status = ActionStatus(actual_status)
    elif isinstance(actual_status, ActionStatus):
        pass
    else:
        raise AssertionError(f"Invalid status type: {type(actual_status)}")

    assert actual_status == expected_status, (
        f"Action {action_name} ended with status {actual_status}, "
        f"expected {expected_status}. Result: {result}"
    )

    return result


def validate_openapi_schema_consistency(
    client: TestClient, action_name: str, expected_schema_properties: List[str]
) -> bool:
    """Validate OpenAPI schema matches expected structure.

    Args:
        client: FastAPI test client
        action_name: Name of the action to check
        expected_schema_properties: List of expected property names in schema

    Returns:
        bool: True if schema is consistent, False otherwise
    """
    # Get the OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()

    # Navigate to the action schema
    paths = openapi_schema.get("paths", {})
    action_path = f"/action/{action_name}"

    if action_path not in paths:
        return False

    # Check if all expected properties are present
    post_schema = paths[action_path].get("post", {})
    request_body = post_schema.get("requestBody", {})
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})
    properties = schema.get("properties", {})

    return all(prop in properties for prop in expected_schema_properties)


def create_temp_files_for_testing(
    file_configs: List[Dict[str, str]],
) -> Dict[str, Path]:
    """Create temporary files for file upload testing.

    Args:
        file_configs: List of file configurations with 'name', 'content',
                     and optional 'suffix' keys

    Returns:
        Dict[str, Path]: Mapping of file names to their paths
    """
    temp_files = {}

    for config in file_configs:
        name = config["name"]
        content = config["content"]
        suffix = config.get("suffix", ".txt")

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=suffix
        ) as temp_file:
            temp_file.write(content)
            temp_files[name] = Path(temp_file.name)

    return temp_files


def validate_admin_command_response(
    client: TestClient, command: str, expected_state_changes: Dict[str, bool]
) -> None:
    """Validate admin command execution and resulting state changes.

    Args:
        client: FastAPI test client
        command: Admin command to execute (e.g., 'lock', 'unlock', 'pause')
        expected_state_changes: Expected state changes as {field: expected_value}
    """
    # Execute the admin command
    response = client.post(f"/admin/{command}")
    assert response.status_code == 200

    # Validate command response
    command_result = response.json()
    assert command_result.get("success") is True
    assert not command_result.get("errors")

    # Check resulting state
    status_response = client.get("/status")
    assert status_response.status_code == 200

    status_data = status_response.json()
    for field, expected_value in expected_state_changes.items():
        assert status_data.get(field) == expected_value, (
            f"Expected {field}={expected_value}, got {status_data.get(field)}"
        )


def parametrize_file_scenarios():
    """Decorator factory for common file testing scenarios.

    Returns pytest parametrize decorator with common file test cases.
    """

    return pytest.mark.parametrize(
        "file_scenario",
        [
            {
                "type": "single_file_result",
                "action": "file_result_action",
                "files": [],  # No input files needed
                "expected_response_type": str,  # Returns a file, but for REST API we expect files list
            },
            {
                "type": "multiple_file_result",
                "action": "multiple_file_result_action",
                "files": [],  # No input files needed
                "expected_response_type": dict,  # Returns multiple files
            },
            {
                "type": "mixed_result",
                "action": "mixed_pydantic_and_file_action",
                "files": [],  # No input files needed
                "expected_response_type": dict,  # Returns pydantic model + file
            },
            {
                "type": "custom_pydantic_result",
                "action": "custom_pydantic_result_action",
                "files": [],  # No input files needed
                "expected_response_type": dict,  # Returns custom pydantic model
            },
        ],
    )


def parametrize_action_execution_patterns():
    """Decorator factory for common action execution test patterns.

    Returns pytest parametrize decorator with common action test cases.
    """

    return pytest.mark.parametrize(
        "action_config",
        [
            {
                "name": "test_action",
                "params": {"test_param": 1},
                "expected_status": ActionStatus.SUCCEEDED,
            },
            {
                "name": "test_fail",
                "params": {"test_param": 1},
                "expected_status": ActionStatus.FAILED,
            },
            {
                "name": "test_optional_param_action",
                "params": {"test_param": 42, "optional_param": "test"},
                "expected_status": ActionStatus.SUCCEEDED,
            },
        ],
    )


def parametrize_admin_commands():
    """Decorator factory for admin command testing.

    Returns pytest parametrize decorator with admin command test cases.
    """

    return pytest.mark.parametrize(
        "command,expected_state",
        [
            ("lock", {"ready": False, "locked": True}),
            ("unlock", {"ready": True, "locked": False}),
            ("pause", {"paused": True, "ready": False}),
            ("resume", {"paused": False, "ready": True}),
        ],
    )
