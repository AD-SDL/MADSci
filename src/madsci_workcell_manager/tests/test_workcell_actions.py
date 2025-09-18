"""Unit tests for madsci.workcell_manager.workcell_actions module."""

from unittest.mock import MagicMock, Mock, patch

import httpx
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.context_types import MadsciContext
from madsci.workcell_manager.workcell_actions import (
    _execute_transfer,
    transfer_location_contents,
    transfer_resource,
    wait,
    workcell_action_dict,
)


class TestWaitAction:
    """Test cases for the wait action."""

    def test_wait_action_succeeds(self):
        """Test that wait action returns success after sleeping."""
        with patch("time.sleep") as mock_sleep:
            result = wait(5)

            mock_sleep.assert_called_once_with(5)
            assert result.status == ActionStatus.SUCCEEDED


class TestTransferResourceAction:
    """Test cases for the transfer_resource action."""

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_resource_missing_location_server_url(self, mock_context):
        """Test that transfer_resource fails when location server URL is not configured."""
        mock_context.return_value = MadsciContext(
            location_server_url=None, resource_server_url="http://localhost:8003/"
        )

        result = transfer_resource("resource_123", "dest_location")

        assert result.status == ActionStatus.FAILED
        assert "Location server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_resource_missing_resource_server_url(self, mock_context):
        """Test that transfer_resource fails when resource server URL is not configured."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/", resource_server_url=None
        )

        result = transfer_resource("resource_123", "dest_location")

        assert result.status == ActionStatus.FAILED
        assert "Resource server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("httpx.Client")
    def test_transfer_resource_resource_not_found(self, mock_client, mock_context):
        """Test that transfer_resource fails when resource is not found."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            resource_server_url="http://localhost:8003/",
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock resource not found response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_http_client.get.return_value = mock_response

        result = transfer_resource("nonexistent_resource", "dest_location")

        assert result.status == ActionStatus.FAILED
        assert "Resource nonexistent_resource not found" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("httpx.Client")
    def test_transfer_resource_no_parent_container(self, mock_client, mock_context):
        """Test that transfer_resource fails when resource has no parent container."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            resource_server_url="http://localhost:8003/",
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock resource response without parent_id
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource_id": "resource_123",
            "parent_id": None,
        }
        mock_http_client.get.return_value = mock_response

        result = transfer_resource("resource_123", "dest_location")

        assert result.status == ActionStatus.FAILED
        assert "has no parent container" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._execute_transfer")
    @patch("httpx.Client")
    def test_transfer_resource_success_flow(
        self, mock_client, mock_execute, mock_context
    ):
        """Test successful transfer_resource flow."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            resource_server_url="http://localhost:8003/",
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock resource response with parent_id
        resource_response = Mock()
        resource_response.status_code = 200
        resource_response.json.return_value = {
            "resource_id": "resource_123",
            "parent_id": "container_456",
        }

        # Mock locations response
        locations_response = Mock()
        locations_response.status_code = 200
        locations_response.json.return_value = [
            {"location_id": "source_loc", "resource_id": "container_456"},
            {"location_id": "other_loc", "resource_id": "other_container"},
        ]

        mock_http_client.get.side_effect = [resource_response, locations_response]

        # Mock successful transfer execution
        mock_execute.return_value = Mock(status=ActionStatus.SUCCEEDED)

        result = transfer_resource("resource_123", "dest_location")

        assert result.status == ActionStatus.SUCCEEDED
        mock_execute.assert_called_once_with(
            "source_loc", "dest_location", "resource_123", mock_context.return_value
        )

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("httpx.Client")
    def test_transfer_resource_location_not_found(self, mock_client, mock_context):
        """Test that transfer_resource fails when resource location cannot be found."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            resource_server_url="http://localhost:8003/",
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock resource response with parent_id
        resource_response = Mock()
        resource_response.status_code = 200
        resource_response.json.return_value = {
            "resource_id": "resource_123",
            "parent_id": "container_456",
        }

        # Mock locations response without matching container
        locations_response = Mock()
        locations_response.status_code = 200
        locations_response.json.return_value = [
            {"location_id": "other_loc", "resource_id": "other_container"}
        ]

        mock_http_client.get.side_effect = [resource_response, locations_response]

        result = transfer_resource("resource_123", "dest_location")

        assert result.status == ActionStatus.FAILED
        assert "Could not find location containing resource" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("httpx.Client")
    def test_transfer_resource_connection_error(self, mock_client, mock_context):
        """Test that transfer_resource handles connection errors gracefully."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            resource_server_url="http://localhost:8003/",
        )

        # Mock connection error
        mock_client.return_value.__enter__.side_effect = httpx.RequestError(
            "Connection failed"
        )

        result = transfer_resource("resource_123", "dest_location")

        assert result.status == ActionStatus.FAILED
        assert "Failed to connect to resource manager" in result.errors[0].message


class TestTransferLocationContentsAction:
    """Test cases for the transfer_location_contents action."""

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_location_contents_missing_location_server_url(self, mock_context):
        """Test that transfer_location_contents fails when location server URL is not configured."""
        mock_context.return_value = MadsciContext(location_server_url=None)

        result = transfer_location_contents("source_loc", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Location server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("httpx.Client")
    def test_transfer_location_contents_source_not_found(
        self, mock_client, mock_context
    ):
        """Test that transfer_location_contents fails when source location is not found."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/"
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock location not found response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_http_client.get.return_value = mock_response

        result = transfer_location_contents("nonexistent_location", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert (
            "Source location nonexistent_location not found" in result.errors[0].message
        )

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("httpx.Client")
    def test_transfer_location_contents_empty_location(self, mock_client, mock_context):
        """Test that transfer_location_contents succeeds when source location is empty."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/"
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock empty resources response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_http_client.get.return_value = mock_response

        result = transfer_location_contents("empty_location", "dest_loc")

        assert result.status == ActionStatus.SUCCEEDED
        assert "No resources found" in result.data["message"]

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._execute_transfer")
    @patch("httpx.Client")
    def test_transfer_location_contents_success_flow(
        self, mock_client, mock_execute, mock_context
    ):
        """Test successful transfer_location_contents flow."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/"
        )

        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock resources response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["resource_1", "resource_2"]
        mock_http_client.get.return_value = mock_response

        # Mock successful transfer execution
        mock_execute.return_value = Mock(status=ActionStatus.SUCCEEDED)

        result = transfer_location_contents("source_loc", "dest_loc")

        assert result.status == ActionStatus.SUCCEEDED
        mock_execute.assert_called_once_with(
            "source_loc", "dest_loc", None, mock_context.return_value
        )


class TestExecuteTransfer:
    """Test cases for the _execute_transfer helper function."""

    @patch("httpx.Client")
    def test_execute_transfer_no_path_exists(self, mock_client):
        """Test that _execute_transfer fails when no transfer path exists."""
        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock no path response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_http_client.post.return_value = mock_response

        mock_context = MadsciContext(location_server_url="http://localhost:8006/")

        result = _execute_transfer(
            "source_loc", "dest_loc", "resource_123", mock_context
        )

        assert result.status == ActionStatus.FAILED
        assert "No transfer path exists" in result.errors[0].message

    @patch("httpx.Client")
    def test_execute_transfer_success(self, mock_client):
        """Test successful _execute_transfer execution."""
        # Mock the HTTP client
        mock_http_client = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_http_client

        # Mock successful transfer plan response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"workflow": "transfer_workflow_definition"}
        mock_http_client.post.return_value = mock_response

        mock_context = MadsciContext(location_server_url="http://localhost:8006/")

        result = _execute_transfer(
            "source_loc", "dest_loc", "resource_123", mock_context
        )

        assert result.status == ActionStatus.SUCCEEDED
        assert "Transfer planned" in result.data["message"]
        assert result.data["resource_id"] == "resource_123"
        assert "workflow_definition" in result.data

    @patch("httpx.Client")
    def test_execute_transfer_connection_error(self, mock_client):
        """Test that _execute_transfer handles connection errors gracefully."""
        # Mock connection error
        mock_client.return_value.__enter__.side_effect = httpx.RequestError(
            "Connection failed"
        )

        mock_context = MadsciContext(location_server_url="http://localhost:8006/")

        result = _execute_transfer(
            "source_loc", "dest_loc", "resource_123", mock_context
        )

        assert result.status == ActionStatus.FAILED
        assert "Failed to connect to location manager" in result.errors[0].message


class TestWorkcellActionDict:
    """Test cases for the workcell_action_dict."""

    def test_workcell_action_dict_contains_all_actions(self):
        """Test that workcell_action_dict contains all expected actions."""
        expected_actions = ["wait", "transfer_resource", "transfer_location_contents"]

        for action in expected_actions:
            assert action in workcell_action_dict
            assert callable(workcell_action_dict[action])

    def test_workcell_action_dict_functions_are_correct(self):
        """Test that workcell_action_dict maps to the correct functions."""
        assert workcell_action_dict["wait"] == wait
        assert workcell_action_dict["transfer_resource"] == transfer_resource
        assert (
            workcell_action_dict["transfer_location_contents"]
            == transfer_location_contents
        )
