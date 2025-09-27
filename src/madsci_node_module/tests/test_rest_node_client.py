"""Comprehensive unit tests for the RestNodeClient class."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from zipfile import ZipFile

import pytest
import requests
from madsci.client.node.rest_node_client import (
    RestNodeClient,
    action_response_from_headers,
    process_file_response,
)
from madsci.common.types.action_types import (
    ActionFiles,
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
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = ActionSucceeded().model_dump(mode="json")
    mock_post.return_value = mock_response

    action_request = ActionRequest(action_name="test_action", args={}, files={})
    result = rest_node_client.send_action(action_request, await_result=False)
    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == mock_response.json.return_value["action_id"]
    mock_post.assert_called_once_with(
        "http://localhost:2000/action/test_action",
        params={
            "action_name": "test_action",
            "args": json.dumps({}),
            "action_id": action_request.action_id,
        },
        files=[],
        timeout=60,
    )


@patch("requests.post")
@patch("requests.get")
def test_send_action_await(
    mock_get: MagicMock, mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test the send_action method with awaiting."""
    mock_post_response = MagicMock()
    mock_post_response.ok = True
    mock_post_response.json.return_value = ActionRunning().model_dump(mode="json")
    mock_post.return_value = mock_post_response
    mock_get_response = MagicMock()
    mock_get_response.ok = True
    mock_get_response.json.return_value = ActionSucceeded(
        action_id=mock_post_response.json.return_value["action_id"]
    ).model_dump(mode="json")
    mock_get.return_value = mock_get_response

    action_request = ActionRequest(action_name="test_action", args={}, files={})
    result = rest_node_client.send_action(action_request)
    assert isinstance(result, ActionResult)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == mock_post_response.json.return_value["action_id"]
    mock_post.assert_called_once_with(
        "http://localhost:2000/action/test_action",
        params={
            "action_name": "test_action",
            "args": json.dumps({}),
            "action_id": action_request.action_id,
        },
        files=[],
        timeout=60,
    )
    mock_get.assert_called_with(
        f"http://localhost:2000/action/{mock_get_response.json.return_value['action_id']}",
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


# Additional tests for improved coverage


def test_get_resources_not_implemented(rest_node_client: RestNodeClient) -> None:
    """Test that get_resources raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="get_resources is not implemented"):
        rest_node_client.get_resources()


@patch("requests.post")
def test_send_action_http_error(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test send_action method with HTTP error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_post.return_value = mock_response

    action_request = ActionRequest(action_name="test_action", args={}, files={})

    with pytest.raises(requests.HTTPError):
        rest_node_client.send_action(action_request, await_result=False)


@patch("requests.post")
def test_send_action_with_files(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test send_action method with file uploads."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.headers = {}  # No x-madsci-status header
    mock_response.json.return_value = ActionSucceeded().model_dump(mode="json")
    mock_post.return_value = mock_response

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

        # Verify files were passed correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "files" in call_args.kwargs
        assert len(call_args.kwargs["files"]) == 2

    finally:
        # Clean up temporary files
        Path(temp_file1_path).unlink(missing_ok=True)
        Path(temp_file2_path).unlink(missing_ok=True)


@patch("requests.post")
def test_send_action_file_response(
    mock_post: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test send_action method with file response."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.headers = {
        "x-madsci-status": "succeeded",
        "x-madsci-action-id": new_ulid_str(),
        "x-madsci-errors": "[]",
        "x-madsci-files": '{"output.txt": "result.txt"}',
        "x-madsci-datapoints": "{}",
        "x-madsci-data": "{}",
    }
    mock_response.content = b"test file content"
    mock_post.return_value = mock_response

    action_request = ActionRequest(action_name="test_action", args={}, files={})

    with patch(
        "madsci.client.node.rest_node_client.process_file_response"
    ) as mock_process:
        mock_result = ActionResult(
            action_id=mock_response.headers["x-madsci-action-id"],
            status=ActionStatus.SUCCEEDED,
        )
        mock_process.return_value = mock_result

        result = rest_node_client.send_action(action_request, await_result=False)
        assert result == mock_result
        mock_process.assert_called_once_with(mock_response)


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
    mock_response.json.return_value = ActionRunning(action_id=action_id).model_dump(
        mode="json"
    )
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

    # Mock responses: running -> running -> succeeded
    running_response = MagicMock()
    running_response.ok = True
    running_response.headers = {}
    running_response.json.return_value = ActionRunning(action_id=action_id).model_dump(
        mode="json"
    )

    succeeded_response = MagicMock()
    succeeded_response.ok = True
    succeeded_response.headers = {}
    succeeded_response.json.return_value = ActionSucceeded(
        action_id=action_id
    ).model_dump(mode="json")

    mock_get.side_effect = [running_response, running_response, succeeded_response]

    result = rest_node_client.await_action_result(action_id)
    assert result.status == ActionStatus.SUCCEEDED
    assert result.action_id == action_id

    # Verify exponential backoff
    assert mock_sleep.call_count == 2
    # First sleep: 0.25, second sleep: 0.25 * 1.5 = 0.375
    mock_sleep.assert_any_call(0.25)
    mock_sleep.assert_any_call(0.375)


@patch("requests.get")
def test_get_action_result_file_response(
    mock_get: MagicMock, rest_node_client: RestNodeClient
) -> None:
    """Test get_action_result with file response."""
    action_id = new_ulid_str()

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.headers = {
        "x-madsci-status": "succeeded",
        "x-madsci-action-id": action_id,
        "x-madsci-errors": "[]",
        "x-madsci-files": '{"output.txt": "result.txt"}',
        "x-madsci-datapoints": "{}",
        "x-madsci-data": "{}",
    }
    mock_response.content = b"test file content"
    mock_get.return_value = mock_response

    with patch(
        "madsci.client.node.rest_node_client.process_file_response"
    ) as mock_process:
        mock_result = ActionResult(action_id=action_id, status=ActionStatus.SUCCEEDED)
        mock_process.return_value = mock_result

        result = rest_node_client.get_action_result(action_id)
        assert result == mock_result
        mock_process.assert_called_once_with(mock_response)


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


def test_action_response_from_headers():
    """Test action_response_from_headers function."""
    action_id = new_ulid_str()
    headers = {
        "x-madsci-action-id": action_id,
        "x-madsci-status": "succeeded",
        "x-madsci-errors": '["error1", "error2"]',
        "x-madsci-files": '{"output": "result.txt"}',
        "x-madsci-datapoints": '{"temp": {"label": "temp", "data_type": "json", "value": 25.0}}',
        "x-madsci-json_data": '{"key": "value"}',
    }

    result = action_response_from_headers(headers)

    assert result.action_id == action_id
    assert result.status == ActionStatus.SUCCEEDED
    assert len(result.errors) == 2
    assert result.errors[0].message == "error1"
    assert result.errors[1].message == "error2"
    assert result.files.output == Path("result.txt")
    assert result.datapoints.temp.label == "temp"
    assert result.datapoints.temp.value == 25.0
    assert result.json_data == {"key": "value"}


def test_process_file_response_single_file():
    """Test process_file_response with single file."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.headers = {
        "x-madsci-action-id": action_id,
        "x-madsci-status": "succeeded",
        "x-madsci-errors": "[]",
        "x-madsci-files": "result.txt",
        "x-madsci-datapoints": "{}",
        "x-madsci-json_data": "{}",
    }
    mock_response.content = b"test file content"

    with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = "/tmp/test_file.txt"  # noqa: S108

        result = process_file_response(mock_response)

        assert result.action_id == action_id
        assert result.status == ActionStatus.SUCCEEDED
        assert result.files == Path("/tmp/test_file.txt")  # noqa: S108


def test_process_file_response_multiple_files():
    """Test process_file_response with multiple files in zip."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.headers = {
        "x-madsci-action-id": action_id,
        "x-madsci-status": "succeeded",
        "x-madsci-errors": "[]",
        "x-madsci-files": '{"file1": "output1.txt", "file2": "output2.txt"}',
        "x-madsci-datapoints": "{}",
        "x-madsci-json_data": "{}",
    }
    mock_response.content = b"fake zip content"

    # Create a real temporary zip file for testing
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip_file:
        temp_zip_path = Path(temp_zip_file.name)

        # Create a valid zip file with test content
        with ZipFile(temp_zip_path, "w") as zip_file:
            zip_file.writestr("output1.txt", "content1")
            zip_file.writestr("output2.txt", "content2")

    try:
        with patch("tempfile.NamedTemporaryFile") as mock_temp_file:
            # Mock the zip file creation
            mock_zip_temp = MagicMock()
            mock_zip_temp.name = str(temp_zip_path)
            mock_zip_temp.write = MagicMock()

            # Mock individual temp files
            mock_temp1 = MagicMock()
            mock_temp1.name = "/tmp/file1.txt"  # noqa: S108
            mock_temp2 = MagicMock()
            mock_temp2.name = "/tmp/file2.txt"  # noqa: S108

            mock_temp_file.side_effect = [
                MagicMock(
                    __enter__=lambda self: mock_zip_temp,  # noqa: ARG005
                    __exit__=lambda *args: None,  # noqa: ARG005
                ),
                MagicMock(
                    __enter__=lambda self: mock_temp1,  # noqa: ARG005
                    __exit__=lambda *args: None,  # noqa: ARG005
                ),
                MagicMock(
                    __enter__=lambda self: mock_temp2,  # noqa: ARG005
                    __exit__=lambda *args: None,  # noqa: ARG005
                ),
            ]

            result = process_file_response(mock_response)

            assert result.action_id == action_id
            assert result.status == ActionStatus.SUCCEEDED
            assert result.files.file1 == Path("/tmp/file1.txt")  # noqa: S108
            assert result.files.file2 == Path("/tmp/file2.txt")  # noqa: S108
    finally:
        # Clean up
        temp_zip_path.unlink(missing_ok=True)


def test_process_file_response_no_files():
    """Test process_file_response with no files."""
    action_id = new_ulid_str()
    mock_response = MagicMock()
    mock_response.headers = {
        "x-madsci-action-id": action_id,
        "x-madsci-status": "succeeded",
        "x-madsci-errors": "[]",
        "x-madsci-files": "{}",
        "x-madsci-datapoints": "{}",
        "x-madsci-json_data": "{}",
    }
    mock_response.content = b""

    result = process_file_response(mock_response)

    assert result.action_id == action_id
    assert result.status == ActionStatus.SUCCEEDED
    assert result.files == ActionFiles()


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
