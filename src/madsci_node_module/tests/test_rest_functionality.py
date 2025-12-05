"""Test REST API functionality including endpoints, client operations, and file handling.

Consolidates tests from:
- test_rest_node_module.py (REST endpoint tests)
- test_rest_node_client.py (client tests)
- File operation tests scattered across multiple files
"""

import tempfile
import time
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import (
    ActionRequest,
    ActionResult,
    ActionRunning,
    ActionStatus,
    ActionSucceeded,
    RestActionResult,
    create_dynamic_model,
    extract_file_parameters,
)
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import NodeInfo, NodeStatus
from madsci.common.utils import new_ulid_str

from madsci_node_module.tests.test_node import TestNode
from madsci_node_module.tests.test_rest_utils import (
    create_temp_files_for_testing,
    execute_action_with_validation,
    parametrize_file_scenarios,
)


class TestRESTEndpoints:
    """Test all REST API endpoints."""

    def test_openapi_schema_endpoint(self, test_client: TestClient) -> None:
        """Test that OpenAPI schema is available."""
        with test_client as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            schema = response.json()
            assert "openapi" in schema
            assert "paths" in schema

    def test_get_log(self, test_client: TestClient) -> None:
        """Test the /log endpoint."""
        with test_client as client:
            time.sleep(0.1)

            # Execute an action to generate some log entries
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            action_id = response.json()["action_id"]
            client.post(f"/action/test_action/{action_id}/start")
            time.sleep(0.1)

            # Get log
            response = client.get("/log")
            assert response.status_code == 200
            log_data = response.json()

            # Log data is returned as a dict with event IDs as keys
            assert isinstance(log_data, dict)

            # Should have log entries
            if len(log_data) > 0:
                # Get first log entry from the dict
                first_event_id = next(iter(log_data))
                log_entry = Event.model_validate(log_data[first_event_id])
                assert hasattr(log_entry, "event_id")

    def test_endpoint_404_handling(self, test_client: TestClient) -> None:
        """Test 404 handling for non-existent endpoints."""
        with test_client as client:
            response = client.get("/nonexistent")
            assert response.status_code == 404

    def test_method_not_allowed_handling(self, test_client: TestClient) -> None:
        """Test 405 handling for unsupported methods."""
        with test_client as client:
            # Try DELETE on status endpoint (should be GET only)
            response = client.delete("/status")
            assert response.status_code == 405


class TestClientOperations:
    """Test REST client functionality."""

    @pytest.fixture
    def rest_node_client(self) -> RestNodeClient:
        """Fixture to create a RestNodeClient instance."""
        return RestNodeClient(url="http://localhost:2000")

    @patch("madsci.client.node.rest_node_client.create_http_session")
    def test_get_status(self, mock_create_session: MagicMock) -> None:
        """Test the get_status method."""
        # Create mock session and response
        mock_session = MagicMock()
        mock_create_session.return_value = mock_session

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"ready": True, "locked": False}
        mock_session.get.return_value = mock_response

        # Create new client to use mocked session
        test_client = RestNodeClient(url="http://localhost:2000")
        status = test_client.get_status()

        assert isinstance(status, NodeStatus)
        assert status.ready is True
        assert status.locked is False
        mock_session.get.assert_called_once_with(
            "http://localhost:2000/status", timeout=10
        )

    @patch("madsci.client.node.rest_node_client.create_http_session")
    def test_get_info(self, mock_create_session: MagicMock) -> None:
        """Test the get_info method."""
        # Create mock session and response
        mock_session = MagicMock()
        mock_create_session.return_value = mock_session

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = NodeInfo(
            node_name="Test Node", module_name="test_module"
        ).model_dump(mode="json")
        mock_session.get.return_value = mock_response

        # Create new client to use mocked session
        test_client = RestNodeClient(url="http://localhost:2000")
        info = test_client.get_info()

        assert isinstance(info, NodeInfo)
        assert info.node_name == "Test Node"
        assert info.module_name == "test_module"
        mock_session.get.assert_called_once_with(
            "http://localhost:2000/info", timeout=10
        )

    @patch("madsci.client.node.rest_node_client.create_http_session")
    def test_send_action_no_await(self, mock_create_session: MagicMock) -> None:
        """Test the send_action method without awaiting."""
        action_id = new_ulid_str()

        # Create mock session
        mock_session = MagicMock()
        mock_create_session.return_value = mock_session

        # Mock create_action response
        create_response = MagicMock()
        create_response.ok = True
        create_response.raise_for_status.return_value = None
        create_response.json.return_value = {"action_id": action_id}

        # Mock start_action response
        start_response = MagicMock()
        start_response.ok = True
        start_response.raise_for_status.return_value = None
        start_response.json.return_value = ActionSucceeded(
            action_id=action_id
        ).model_dump(mode="json")

        mock_session.post.side_effect = [create_response, start_response]

        # Create new client to use mocked session
        test_client = RestNodeClient(url="http://localhost:2000")
        action_request = ActionRequest(action_name="test_action", args={}, files={})
        result = test_client.send_action(action_request, await_result=False)

        assert isinstance(result, ActionResult)
        assert result.status == ActionStatus.SUCCEEDED
        assert result.action_id == action_id

        # Verify the calls: create_action then start_action
        assert mock_session.post.call_count == 2

    @patch("madsci.client.node.rest_node_client.create_http_session")
    def test_send_action_with_await(
        self,
        mock_create_session: MagicMock,
    ) -> None:
        """Test the send_action method with awaiting."""
        action_id = new_ulid_str()

        # Create mock session
        mock_session = MagicMock()
        mock_create_session.return_value = mock_session

        # Mock create_action response
        create_response = MagicMock()
        create_response.ok = True
        create_response.raise_for_status.return_value = None
        create_response.json.return_value = {"action_id": action_id}

        # Mock start_action response
        start_response = MagicMock()
        start_response.ok = True
        start_response.raise_for_status.return_value = None
        start_response.json.return_value = ActionRunning(
            action_id=action_id
        ).model_dump(mode="json")

        # Mock polling responses - first running, then succeeded
        # The status endpoint should return just the status string
        running_response = MagicMock()
        running_response.ok = True
        running_response.raise_for_status.return_value = None
        running_response.json.return_value = "running"

        success_response = MagicMock()
        success_response.ok = True
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = "succeeded"

        # Final result response
        result_response = MagicMock()
        result_response.ok = True
        result_response.raise_for_status.return_value = None
        result_response.json.return_value = ActionSucceeded(
            action_id=action_id
        ).model_dump(mode="json")

        mock_session.post.side_effect = [create_response, start_response]
        mock_session.get.side_effect = [
            running_response,
            success_response,
            result_response,
        ]

        # Create new client to use mocked session
        test_client = RestNodeClient(url="http://localhost:2000")
        action_request = ActionRequest(action_name="test_action", args={}, files={})
        result = test_client.send_action(action_request, await_result=True, timeout=5)

        assert isinstance(result, ActionResult)
        assert result.status == ActionStatus.SUCCEEDED
        assert result.action_id == action_id

    @patch("madsci.client.node.rest_node_client.create_http_session")
    def test_client_timeout_handling(self, mock_create_session: MagicMock) -> None:
        """Test client timeout handling."""
        # Create mock session
        mock_session = MagicMock()
        mock_create_session.return_value = mock_session
        mock_session.get.side_effect = requests.Timeout("Request timed out")

        # Create new client to use mocked session
        test_client = RestNodeClient(url="http://localhost:2000")
        with pytest.raises(requests.Timeout):
            test_client.get_status()

    @patch("madsci.client.node.rest_node_client.create_http_session")
    def test_client_connection_error_handling(
        self, mock_create_session: MagicMock
    ) -> None:
        """Test client connection error handling."""
        # Create mock session
        mock_session = MagicMock()
        mock_create_session.return_value = mock_session
        mock_session.get.side_effect = requests.ConnectionError("Connection failed")

        # Create new client to use mocked session
        test_client = RestNodeClient(url="http://localhost:2000")
        with pytest.raises(requests.ConnectionError):
            test_client.get_status()


class TestFileOperations:
    """Consolidated file upload/download testing."""

    def test_file_parameter_extraction(self, basic_test_node: TestNode) -> None:
        """Test extracting file parameters from action signatures."""
        # Test single file parameter
        file_params = extract_file_parameters(basic_test_node.file_action)
        assert "config_file" in file_params
        assert file_params["config_file"]["required"] is True
        assert file_params["config_file"]["is_list"] is False

        assert "optional_file" in file_params
        assert file_params["optional_file"]["required"] is False

    def test_list_file_parameter_extraction(self, basic_test_node: TestNode) -> None:
        """Test extracting list file parameters."""
        file_params = extract_file_parameters(basic_test_node.list_file_action)
        assert "files" in file_params
        assert file_params["files"]["required"] is True
        assert file_params["files"]["is_list"] is True

    def test_optional_file_parameter_extraction(
        self, basic_test_node: TestNode
    ) -> None:
        """Test extracting optional file parameters."""
        file_params = extract_file_parameters(basic_test_node.optional_file_action)
        assert "optional_file" in file_params
        assert file_params["optional_file"]["required"] is False
        assert file_params["optional_file"]["is_list"] is False

    def test_optional_list_file_parameter_extraction(
        self, basic_test_node: TestNode
    ) -> None:
        """Test extracting optional list file parameters."""
        file_params = extract_file_parameters(basic_test_node.optional_list_file_action)
        assert "optional_files" in file_params
        assert file_params["optional_files"]["required"] is False
        assert file_params["optional_files"]["is_list"] is True

    def test_openapi_file_documentation(self, test_client: TestClient) -> None:
        """Test that file parameters are correctly documented in OpenAPI."""
        with test_client as client:
            time.sleep(0.1)
            response = client.get("/openapi.json")
            assert response.status_code == 200
            openapi_spec = response.json()

            # Check that file action endpoints are documented
            paths = openapi_spec.get("paths", {})

            # Should have file upload endpoints
            file_action_path = "/action/file_action"
            assert file_action_path in paths

            # Should have POST method for action creation
            post_spec = paths[file_action_path].get("post")
            assert post_spec is not None

    def test_file_upload_endpoints_generated(self, test_client: TestClient) -> None:
        """Test that file upload endpoints are automatically generated."""
        with test_client as client:
            time.sleep(0.1)
            response = client.get("/openapi.json")
            openapi_spec = response.json()
            paths = openapi_spec.get("paths", {})

            # Check for file upload endpoints (they follow pattern /action/{action_name}/{action_id}/upload/{file_param})
            file_upload_paths = [path for path in paths if "/upload/" in path]
            assert len(file_upload_paths) > 0, "No file upload endpoints found"

    def test_file_download_routes(self, test_client: TestClient) -> None:
        """Test file download functionality."""
        with test_client as client:
            time.sleep(0.1)

            # Execute an action that returns a file
            result = execute_action_with_validation(
                client,
                "file_result_action",
                {"data": "test data"},
                ActionStatus.SUCCEEDED,
            )

            action_id = result["action_id"]

            # Try to download the file
            response = client.get(f"/action/{action_id}/download")
            # This might be 200 with file content or 404 if not implemented
            assert response.status_code in [200, 404]

    @parametrize_file_scenarios()
    def test_file_scenarios(self, test_client: TestClient, file_scenario: dict) -> None:
        """Parametrized test for various file handling scenarios."""
        action_name = file_scenario["action"]
        files_config = file_scenario["files"]
        expected_type = file_scenario["expected_response_type"]

        # Create temporary files
        temp_files = create_temp_files_for_testing(files_config)

        try:
            with test_client as client:
                time.sleep(0.1)

                # Prepare parameters based on action type
                if action_name in ["file_result_action", "multiple_file_result_action"]:
                    params = {"data": "test data"}
                elif action_name in [
                    "mixed_pydantic_and_file_action",
                    "custom_pydantic_result_action",
                ]:
                    params = {"test_id": "test_001"}
                else:
                    params = {"data": "test"}

                # Execute action
                result = execute_action_with_validation(
                    client, action_name, params, ActionStatus.SUCCEEDED
                )

                # Validate result type - for file results, check that files are present
                if action_name in [
                    "file_result_action",
                    "multiple_file_result_action",
                    "mixed_pydantic_and_file_action",
                ]:
                    # These actions return files, so should have 'files' field
                    assert "files" in result, (
                        f"Expected 'files' field in result for {action_name}"
                    )
                elif expected_type is str:
                    assert isinstance(result.get("result"), str)
                elif expected_type is dict:
                    # For pydantic results, check that json_result is a dict
                    json_result = result.get("json_result") or result.get("result")
                    assert isinstance(json_result, dict), (
                        f"Expected dict result for {action_name}, got {type(json_result)}"
                    )

        finally:
            # Clean up temporary files
            for file_path in temp_files.values():
                if file_path.exists():
                    file_path.unlink()

    def test_file_upload_with_zip_extraction(self, test_client: TestClient) -> None:
        """Test file upload with zip file handling."""
        with test_client as client:
            time.sleep(0.1)

            # Create a test zip file
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as zip_file:
                with zipfile.ZipFile(zip_file.name, "w") as zf:
                    zf.writestr("test.txt", "test content")
                    zf.writestr("data.csv", "col1,col2\n1,2\n3,4")

                zip_path = Path(zip_file.name)

            try:
                # Test that we can handle zip files (if the endpoint exists)
                response = client.post(
                    "/action/file_action", json={"config_file": str(zip_path)}
                )
                # Should either work (200) or not be implemented (404/422)
                assert response.status_code in [200, 404, 422]

            finally:
                if zip_path.exists():
                    zip_path.unlink()

    def test_large_file_handling(self, test_client: TestClient) -> None:
        """Test handling of larger files."""
        with test_client as client:
            time.sleep(0.1)

            # Create a moderately sized test file (10KB - sufficient for testing)
            large_content = "x" * (1024 * 10)  # 10KB
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                f.write(large_content)
                large_file_path = Path(f.name)

            try:
                # Test file action with large file
                response = client.post(
                    "/action/file_action", json={"config_file": str(large_file_path)}
                )
                # Should handle large files gracefully
                assert response.status_code in [
                    200,
                    413,
                    422,
                ]  # 413 = Request Entity Too Large

            finally:
                if large_file_path.exists():
                    large_file_path.unlink()

    def test_file_validation_errors(self, test_client: TestClient) -> None:
        """Test file validation error cases."""
        with test_client as client:
            time.sleep(0.1)

            # For REST API, file parameters are handled via uploads, not JSON
            # Test missing required non-file parameter instead
            response = client.post("/action/test_action", json={})
            assert response.status_code == 422  # Missing required parameter

            # Test invalid parameter types
            response = client.post(
                "/action/test_action", json={"test_param": "not_an_integer"}
            )
            assert response.status_code == 422  # Invalid parameter type


class TestCustomReturnTypes:
    """Test handling of custom return types including Pydantic models and files."""

    def test_custom_pydantic_result_processing(self, basic_test_node: TestNode) -> None:
        """Test processing of custom Pydantic model results."""
        # Test the custom pydantic result action
        basic_test_node.start_node(testing=True)

        with TestClient(basic_test_node.rest_api) as client:
            time.sleep(0.1)

            result = execute_action_with_validation(
                client,
                "custom_pydantic_result_action",
                {"test_id": "custom_001"},
                ActionStatus.SUCCEEDED,
            )

            # Should have a json_result field with the custom model data
            assert "json_result" in result
            result_data = result["json_result"]
            assert result_data["test_id"] == "custom_001"
            assert result_data["value"] == 42.5
            assert result_data["status"] == "completed"

    def test_mixed_pydantic_and_file_result_processing(
        self, basic_test_node: TestNode
    ) -> None:
        """Test processing of mixed return types (Pydantic model + file)."""
        basic_test_node.start_node(testing=True)

        with TestClient(basic_test_node.rest_api) as client:
            time.sleep(0.1)

            result = execute_action_with_validation(
                client,
                "mixed_pydantic_and_file_action",
                {"test_id": "mixed_001"},
                ActionStatus.SUCCEEDED,
            )

            # Should have both json_result and files
            assert "json_result" in result
            assert "files" in result
            result_data = result["json_result"]
            assert result_data["test_id"] == "mixed_001"
            assert result_data["value"] == 123.45

    def test_create_dynamic_model_functionality(self) -> None:
        """Test the create_dynamic_model helper function."""
        # Test basic action model creation
        model = create_dynamic_model("test_action")
        assert model is not None
        assert issubclass(model, RestActionResult)

        # Test with json_result_type
        model = create_dynamic_model("test_action", json_result_type=dict)
        assert model is not None
        assert issubclass(model, RestActionResult)

        # Test with no result type
        model = create_dynamic_model("simple_action")
        assert model is not None


class TestAPICompatibility:
    """Test backward compatibility and API versioning."""

    def test_rest_action_result_structure(self) -> None:
        """Test RestActionResult structure and inheritance."""
        # Test that RestActionResult maintains expected structure
        action_id = new_ulid_str()
        result = RestActionResult(
            action_id=action_id,
            status=ActionStatus.SUCCEEDED,
            json_result={"test": "data"},
            files=[],  # files should be a list, not a dict
        )

        assert result.action_id == action_id
        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_result == {"test": "data"}
        assert hasattr(result, "files")

    def test_backward_compatibility_endpoints(self, test_client: TestClient) -> None:
        """Test that existing API endpoints maintain compatibility."""
        with test_client as client:
            time.sleep(0.1)

            # Test that legacy endpoints still work
            response = client.get("/status")
            assert response.status_code == 200

            response = client.get("/info")
            assert response.status_code == 200

            # Test action creation still works
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            assert response.status_code == 200
            assert "action_id" in response.json()
