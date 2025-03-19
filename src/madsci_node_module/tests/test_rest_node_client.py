"""Automated pytest unit tests for the RestNodeClient class."""

import json
from unittest.mock import MagicMock, patch

import pytest
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
    ActionStatus,
    ActionSucceeded,
    new_ulid_str,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import NodeInfo, NodeSetConfigResponse, NodeStatus


@pytest.fixture
def rest_node_client() -> RestNodeClient:
    """Fixture to create a RestNodeClient instance."""
    return RestNodeClient(url="http://localhost:2000")


@patch("requests.get")
def test_get_status(mock_get: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test the get_status method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"ready": True, "locked": False}
    mock_get.return_value = mock_response

    status = rest_node_client.get_status()
    assert isinstance(status, NodeStatus)
    assert status.ready is True
    assert status.locked is False
    mock_get.assert_called_once_with("http://localhost:2000/status", timeout=10)


@patch("requests.get")
def test_get_info(mock_get: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test the get_info method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = NodeInfo(
        node_name="Test Node", module_name="test_module"
    ).model_dump(mode="json")
    mock_get.return_value = mock_response

    info = rest_node_client.get_info()
    assert isinstance(info, NodeInfo)
    assert info.node_name == "Test Node"
    assert info.module_name == "test_module"
    mock_get.assert_called_once_with("http://localhost:2000/info", timeout=10)


@patch("requests.post")
def test_send_action(mock_post: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test the send_action method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = ActionSucceeded().model_dump(mode="json")
    mock_post.return_value = mock_response

    action_request = ActionRequest(action_name="test_action", args={}, files={})
    result = rest_node_client.send_action(action_request)
    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == mock_response.json.return_value["action_id"]
    mock_post.assert_called_once_with(
        "http://localhost:2000/action",
        params={
            "action_name": "test_action",
            "args": json.dumps({}),
            "action_id": action_request.action_id,
        },
        files=[],
        timeout=10,
    )


@patch("requests.get")
def test_get_action_result(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the get_action_result method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = ActionSucceeded().model_dump(mode="json")
    mock_get.return_value = mock_response

    result = rest_node_client.get_action_result(
        mock_response.json.return_value["action_id"]
    )
    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == mock_response.json.return_value["action_id"]
    mock_get.assert_called_once_with(
        f"http://localhost:2000/action/{mock_response.json.return_value['action_id']}",
        timeout=10,
    )


@patch("requests.post")
def test_set_config(mock_post: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test the set_config method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = NodeSetConfigResponse(success=True).model_dump(
        mode="json"
    )
    mock_post.return_value = mock_response

    new_config = {"key": "value"}
    response = rest_node_client.set_config(new_config)
    assert isinstance(response, NodeSetConfigResponse)
    assert response.success is True
    mock_post.assert_called_once_with(
        "http://localhost:2000/config", json=new_config, timeout=60
    )


@patch("requests.post")
def test_send_admin_command(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the send_admin_command method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = AdminCommandResponse(success=True).model_dump(
        mode="json"
    )
    mock_post.return_value = mock_response

    response = rest_node_client.send_admin_command("lock")
    assert isinstance(response, AdminCommandResponse)
    assert response.success is True
    mock_post.assert_called_once_with("http://localhost:2000/admin/lock", timeout=10)


@patch("requests.get")
def test_get_log(mock_get: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test the get_log method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "event1": {"event_type": "INFO", "event_data": {"message": "Test log entry 1"}},
        "event2": {
            "event_type": "ERROR",
            "event_data": {"message": "Test log entry 2"},
        },
    }
    mock_get.return_value = mock_response

    log = rest_node_client.get_log()
    assert isinstance(log, dict)
    assert len(log) == 2
    assert log["event1"]["event_type"] == "INFO"
    assert log["event1"]["event_data"]["message"] == "Test log entry 1"
    assert log["event2"]["event_type"] == "ERROR"
    assert log["event2"]["event_data"]["message"] == "Test log entry 2"
    mock_get.assert_called_once_with("http://localhost:2000/log", timeout=10)


@patch("requests.get")
def test_get_state(mock_get: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test the get_state method."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"key1": "value1", "key2": "value2"}
    mock_get.return_value = mock_response

    state = rest_node_client.get_state()
    assert isinstance(state, dict)
    assert state["key1"] == "value1"
    assert state["key2"] == "value2"
    mock_get.assert_called_once_with("http://localhost:2000/state", timeout=10)


@patch("requests.get")
def test_get_action_history(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the get_action_history method."""
    mock_response = MagicMock()
    mock_response.ok = True
    action1_id = new_ulid_str()
    action2_id = new_ulid_str()
    mock_response.json.return_value = {
        action1_id: [
            {"status": "NOT_STARTED", "action_id": action1_id},
            {"status": "RUNNING", "action_id": action1_id},
            {"status": "SUCCEEDED", "action_id": action1_id},
        ],
        action2_id: [
            {"status": "NOT_STARTED", "action_id": action2_id},
            {"status": "FAILED", "action_id": action2_id},
        ],
    }
    mock_get.return_value = mock_response

    action_history = rest_node_client.get_action_history()
    assert isinstance(action_history, dict)
    assert len(action_history) == 2
    assert len(action_history[action1_id]) == 3
    assert action_history[action1_id][0]["status"] == "NOT_STARTED"
    assert action_history[action1_id][2]["status"] == "SUCCEEDED"
    assert len(action_history[action2_id]) == 2
    assert action_history[action2_id][1]["status"] == "FAILED"
    mock_get.assert_called_once_with(
        "http://localhost:2000/action", params={"action_id": None}, timeout=10
    )


@patch("requests.get")
def test_get_action_history_with_action_id(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the get_action_history method with a specified action_id."""
    mock_response = MagicMock()
    mock_response.ok = True
    action_id = new_ulid_str()
    mock_response.json.return_value = {
        action_id: [
            {"status": "NOT_STARTED", "action_id": action_id},
            {"status": "RUNNING", "action_id": action_id},
            {"status": "SUCCEEDED", "action_id": action_id},
        ]
    }
    mock_get.return_value = mock_response

    action_history = rest_node_client.get_action_history(action_id=action_id)
    assert isinstance(action_history, dict)
    assert len(action_history) == 1
    assert action_id in action_history
    assert len(action_history[action_id]) == 3
    assert action_history[action_id][0]["status"] == "NOT_STARTED"
    assert action_history[action_id][2]["status"] == "SUCCEEDED"
    mock_get.assert_called_once_with(
        "http://localhost:2000/action", params={"action_id": action_id}, timeout=10
    )
