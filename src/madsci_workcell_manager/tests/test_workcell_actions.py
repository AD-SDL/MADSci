"""Unit tests for madsci.workcell_manager.workcell_actions module."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from madsci.common.exceptions import LocationNotFoundError
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.context_types import MadsciContext
from madsci.workcell_manager.workcell_actions import (
    _resolve_location_identifier,
    transfer,
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
            assert "Transfer completed" in result.data["message"]
            assert result.data["source_location_id"] == "source_id"
            assert result.data["destination_location_id"] == "dest_id"
            assert result.data["workflow_id"] == "test_workflow_123"

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
            assert "Transfer workflow enqueued" in result.data["message"]
            assert result.data["workflow_id"] == "test_workflow_123"

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
        mock_location.name = "test_name"
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


class TestWorkcellActionDict:
    """Test cases for the workcell_action_dict."""

    def test_workcell_action_dict_contains_all_actions(self):
        """Test that workcell_action_dict contains all expected actions."""
        expected_actions = ["wait", "transfer"]

        for action in expected_actions:
            assert action in workcell_action_dict
            assert callable(workcell_action_dict[action])

    def test_workcell_action_dict_functions_are_correct(self):
        """Test that workcell_action_dict maps to the correct functions."""
        assert workcell_action_dict["wait"] == wait
        assert workcell_action_dict["transfer"] == transfer

    def test_workcell_action_dict_only_contains_mvp_actions(self):
        """Test that workcell_action_dict only contains MVP actions."""
        assert len(workcell_action_dict) == 2
        assert set(workcell_action_dict.keys()) == {"wait", "transfer"}
