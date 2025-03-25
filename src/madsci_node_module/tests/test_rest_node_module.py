"""Automated pytest unit tests for the RestNode class."""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.action_types import (
    ActionResult,
    ActionStatus,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.event_types import Event, EventClientConfig, EventLogLevel
from madsci.common.types.node_types import NodeDefinition, NodeInfo, NodeStatus

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


@pytest.fixture
def test_node(tmpdir: Path) -> TestNode:
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
            event_client_config=EventClientConfig(
                log_dir=Path(tmpdir),
                log_level=EventLogLevel.DEBUG,
            ),
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


def test_run_action(test_client: TestClient) -> None:
    """Test the test_action command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.post(
            "/action",
            params={
                "action_name": "test_action",
                "args": json.dumps({"test_param": 1}),
            },
        )
        assert response.status_code == 200
        assert (
            ActionResult.model_validate(response.json()).status == ActionStatus.RUNNING
        )
        response = client.get(f"/action/{response.json()['action_id']}")
        assert response.status_code == 200
        assert (
            ActionResult.model_validate(response.json()).status
            == ActionStatus.SUCCEEDED
        )

        response = client.post("/action", params={"action_name": "test_action"})
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status == ActionStatus.FAILED
        assert "Missing required arguments" in result.errors[0].message
        assert result.errors[0].error_type == "ValueError"


def test_run_action_fail(test_client: TestClient) -> None:
    """Test the test_action_fail command."""

    with test_client as client:
        time.sleep(0.5)
        response = client.post(
            "/action",
            params={"action_name": "test_fail", "args": json.dumps({"test_param": 1})},
        )
        assert ActionResult.model_validate(response.json()).status in [
            ActionStatus.FAILED,
            ActionStatus.RUNNING,
        ]
        response = client.get(f"/action/{response.json()['action_id']}")
        assert response.status_code == 200
        action_result = ActionResult.model_validate(response.json())
        assert action_result.status == ActionStatus.FAILED
        assert len(action_result.errors) == 1
        assert "returned 'False'" in action_result.errors[0].message


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
        assert len(node_info.actions) == 4
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


def test_get_action_result(test_client: TestClient) -> None:
    """Test the get_action_result command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.post(
            "/action",
            params={
                "action_name": "test_action",
                "args": json.dumps({"test_param": 1}),
            },
        )
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]

        response = client.get(f"/action/{result.action_id}")
        assert response.status_code == 200
        fetched_result = ActionResult.model_validate(response.json())
        assert fetched_result.status == ActionStatus.SUCCEEDED
        assert fetched_result.action_id == result.action_id

        response = client.get("/action/not_a_valid_id")
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

        response = client.post(
            "/action",
            params={
                "action_name": "test_action",
                "args": json.dumps({"test_param": 1}),
            },
        )
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]
        response = client.get(f"/action/{response.json()['action_id']}")
        assert response.status_code == 200
        assert ActionResult.model_validate(response.json()).status in [
            ActionStatus.RUNNING,
            ActionStatus.SUCCEEDED,
        ]

        response = client.post(
            "/action",
            params={
                "action_name": "test_action",
                "args": json.dumps({"test_param": 1}),
            },
        )
        assert response.status_code == 200
        result2 = ActionResult.model_validate(response.json())
        assert result2.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]

        response = client.get("/action")
        assert response.status_code == 200
        action_history = response.json()
        assert len(action_history) - existing_history_length == 2
        assert result.action_id in action_history
        assert result2.action_id in action_history
        assert len(action_history[result.action_id]) == 3
        assert (
            ActionResult.model_validate(action_history[result.action_id][0]).status
            == ActionStatus.NOT_STARTED
        )
        assert (
            ActionResult.model_validate(action_history[result.action_id][1]).status
            == ActionStatus.RUNNING
        )
        assert (
            ActionResult.model_validate(action_history[result.action_id][2]).status
            == ActionStatus.SUCCEEDED
        )

        response = client.get("/action", params={"action_id": result2.action_id})
        assert response.status_code == 200
        action_history = response.json()
        assert len(action_history) == 1
        assert result.action_id not in action_history
        assert result2.action_id in action_history
        assert len(action_history[result2.action_id]) == 3
        assert (
            ActionResult.model_validate(action_history[result2.action_id][0]).status
            == ActionStatus.NOT_STARTED
        )
        assert (
            ActionResult.model_validate(action_history[result2.action_id][1]).status
            == ActionStatus.RUNNING
        )
        assert (
            ActionResult.model_validate(action_history[result2.action_id][2]).status
            == ActionStatus.SUCCEEDED
        )


def test_get_log(test_client: TestClient) -> None:
    """Test the get_log command."""
    with test_client as client:
        time.sleep(0.5)
        response = client.post(
            "/action",
            params={
                "action_name": "test_action",
                "args": json.dumps({"test_param": 1}),
            },
        )
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]

        response = client.get("/log")
        assert response.status_code == 200
        assert len(response.json()) > 0
        for _, entry in response.json().items():
            Event.model_validate(entry)


def test_optional_param_action_with_optional_param(test_client: TestClient) -> None:
    """Test the test_optional_param_action command with the optional parameter."""
    with test_client as client:
        time.sleep(0.5)
        response = client.post(
            "/action",
            params={
                "action_name": "test_optional_param_action",
                "args": json.dumps({"test_param": 1, "optional_param": "test_value"}),
            },
        )
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]


def test_optional_param_action_without_optional_param(test_client: TestClient) -> None:
    """Test the test_optional_param_action command without the optional parameter."""
    with test_client as client:
        time.sleep(0.5)
        response = client.post(
            "/action",
            params={
                "action_name": "test_optional_param_action",
                "args": json.dumps({"test_param": 1}),
            },
        )
        assert response.status_code == 200
        result = ActionResult.model_validate(response.json())
        assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]
