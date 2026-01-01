"""Unit tests for madsci.workcell_manager.workcell_utils module."""

from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

from fastapi import UploadFile
from madsci.client.node import AbstractNodeClient
from madsci.common.types.datapoint_types import FileDataPoint
from madsci.common.types.parameter_types import ParameterInputFile
from madsci.common.types.workflow_types import Workflow, WorkflowParameters
from madsci.workcell_manager.workcell_utils import find_node_client
from madsci.workcell_manager.workflow_utils import save_workflow_files


class MockNodeClient(AbstractNodeClient):
    """Mock node client for testing."""

    def __init__(self, url: str):
        self.url = url

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith("mock://")

    def get_status(self):
        return {"status": "ok"}

    def execute_action(self, action: str, **kwargs):
        return {"result": f"executed {action}"}


class AnotherMockNodeClient(AbstractNodeClient):
    """Another mock node client for testing."""

    def __init__(self, url: str):
        self.url = url

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith("another://")

    def get_status(self):
        return {"status": "ok"}

    def execute_action(self, action: str, **kwargs):
        return {"result": f"executed {action}"}


def test_find_node_client_from_node_client_map():
    """Test finding node client from NODE_CLIENT_MAP."""
    mock_client_class = MagicMock()
    mock_client_class.validate_url.return_value = True
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance

    with patch(
        "madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP",
        {"test": mock_client_class},
    ):
        result = find_node_client("http://test.com")

        assert result == mock_client_instance
        mock_client_class.validate_url.assert_called_once_with("http://test.com")
        mock_client_class.assert_called_once_with("http://test.com")


def test_find_node_client_from_subclasses():
    """Test finding node client from AbstractNodeClient subclasses."""
    # Mock the NODE_CLIENT_MAP to be empty
    with (
        patch("madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP", {}),
        patch.object(
            AbstractNodeClient, "__subclasses__", return_value=[MockNodeClient]
        ),
    ):
        result = find_node_client("mock://test.com")

        assert isinstance(result, MockNodeClient)
        assert result.url == "mock://test.com"


def test_find_node_client_no_match():
    """Test find_node_client returns None when no client matches."""
    # Mock both NODE_CLIENT_MAP and subclasses to be empty/non-matching
    with (
        patch("madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP", {}),
        patch.object(AbstractNodeClient, "__subclasses__", return_value=[]),
    ):
        result = find_node_client("unsupported://test.com")

        assert result is None


def test_find_node_client_multiple_subclasses():
    """Test find_node_client with multiple subclasses."""
    with (
        patch("madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP", {}),
        patch.object(
            AbstractNodeClient,
            "__subclasses__",
            return_value=[MockNodeClient, AnotherMockNodeClient],
        ),
    ):
        # Test first client matches
        result1 = find_node_client("mock://test.com")
        assert isinstance(result1, MockNodeClient)

        # Test second client matches
        result2 = find_node_client("another://test.com")
        assert isinstance(result2, AnotherMockNodeClient)


def test_find_node_client_node_client_map_priority():
    """Test that NODE_CLIENT_MAP takes priority over subclasses."""
    mock_client_from_map = MagicMock()
    mock_client_from_map.validate_url.return_value = True
    mock_instance_from_map = MagicMock()
    mock_client_from_map.return_value = mock_instance_from_map

    with (
        patch(
            "madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP",
            {"priority": mock_client_from_map},
        ),
        patch.object(
            AbstractNodeClient, "__subclasses__", return_value=[MockNodeClient]
        ),
    ):
        result = find_node_client(
            "mock://test.com"
        )  # MockNodeClient would normally handle this

        # Should use the NODE_CLIENT_MAP client instead
        assert result == mock_instance_from_map
        mock_client_from_map.validate_url.assert_called_once()


def test_find_node_client_validation_fails():
    """Test find_node_client when validation fails for all clients."""
    mock_client = MagicMock()
    mock_client.validate_url.return_value = False

    with (
        patch(
            "madsci.workcell_manager.workcell_utils.NODE_CLIENT_MAP",
            {"test": mock_client},
        ),
        patch.object(AbstractNodeClient, "__subclasses__", return_value=[]),
    ):
        result = find_node_client("http://test.com")

        assert result is None
        mock_client.validate_url.assert_called_once_with("http://test.com")


def test_save_workflow_files_flushes_buffer():
    """Test that save_workflow_files properly flushes file buffer before reading.

    This is a regression test for the bug where files were being emptied because
    the buffer wasn't flushed after writing to the temp file, resulting in the
    data_client reading an empty file.
    """
    # Create a mock workflow with a file input parameter
    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            file_inputs=[ParameterInputFile(key="test_file")]
        ),
        file_input_paths={"test_file": "test.txt"},
    )

    # Create test file content
    test_content = b"This is test file content that should not be empty!"
    file_handle = BytesIO(test_content)

    # Create UploadFile with the test content
    upload_file = UploadFile(filename="test_file", file=file_handle)

    # Mock the data_client to capture what file is being submitted
    mock_data_client = Mock()
    submitted_file_contents = []

    def mock_submit_datapoint(datapoint):
        """Mock submit that reads the file to verify its content."""
        if isinstance(datapoint, FileDataPoint):
            file_path = datapoint.path
            # Read the file content to verify it's not empty
            content = file_path.read_bytes()
            submitted_file_contents.append(content)
            # Clean up the temp file
            file_path.unlink(missing_ok=True)

        # Return a mock datapoint with an ID
        mock_result = Mock()
        mock_result.datapoint_id = "mock_datapoint_id_123"
        return mock_result

    mock_data_client.submit_datapoint = mock_submit_datapoint

    # Call the function
    result = save_workflow_files(workflow, [upload_file], mock_data_client)

    # Verify that the file was submitted with non-empty content
    assert len(submitted_file_contents) == 1, "Expected one file to be submitted"
    assert len(submitted_file_contents[0]) == len(test_content), (
        f"File content should be {len(test_content)} bytes, but got {len(submitted_file_contents[0])} bytes"
    )
    assert submitted_file_contents[0] == test_content, (
        "File content does not match expected content"
    )

    # Verify that the workflow was updated with the file input ID
    assert "test_file" in result.file_input_ids
    assert result.file_input_ids["test_file"] == "mock_datapoint_id_123"


def test_save_workflow_files_with_multiple_files():
    """Test that save_workflow_files correctly handles multiple file inputs."""
    # Create a mock workflow with multiple file input parameters
    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            file_inputs=[
                ParameterInputFile(key="file1"),
                ParameterInputFile(key="file2"),
                ParameterInputFile(key="file3"),
            ]
        ),
        file_input_paths={
            "file1": "test1.txt",
            "file2": "test2.csv",
            "file3": "test3.json",
        },
    )

    # Create test files with different content
    files = []
    expected_contents = {}
    for i in range(1, 4):
        content = f"Content of file {i} - some test data here!".encode()
        expected_contents[f"file{i}"] = content
        file_handle = BytesIO(content)
        upload_file = UploadFile(filename=f"file{i}", file=file_handle)
        files.append(upload_file)

    # Mock the data_client
    mock_data_client = Mock()
    submitted_files = {}

    def mock_submit_datapoint(datapoint):
        if isinstance(datapoint, FileDataPoint):
            file_path = datapoint.path
            content = file_path.read_bytes()
            submitted_files[datapoint.label] = content
            file_path.unlink(missing_ok=True)

        mock_result = Mock()
        mock_result.datapoint_id = f"mock_id_{datapoint.label}"
        return mock_result

    mock_data_client.submit_datapoint = mock_submit_datapoint

    # Call the function
    result = save_workflow_files(workflow, files, mock_data_client)

    # Verify all files were submitted with correct content
    assert len(submitted_files) == 3, "Expected three files to be submitted"
    for file_key, expected_content in expected_contents.items():
        assert file_key in submitted_files, f"File {file_key} was not submitted"
        assert submitted_files[file_key] == expected_content, (
            f"Content mismatch for {file_key}"
        )
        assert file_key in result.file_input_ids, (
            f"File {file_key} not in file_input_ids"
        )
        assert result.file_input_ids[file_key] == f"mock_id_{file_key}"
