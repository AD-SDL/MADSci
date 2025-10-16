"""Comprehensive unit tests for the RestNodeClient class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from madsci.client.node.rest_node_client import (
    RestNodeClient,
)
from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
    ActionRunning,
    ActionStatus,
    ActionSucceeded,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import NodeInfo, NodeSetConfigResponse, NodeStatus
from madsci.common.utils import new_ulid_str


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
def test_send_action_no_await(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the send_action method without awaiting."""
    action_id = new_ulid_str()

    # Mock create_action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock start_action response
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(action_id=action_id).model_dump(
        mode="json"
    )

    mock_post.side_effect = [create_response, start_response]

    action_request = ActionRequest(action_name="test_action", args={}, files={})
    result = rest_node_client.send_action(action_request, await_result=False)

    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == action_id

    # Verify the calls: create_action then start_action
    assert mock_post.call_count == 2

    # First call: create action
    create_call = mock_post.call_args_list[0]
    assert create_call[0][0] == "http://localhost:2000/action/test_action"
    assert "json" in create_call[1]

    # Second call: start action
    start_call = mock_post.call_args_list[1]
    assert (
        start_call[0][0]
        == f"http://localhost:2000/action/test_action/{action_id}/start"
    )


@patch("requests.post")
@patch("requests.get")
def test_send_action_await(
    mock_get: MagicMock, mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the send_action method with awaiting."""
    action_id = new_ulid_str()

    # Mock create_action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock start_action response (returns running status)
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionRunning(action_id=action_id).model_dump(
        mode="json"
    )

    mock_post.side_effect = [create_response, start_response]

    # Mock status check (first running, then completed)
    running_response = MagicMock()
    running_response.ok = True
    running_response.json.return_value = ActionStatus.RUNNING.value

    completed_response = MagicMock()
    completed_response.ok = True
    completed_response.json.return_value = ActionStatus.SUCCEEDED.value

    # Mock result data response (when action completes successfully)
    result_data_response = MagicMock()
    result_data_response.ok = True
    result_data_response.json.return_value = ActionSucceeded(
        action_id=action_id
    ).model_dump(mode="json")

    mock_get.side_effect = [running_response, completed_response, result_data_response]

    action_request = ActionRequest(action_name="test_action", args={}, files={})
    result = rest_node_client.send_action(action_request)

    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == action_id

    # Verify the calls
    assert mock_post.call_count == 2  # create + start
    assert mock_get.call_count == 3  # status check + completed status + result data

    # Verify status endpoint was called
    status_calls = [
        call for call in mock_get.call_args_list if "/action/test_action/" in call[0][0]
    ]
    assert len(status_calls) >= 2


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
        f"http://localhost:2000/action/{mock_response.json.return_value['action_id']}/result",
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


# Additional tests for improved coverage


def test_get_resources_not_implemented(rest_node_client: RestNodeClient) -> None:
    """Test that get_resources raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="get_resources is not implemented"):
        rest_node_client.get_resources()


@patch("requests.post")
def test_send_action_http_error(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test send_action method with HTTP error during create_action."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    http_error = requests.HTTPError("500 Server Error")
    http_error.response = mock_response  # Add the response attribute
    mock_response.raise_for_status.side_effect = http_error
    mock_post.return_value = mock_response

    action_request = ActionRequest(action_name="test_action", args={}, files={})

    with pytest.raises(requests.HTTPError):
        rest_node_client.send_action(action_request, await_result=False)


@patch("requests.post")
def test_send_action_with_files(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test send_action method with file uploads."""
    action_id = new_ulid_str()

    # Mock create_action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock file upload responses
    upload_response1 = MagicMock()
    upload_response1.ok = True
    upload_response2 = MagicMock()
    upload_response2.ok = True

    # Mock start_action response
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(action_id=action_id).model_dump(
        mode="json"
    )

    mock_post.side_effect = [
        create_response,
        upload_response1,
        upload_response2,
        start_response,
    ]

    # Create temporary files for testing
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file1:
        temp_file1.write("test content 1")
        temp_file1_path = temp_file1.name

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file2:
        temp_file2.write("test content 2")
        temp_file2_path = temp_file2.name

    try:
        action_request = ActionRequest(
            action_name="test_action",
            args={},
            files={"file1": temp_file1_path, "file2": temp_file2_path},
        )

        result = rest_node_client.send_action(action_request, await_result=False)
        assert isinstance(result, ActionResult)
        assert result.status == ActionStatus.SUCCEEDED
        assert result.action_id == action_id

        # Verify the sequence of calls: create + 2 file uploads + start
        assert mock_post.call_count == 4

        # First call: create action
        create_call = mock_post.call_args_list[0]
        assert create_call[0][0] == "http://localhost:2000/action/test_action"

        # File upload calls
        upload_calls = mock_post.call_args_list[1:3]
        upload_urls = [call[0][0] for call in upload_calls]
        assert (
            f"http://localhost:2000/action/test_action/{action_id}/upload/file1"
            in upload_urls
        )
        assert (
            f"http://localhost:2000/action/test_action/{action_id}/upload/file2"
            in upload_urls
        )

        # Start action call
        start_call = mock_post.call_args_list[3]
        assert (
            start_call[0][0]
            == f"http://localhost:2000/action/test_action/{action_id}/start"
        )

    finally:
        # Clean up temporary files
        Path(temp_file1_path).unlink(missing_ok=True)
        Path(temp_file2_path).unlink(missing_ok=True)


@patch("requests.post")
def test_send_action_file_response(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test send_action method."""
    action_id = new_ulid_str()

    # Mock create_action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock start_action response
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(action_id=action_id).model_dump(
        mode="json"
    )

    mock_post.side_effect = [create_response, start_response]

    action_request = ActionRequest(action_name="test_action", args={}, files={})

    result = rest_node_client.send_action(action_request, await_result=False)

    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == action_id


@patch("time.sleep")
@patch("requests.get")
def test_await_action_result_timeout(
    mock_get: MagicMock,
    mock_sleep: MagicMock,  # noqa: ARG001
    rest_node_client: RestNodeClient,
) -> None:
    """Test await_action_result with timeout."""
    action_id = new_ulid_str()

    # Mock response that never completes
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.headers = {}
    mock_response.json.return_value = ActionStatus.RUNNING.value
    mock_get.return_value = mock_response

    with pytest.raises(TimeoutError, match="Timed out waiting for action to complete"):
        rest_node_client.await_action_result(action_id, timeout=0.1)


@patch("time.sleep")
@patch("requests.get")
def test_await_action_result_exponential_backoff(
    mock_get: MagicMock, mock_sleep: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test await_action_result with exponential backoff."""
    action_id = new_ulid_str()

    # Mock responses: running status -> running status -> succeeded status -> result
    running_status_response = MagicMock()
    running_status_response.ok = True
    running_status_response.headers = {}
    running_status_response.json.return_value = ActionStatus.RUNNING.value

    succeeded_status_response = MagicMock()
    succeeded_status_response.ok = True
    succeeded_status_response.headers = {}
    succeeded_status_response.json.return_value = ActionStatus.SUCCEEDED.value

    result_response = MagicMock()
    result_response.ok = True
    result_response.headers = {}
    result_response.json.return_value = ActionSucceeded(action_id=action_id).model_dump(
        mode="json"
    )

    mock_get.side_effect = [
        running_status_response,
        running_status_response,
        succeeded_status_response,
        result_response,
    ]

    result = rest_node_client.await_action_result(action_id)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == action_id

    # Verify exponential backoff
    assert mock_sleep.call_count == 2
    # First sleep: 0.25, second sleep: 0.25 * 1.5 = 0.375
    mock_sleep.assert_any_call(0.25)
    mock_sleep.assert_any_call(0.375)


@patch("requests.get")
def test_http_error_handling(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test HTTP error handling in various methods."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_get.return_value = mock_response

    # Test get_status HTTP error
    with pytest.raises(requests.HTTPError):
        rest_node_client.get_status()

    # Test get_info HTTP error
    with pytest.raises(requests.HTTPError):
        rest_node_client.get_info()

    # Test get_state HTTP error
    with pytest.raises(requests.HTTPError):
        rest_node_client.get_state()

    # Test get_log HTTP error
    with pytest.raises(requests.HTTPError):
        rest_node_client.get_log()


def test_client_capabilities():
    """Test that client has correct capabilities."""
    client = RestNodeClient(url="http://localhost:2000")

    capabilities = client.supported_capabilities

    # Test supported capabilities
    assert capabilities.get_info is True
    assert capabilities.get_state is True
    assert capabilities.get_status is True
    assert capabilities.send_action is True
    assert capabilities.get_action_result is True
    assert capabilities.get_action_history is True
    assert capabilities.action_files is True
    assert capabilities.send_admin_commands is True
    assert capabilities.set_config is True
    assert capabilities.get_log is True

    # Test unsupported capabilities
    assert capabilities.get_resources is False


def test_url_protocols():
    """Test supported URL protocols."""
    assert "http" in RestNodeClient.url_protocols
    assert "https" in RestNodeClient.url_protocols


@patch("requests.post")
def test_create_action(mock_post: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test create_action method."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"action_id": action_id}
    mock_post.return_value = mock_response

    action_request = ActionRequest(
        action_name="test_action", args={"param": "value"}, files={}
    )
    result_action_id = rest_node_client._create_action(action_request)

    assert result_action_id == action_id
    mock_post.assert_called_once_with(
        "http://localhost:2000/action/test_action",
        json={"args": {"param": "value"}},
        timeout=60,
    )


@patch("requests.post")
def test_upload_action_files(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test upload_action_files method."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_post.return_value = mock_response

    # Create temporary files for testing
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write("test content")
        temp_file_path = temp_file.name

    try:
        rest_node_client._upload_action_files(
            "test_action", action_id, {"input_file": temp_file_path}
        )

        mock_post.assert_called_once_with(
            f"http://localhost:2000/action/test_action/{action_id}/upload/input_file",
            files={"file": mock_post.call_args[1]["files"]["file"]},
            timeout=60,
        )

    finally:
        Path(temp_file_path).unlink(missing_ok=True)


@patch("requests.post")
def test_start_action(mock_post: MagicMock, rest_node_client: RestNodeClient) -> None:
    """Test start_action method."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = ActionRunning(action_id=action_id).model_dump(
        mode="json"
    )
    mock_post.return_value = mock_response

    result = rest_node_client._start_action("test_action", action_id)

    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.RUNNING
    assert result.action_id == action_id
    mock_post.assert_called_once_with(
        f"http://localhost:2000/action/test_action/{action_id}/start",
        timeout=60,
    )


@patch("requests.get")
def test_get_action_status(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test get_action_status method."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = ActionStatus.RUNNING.value
    mock_get.return_value = mock_response

    result = rest_node_client.get_action_status(action_id)

    assert isinstance(result, ActionStatus)
    assert result == ActionStatus.RUNNING
    mock_get.assert_called_once_with(
        f"http://localhost:2000/action/{action_id}/status",
        timeout=10,
    )


@patch("requests.get")
def test_get_action_result_data(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test get_action_result_data method."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = ActionSucceeded(action_id=action_id).model_dump(
        mode="json"
    )
    mock_get.return_value = mock_response

    result = rest_node_client.get_action_result_by_name("test_action", action_id)

    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == action_id
    mock_get.assert_called_once_with(
        f"http://localhost:2000/action/test_action/{action_id}/result",
        timeout=10,
    )


@patch("requests.get")
def test_get_action_files_zip(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test get_action_files_zip method."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.content = b"fake zip content"
    mock_get.return_value = mock_response

    with patch("tempfile.NamedTemporaryFile") as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = "/tmp/test_files.zip"  # noqa: S108

        result = rest_node_client._get_action_files_zip("test_action", action_id)

        assert result == Path("/tmp/test_files.zip")  # noqa: S108
        mock_get.assert_called_once_with(
            f"http://localhost:2000/action/test_action/{action_id}/download",
            timeout=60,
        )


@patch("requests.post")
def test_upload_action_files_list_support(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the _upload_action_files method with list[Path] support."""
    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        mock_response = MagicMock()
        mock_response.ok = True
        mock_post.return_value = mock_response

        # Test single file upload
        rest_node_client._upload_action_files(
            "test_action", "test_id", {"single_file": str(file1)}
        )

        # Verify single file upload call
        assert mock_post.called
        call_args = mock_post.call_args
        assert (
            call_args[0][0]
            == "http://localhost:2000/action/test_action/test_id/upload/single_file"
        )
        assert call_args[1]["timeout"] == 60
        assert "file" in call_args[1]["files"]

        # Reset mock for list upload test
        mock_post.reset_mock()

        # Test list file upload
        rest_node_client._upload_action_files(
            "test_action", "test_id", {"file_list": [str(file1), str(file2)]}
        )

        # Verify list file upload call
        # The exact files parameter structure depends on implementation
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 60
        assert "file_list" in str(call_args)  # files parameter should contain file_list


@patch("requests.post")
def test_send_action_with_list_files(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test sending an action with list[Path] files."""
    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        file1 = Path(temp_dir) / "test1.txt"
        file2 = Path(temp_dir) / "test2.txt"
        file1.write_text("test content 1")
        file2.write_text("test content 2")

        # Mock responses for the three-step process
        action_id = new_ulid_str()

        # Mock create action response
        create_response = MagicMock()
        create_response.ok = True
        create_response.json.return_value = {"action_id": action_id}

        # Mock file upload responses
        upload_response = MagicMock()
        upload_response.ok = True

        # Mock start action response
        start_response = MagicMock()
        start_response.ok = True
        start_response.json.return_value = ActionSucceeded(
            action_id=action_id, json_result="test result"
        ).model_dump(mode="json")

        mock_post.side_effect = [create_response, upload_response, start_response]

        # Create action request with list files
        action_request = ActionRequest(
            action_name="test_list_action",
            args={"param": "value"},
            files={"file_list": [str(file1), str(file2)]},
        )

        result = rest_node_client.send_action(action_request, await_result=False)

        # Verify the result
        assert isinstance(result, ActionResult)
        assert result.action_id == action_id
        assert result.status == ActionStatus.SUCCEEDED

        # Verify all three calls were made
        assert mock_post.call_count == 3


@patch("requests.post")
def test_send_action_with_var_args(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test sending an action request with variable arguments (*args)."""
    action_id = new_ulid_str()

    # Mock create action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock start action response
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(
        action_id=action_id, json_result={"var_args": ["arg1", "arg2", 123]}
    ).model_dump(mode="json")

    mock_post.side_effect = [create_response, start_response]

    # Create action request with var_args
    action_request = ActionRequest(
        action_name="test_var_args",
        args={"required_param": "value"},
        var_args=["arg1", "arg2", 123],
    )

    result = rest_node_client.send_action(action_request, await_result=False)

    # Verify the result
    assert isinstance(result, ActionResult)
    assert result.action_id == action_id
    assert result.status == ActionStatus.SUCCEEDED
    assert result.json_result["var_args"] == ["arg1", "arg2", 123]

    # Verify the calls
    assert mock_post.call_count == 2

    # Check that var_args was included in the request payload
    create_call_kwargs = mock_post.call_args_list[0][1]
    request_data = create_call_kwargs["json"]
    assert request_data["var_args"] == ["arg1", "arg2", 123]


@patch("requests.post")
def test_send_action_with_var_kwargs(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test sending an action request with variable keyword arguments (**kwargs)."""
    action_id = new_ulid_str()

    # Mock create action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock start action response
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(
        action_id=action_id,
        json_result={"var_kwargs": {"extra1": "value1", "extra2": 42}},
    ).model_dump(mode="json")

    mock_post.side_effect = [create_response, start_response]

    # Create action request with var_kwargs
    action_request = ActionRequest(
        action_name="test_var_kwargs",
        args={"required_param": "value"},
        var_kwargs={"extra1": "value1", "extra2": 42},
    )

    result = rest_node_client.send_action(action_request, await_result=False)

    # Verify the result
    assert isinstance(result, ActionResult)
    assert result.action_id == action_id
    assert result.status == ActionStatus.SUCCEEDED
    assert result.json_result["var_kwargs"] == {"extra1": "value1", "extra2": 42}

    # Verify the calls
    assert mock_post.call_count == 2

    # Check that var_kwargs was included in the request payload
    create_call_kwargs = mock_post.call_args_list[0][1]
    request_data = create_call_kwargs["json"]
    assert request_data["var_kwargs"] == {"extra1": "value1", "extra2": 42}


@patch("requests.post")
def test_send_action_with_var_args_and_kwargs(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test sending an action request with both *args and **kwargs."""
    action_id = new_ulid_str()

    # Mock create action response
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    # Mock start action response
    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(
        action_id=action_id,
        json_result={"var_args": ["arg1", "arg2"], "var_kwargs": {"extra1": "value1"}},
    ).model_dump(mode="json")

    mock_post.side_effect = [create_response, start_response]

    # Create action request with both var_args and var_kwargs
    action_request = ActionRequest(
        action_name="test_both_var",
        args={"required_param": "value"},
        var_args=["arg1", "arg2"],
        var_kwargs={"extra1": "value1"},
    )

    result = rest_node_client.send_action(action_request, await_result=False)

    # Verify the result
    assert isinstance(result, ActionResult)
    assert result.action_id == action_id
    assert result.status == ActionStatus.SUCCEEDED
    assert result.json_result["var_args"] == ["arg1", "arg2"]
    assert result.json_result["var_kwargs"] == {"extra1": "value1"}

    # Verify the calls
    assert mock_post.call_count == 2

    # Check that both var_args and var_kwargs were included in the request payload
    create_call_kwargs = mock_post.call_args_list[0][1]
    request_data = create_call_kwargs["json"]
    assert request_data["var_args"] == ["arg1", "arg2"]
    assert request_data["var_kwargs"] == {"extra1": "value1"}


@patch("requests.post")
def test_send_action_with_files_and_var_kwargs(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test sending an action request that combines file uploads with **kwargs."""
    action_id = new_ulid_str()

    # Create temporary files
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("test content")
        test_file = Path(f.name)

    # Mock responses
    create_response = MagicMock()
    create_response.ok = True
    create_response.json.return_value = {"action_id": action_id}

    upload_response = MagicMock()
    upload_response.ok = True

    start_response = MagicMock()
    start_response.ok = True
    start_response.json.return_value = ActionSucceeded(
        action_id=action_id,
        json_result={
            "file_processed": True,
            "var_kwargs": {"processing_mode": "fast", "quality": "high"},
        },
    ).model_dump(mode="json")

    mock_post.side_effect = [create_response, upload_response, start_response]

    # Create action request with files and var_kwargs
    action_request = ActionRequest(
        action_name="test_files_with_kwargs",
        args={"required_param": "value"},
        files={"input_file": test_file},
        var_kwargs={"processing_mode": "fast", "quality": "high"},
    )

    result = rest_node_client.send_action(action_request, await_result=False)

    # Verify the result
    assert isinstance(result, ActionResult)
    assert result.action_id == action_id
    assert result.status == ActionStatus.SUCCEEDED
    assert result.json_result["var_kwargs"] == {
        "processing_mode": "fast",
        "quality": "high",
    }

    # Verify all three calls were made (create, upload, start)
    assert mock_post.call_count == 3

    # Check that var_kwargs was included in the create request payload
    create_call_kwargs = mock_post.call_args_list[0][1]
    request_data = create_call_kwargs["json"]
    assert request_data["var_kwargs"] == {"processing_mode": "fast", "quality": "high"}

    # Clean up
    test_file.unlink()
