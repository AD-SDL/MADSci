"""Unit tests for madsci.workcell_manager.workcell_actions module."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from madsci.common.exceptions import LocationNotFoundError
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.workcell_manager.workcell_actions import (
    _find_resource_and_transfer,
    _resolve_location_identifier,
    transfer,
    transfer_resource,
    wait,
)


class TestWaitAction:
    """Test cases for the wait action."""

    def test_wait_action_succeeds(self):
        """Test that wait action returns success after sleeping."""
        with patch("time.sleep") as mock_sleep:
            result = wait(5)

            mock_sleep.assert_called_once_with(5)
            assert result.status == ActionStatus.SUCCEEDED


class TestTransferAction:
    """Test cases for the simplified transfer action."""

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_missing_location_server_url(self, mock_context):
        """Test that transfer fails when location server URL is not configured."""
        mock_context.return_value = MadsciContext(location_server_url=None)

        result = transfer("source_loc", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Location server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_missing_workcell_server_url(self, mock_context):
        """Test that transfer fails when workcell server URL is not configured."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/", workcell_server_url=None
        )

        result = transfer("source_loc", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Workcell server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    def test_transfer_source_location_not_found(
        self, mock_location_client, mock_context
    ):
        """Test that transfer fails when source location is not found."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client
        mock_client_instance = MagicMock()
        mock_location_client.return_value = mock_client_instance

        # Mock _resolve_location_identifier to raise exception for source
        with patch(
            "madsci.workcell_manager.workcell_actions._resolve_location_identifier"
        ) as mock_resolve:
            mock_resolve.side_effect = LocationNotFoundError(
                "Location 'nonexistent' not found by ID or name"
            )

            result = transfer("nonexistent", "dest_loc")

            assert result.status == ActionStatus.FAILED
            assert "Unexpected error in transfer" in result.errors[0].message
            assert "not found by ID or name" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    def test_transfer_no_path_exists(self, mock_location_client, mock_context):
        """Test that transfer fails when no transfer path exists."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client
        mock_client_instance = MagicMock()
        mock_location_client.return_value = mock_client_instance

        # Mock successful location resolution
        with patch(
            "madsci.workcell_manager.workcell_actions._resolve_location_identifier"
        ) as mock_resolve:
            mock_resolve.side_effect = ["source_id", "dest_id"]

            # Mock plan_transfer to raise exception (no path)
            mock_client_instance.plan_transfer.side_effect = Exception(
                "No transfer path exists between source_loc and dest_loc"
            )

            result = transfer("source_loc", "dest_loc")

            assert result.status == ActionStatus.FAILED
            assert "Unexpected error in transfer" in result.errors[0].message
            assert "No transfer path exists" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.WorkcellClient")
    def test_transfer_success(
        self, mock_workcell_client, mock_location_client, mock_context
    ):
        """Test successful transfer action."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client
        mock_location_instance = MagicMock()
        mock_location_client.return_value = mock_location_instance

        # Mock workcell client
        mock_workcell_instance = MagicMock()
        mock_workcell_client.return_value = mock_workcell_instance

        # Mock successful location resolution
        with patch(
            "madsci.workcell_manager.workcell_actions._resolve_location_identifier"
        ) as mock_resolve:
            mock_resolve.side_effect = ["source_id", "dest_id"]

            # Mock successful transfer planning
            mock_workflow_def = {"name": "test_transfer", "steps": []}
            mock_location_instance.plan_transfer.return_value = mock_workflow_def

            # Mock successful workflow execution
            mock_workflow = MagicMock()
            mock_workflow.workflow_id = "test_workflow_123"
            mock_workflow.status.completed = True
            mock_workflow.status.workflow_runtime = 5.0
            mock_workcell_instance.start_workflow.return_value = mock_workflow

            result = transfer("source_loc", "dest_loc")

            assert result.status == ActionStatus.SUCCEEDED
            assert "Transfer completed" in result.json_data["message"]
            assert result.json_data["source_location_id"] == "source_id"
            assert result.json_data["target_location_id"] == "dest_id"
            assert result.json_data["workflow_id"] == "test_workflow_123"

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.WorkcellClient")
    def test_transfer_workflow_failed(
        self, mock_workcell_client, mock_location_client, mock_context
    ):
        """Test transfer action when workflow execution fails."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client
        mock_location_instance = MagicMock()
        mock_location_client.return_value = mock_location_instance

        # Mock workcell client
        mock_workcell_instance = MagicMock()
        mock_workcell_client.return_value = mock_workcell_instance

        # Mock successful location resolution
        with patch(
            "madsci.workcell_manager.workcell_actions._resolve_location_identifier"
        ) as mock_resolve:
            mock_resolve.side_effect = ["source_id", "dest_id"]

            # Mock successful transfer planning
            mock_workflow_def = {"name": "test_transfer", "steps": []}
            mock_location_instance.plan_transfer.return_value = mock_workflow_def

            # Mock failed workflow execution
            mock_workflow = MagicMock()
            mock_workflow.workflow_id = "test_workflow_123"
            mock_workflow.status.completed = False
            mock_workflow.status.failed = True
            mock_workflow.status.description = "Robot arm malfunction"
            mock_workflow.status.current_step_index = 2
            mock_workcell_instance.start_workflow.return_value = mock_workflow

            result = transfer("source_loc", "dest_loc")

            assert result.status == ActionStatus.FAILED
            assert "Transfer workflow failed at step 2" in result.errors[0].message
            assert "Robot arm malfunction" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.WorkcellClient")
    def test_transfer_async_execution(
        self, mock_workcell_client, mock_location_client, mock_context
    ):
        """Test transfer action with async execution (await_completion=False)."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client
        mock_location_instance = MagicMock()
        mock_location_client.return_value = mock_location_instance

        # Mock workcell client
        mock_workcell_instance = MagicMock()
        mock_workcell_client.return_value = mock_workcell_instance

        # Mock successful location resolution
        with patch(
            "madsci.workcell_manager.workcell_actions._resolve_location_identifier"
        ) as mock_resolve:
            mock_resolve.side_effect = ["source_id", "dest_id"]

            # Mock successful transfer planning
            mock_workflow_def = {"name": "test_transfer", "steps": []}
            mock_location_instance.plan_transfer.return_value = mock_workflow_def

            # Mock workflow enqueueing (not completed since await_completion=False)
            mock_workflow = MagicMock()
            mock_workflow.workflow_id = "test_workflow_123"
            mock_workcell_instance.start_workflow.return_value = mock_workflow

            result = transfer("source_loc", "dest_loc", await_completion=False)

            assert result.status == ActionStatus.SUCCEEDED
            assert "Transfer workflow enqueued" in result.json_data["message"]
            assert result.json_data["workflow_id"] == "test_workflow_123"

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    def test_transfer_exception_handling(self, mock_location_client, mock_context):
        """Test that transfer handles unexpected exceptions gracefully."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client to raise exception
        mock_location_client.side_effect = Exception("Connection error")

        result = transfer("source_loc", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Unexpected error in transfer" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.WorkcellClient")
    def test_transfer_workflow_failed_exception(
        self, mock_workcell_client, mock_location_client, mock_context
    ):
        """Test transfer action when WorkflowFailedError is raised."""
        from madsci.common.exceptions import WorkflowFailedError  # noqa: PLC0415

        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/",
            workcell_server_url="http://localhost:8005/",
        )

        # Mock location client
        mock_location_instance = MagicMock()
        mock_location_client.return_value = mock_location_instance

        # Mock workcell client to raise WorkflowFailedError
        mock_workcell_instance = MagicMock()
        mock_workcell_client.return_value = mock_workcell_instance

        # Mock successful location resolution
        with patch(
            "madsci.workcell_manager.workcell_actions._resolve_location_identifier"
        ) as mock_resolve:
            mock_resolve.side_effect = ["source_id", "dest_id"]

            # Mock successful transfer planning
            mock_workflow_def = {"name": "test_transfer", "steps": []}
            mock_location_instance.plan_transfer.return_value = mock_workflow_def

            # Mock WorkflowFailedError
            mock_workcell_instance.start_workflow.side_effect = WorkflowFailedError(
                "Step execution failed"
            )

            result = transfer("source_loc", "dest_loc")

            assert result.status == ActionStatus.FAILED
            assert (
                "Transfer workflow failed during execution" in result.errors[0].message
            )
            assert "Step execution failed" in result.errors[0].message


class TestResolveLocationIdentifier:
    """Test cases for the _resolve_location_identifier helper function."""

    def test_resolve_by_id_success(self):
        """Test successful location resolution by ID."""
        mock_client = MagicMock()
        mock_location = Mock()
        mock_location.location_id = "test_id"
        mock_client.get_location.return_value = mock_location

        result = _resolve_location_identifier("test_id", mock_client)

        assert result == "test_id"
        mock_client.get_location.assert_called_once_with("test_id")

    def test_resolve_by_name_success(self):
        """Test successful location resolution by name."""
        mock_client = MagicMock()

        # Mock get_location to fail (not found by ID)
        mock_client.get_location.side_effect = Exception("Not found")

        # Mock get_location_by_name to return matching location
        mock_location = Mock()
        mock_location.location_id = "resolved_id"
        mock_location.location_name = "test_name"
        mock_client.get_location_by_name.return_value = mock_location

        result = _resolve_location_identifier("test_name", mock_client)

        assert result == "resolved_id"

    def test_resolve_not_found(self):
        """Test location resolution failure when location doesn't exist."""
        mock_client = MagicMock()

        # Mock get_location to fail
        mock_client.get_location.side_effect = Exception("Not found")

        # Mock get_location_by_name to fail
        mock_client.get_location_by_name.side_effect = Exception("Not found")

        with pytest.raises(LocationNotFoundError) as exc_info:
            _resolve_location_identifier("nonexistent", mock_client)

        assert "not found by ID or name" in str(exc_info.value)

    def test_resolve_client_error(self):
        """Test location resolution when client throws unexpected error."""
        mock_client = MagicMock()

        # Mock both methods to fail
        mock_client.get_location.side_effect = Exception("Connection error")
        mock_client.get_location_by_name.side_effect = Exception("Connection error")

        with pytest.raises(LocationNotFoundError) as exc_info:
            _resolve_location_identifier("test", mock_client)

        # The function catches exceptions internally and raises "not found" instead of connection error
        assert "not found by ID or name" in str(exc_info.value)


class TestTransferResourceAction:
    """Test cases for the transfer_resource action."""

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_resource_missing_resource_server_url(self, mock_context):
        """Test that transfer_resource fails when resource server URL is not configured."""
        mock_context.return_value = MadsciContext(
            location_server_url="http://localhost:8006/", resource_server_url=None
        )

        result = transfer_resource("resource_123", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Resource server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    def test_transfer_resource_missing_location_server_url(self, mock_context):
        """Test that transfer_resource fails when location server URL is not configured."""
        mock_context.return_value = MadsciContext(
            resource_server_url="http://localhost:8003/", location_server_url=None
        )

        result = transfer_resource("resource_123", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Location server URL not configured" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._find_resource_and_transfer")
    def test_transfer_resource_invalid_resource(
        self, mock_find_and_transfer, mock_context
    ):
        """Test that transfer_resource fails when resource doesn't exist."""
        mock_context.return_value = MadsciContext(
            resource_server_url="http://localhost:8003/",
            location_server_url="http://localhost:8006/",
        )

        # Mock helper function to return error message
        mock_find_and_transfer.return_value = (
            "Failed to verify resource 'invalid_resource': Resource not found"
        )

        result = transfer_resource("invalid_resource", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert "Failed to verify resource" in result.errors[0].message

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._find_resource_and_transfer")
    def test_transfer_resource_not_found_at_location(
        self, mock_find_and_transfer, mock_context
    ):
        """Test that transfer_resource fails when resource is not found at any location."""
        mock_context.return_value = MadsciContext(
            resource_server_url="http://localhost:8003/",
            location_server_url="http://localhost:8006/",
        )

        # Mock helper function to return error message
        mock_find_and_transfer.return_value = (
            "Resource 'resource_123' not found at any location"
        )

        result = transfer_resource("resource_123", "dest_loc")

        assert result.status == ActionStatus.FAILED
        assert (
            "Resource 'resource_123' not found at any location"
            in result.errors[0].message
        )

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._find_resource_and_transfer")
    def test_transfer_resource_success(self, mock_find_and_transfer, mock_context):
        """Test successful transfer_resource action."""
        mock_context.return_value = MadsciContext(
            resource_server_url="http://localhost:8003/",
            location_server_url="http://localhost:8006/",
        )

        # Mock successful transfer result
        mock_transfer_result = MagicMock()
        mock_transfer_result.status = ActionStatus.SUCCEEDED
        mock_transfer_result.json_data = {
            "message": "Transfer completed",
            "source_location_id": "source_location_id",
            "target_location_id": "dest_location_id",
            "workflow_id": "workflow_123",
        }
        mock_find_and_transfer.return_value = mock_transfer_result

        result = transfer_resource("resource_123", "dest_loc")

        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_data["message"] == "Transfer completed"
        mock_find_and_transfer.assert_called_once_with(
            "resource_123", "dest_loc", True, mock_context.return_value
        )

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._find_resource_and_transfer")
    def test_transfer_resource_transfer_failed(
        self, mock_find_and_transfer, mock_context
    ):
        """Test transfer_resource when underlying transfer fails."""
        mock_context.return_value = MadsciContext(
            resource_server_url="http://localhost:8003/",
            location_server_url="http://localhost:8006/",
        )

        # Mock failed transfer result
        mock_transfer_result = MagicMock()
        mock_transfer_result.status = ActionStatus.FAILED
        mock_find_and_transfer.return_value = mock_transfer_result

        result = transfer_resource("resource_123", "dest_loc")

        assert result.status == ActionStatus.FAILED
        mock_find_and_transfer.assert_called_once_with(
            "resource_123", "dest_loc", True, mock_context.return_value
        )

    @patch("madsci.workcell_manager.workcell_actions.get_current_madsci_context")
    @patch("madsci.workcell_manager.workcell_actions._find_resource_and_transfer")
    def test_transfer_resource_async_execution(
        self, mock_find_and_transfer, mock_context
    ):
        """Test transfer_resource with async execution (await_completion=False)."""
        mock_context.return_value = MadsciContext(
            resource_server_url="http://localhost:8003/",
            location_server_url="http://localhost:8006/",
        )

        # Mock successful async transfer result
        mock_transfer_result = MagicMock()
        mock_transfer_result.status = ActionStatus.SUCCEEDED
        mock_transfer_result.json_data = {
            "message": "Transfer workflow enqueued",
            "workflow_id": "workflow_123",
        }
        mock_find_and_transfer.return_value = mock_transfer_result

        result = transfer_resource("resource_123", "dest_loc", await_completion=False)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_data["message"] == "Transfer workflow enqueued"
        mock_find_and_transfer.assert_called_once_with(
            "resource_123", "dest_loc", False, mock_context.return_value
        )


class TestFindResourceAndTransferHelper:
    """Test cases for the _find_resource_and_transfer helper function."""

    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.ResourceClient")
    @patch("madsci.workcell_manager.workcell_actions.transfer")
    def test_find_resource_and_transfer_success(
        self, mock_transfer, mock_resource_client, mock_location_client
    ):
        """Test successful resource finding and transfer."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.location_server_url = "http://localhost:8006/"
        mock_context.resource_server_url = "http://localhost:8003/"

        # Mock resource client
        mock_resource_instance = MagicMock()
        mock_resource_client.return_value = mock_resource_instance
        mock_resource_instance.get_resource.return_value = (
            MagicMock()
        )  # Resource exists

        # Mock location client
        mock_location_instance = MagicMock()
        mock_location_client.return_value = mock_location_instance

        # Mock locations
        mock_location1 = Mock()
        mock_location1.location_id = "loc_1"
        mock_location2 = Mock()
        mock_location2.location_id = "loc_2"
        mock_location_instance.get_locations.return_value = [
            mock_location1,
            mock_location2,
        ]

        # Mock location resources - first location doesn't have resource, second does
        empty_hierarchy = ResourceHierarchy(
            ancestor_ids=[], resource_id="", descendant_ids={}
        )
        found_hierarchy = ResourceHierarchy(
            ancestor_ids=[], resource_id="resource_123", descendant_ids={}
        )
        mock_location_instance.get_location_resources.side_effect = [
            empty_hierarchy,
            found_hierarchy,
        ]

        # Mock successful transfer
        mock_transfer_result = MagicMock()
        mock_transfer_result.status = ActionStatus.SUCCEEDED
        mock_transfer.return_value = mock_transfer_result

        result = _find_resource_and_transfer(
            "resource_123", "dest_loc", True, mock_context
        )

        assert result == mock_transfer_result
        mock_transfer.assert_called_once_with(
            source="loc_2", target="dest_loc", await_completion=True
        )

    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.ResourceClient")
    def test_find_resource_and_transfer_resource_not_found(
        self, mock_resource_client, mock_location_client
    ):
        """Test when resource doesn't exist."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.location_server_url = "http://localhost:8006/"
        mock_context.resource_server_url = "http://localhost:8003/"
        _ = mock_location_client

        # Mock resource client to raise exception
        mock_resource_instance = MagicMock()
        mock_resource_client.return_value = mock_resource_instance
        mock_resource_instance.get_resource.side_effect = Exception(
            "Resource not found"
        )

        result = _find_resource_and_transfer(
            "invalid_resource", "dest_loc", True, mock_context
        )

        assert isinstance(result, str)
        assert "Failed to verify resource" in result

    @patch("madsci.workcell_manager.workcell_actions.LocationClient")
    @patch("madsci.workcell_manager.workcell_actions.ResourceClient")
    def test_find_resource_and_transfer_location_not_found(
        self, mock_resource_client, mock_location_client
    ):
        """Test when resource is not found at any location."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.location_server_url = "http://localhost:8006/"
        mock_context.resource_server_url = "http://localhost:8003/"

        # Mock resource client
        mock_resource_instance = MagicMock()
        mock_resource_client.return_value = mock_resource_instance
        mock_resource_instance.get_resource.return_value = (
            MagicMock()
        )  # Resource exists

        # Mock location client
        mock_location_instance = MagicMock()
        mock_location_client.return_value = mock_location_instance

        # Mock locations
        mock_location1 = Mock()
        mock_location1.location_id = "loc_1"
        mock_location_instance.get_locations.return_value = [mock_location1]

        # Mock location resources - location doesn't have the resource
        empty_hierarchy = ResourceHierarchy(
            ancestor_ids=[], resource_id="", descendant_ids={}
        )
        mock_location_instance.get_location_resources.return_value = empty_hierarchy

        result = _find_resource_and_transfer(
            "resource_123", "dest_loc", True, mock_context
        )

        assert isinstance(result, str)
        assert "not found at any location" in result
