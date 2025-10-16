"""Test node infrastructure including lifecycle, configuration, and basic actions.

Consolidates tests from:
- test_node.py (TestNode implementation)
- test_rest_utils.py (utilities)
- Basic node lifecycle tests from test_rest_node_module.py
"""

import time

from fastapi.testclient import TestClient
from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import NodeStatus
from ulid import ULID

from madsci_node_module.tests.test_node import TestNode
from madsci_node_module.tests.test_rest_utils import (
    execute_action_with_validation,
    parametrize_admin_commands,
    validate_admin_command_response,
)


class TestNodeLifecycle:
    """Test node startup, shutdown, state management."""

    def test_startup_and_shutdown_handlers(self, basic_test_node: TestNode) -> None:
        """Test the startup_handler and shutdown_handler methods."""
        assert not hasattr(basic_test_node, "startup_has_run")
        assert not hasattr(basic_test_node, "shutdown_has_run")
        assert basic_test_node.test_interface is None

        basic_test_node.start_node(testing=True)

        with TestClient(basic_test_node.rest_api) as client:
            time.sleep(0.5)
            assert basic_test_node.startup_has_run
            assert not hasattr(basic_test_node, "shutdown_has_run")
            assert basic_test_node.test_interface is not None

            response = client.get("/status")
            assert response.status_code == 200

        time.sleep(0.5)

        assert basic_test_node.startup_has_run
        assert basic_test_node.shutdown_has_run
        assert basic_test_node.test_interface is None

    def test_node_status_endpoint(self, test_client: TestClient) -> None:
        """Test the /status endpoint."""
        with test_client as client:
            time.sleep(0.1)
            response = client.get("/status")
            assert response.status_code == 200
            status = NodeStatus.model_validate(response.json())
            assert isinstance(status.ready, bool)

    def test_node_state_endpoint(self, test_client: TestClient) -> None:
        """Test the /state endpoint."""
        with test_client as client:
            time.sleep(0.1)
            response = client.get("/state")
            assert response.status_code == 200
            state_data = response.json()
            assert isinstance(state_data, dict)

    def test_node_info_endpoint(self, test_client: TestClient) -> None:
        """Test the /info endpoint."""
        with test_client as client:
            time.sleep(0.1)
            response = client.get("/info")
            assert response.status_code == 200
            info_data = response.json()
            assert isinstance(info_data, dict)
            # Should contain basic node information
            assert isinstance(info_data, dict) and len(info_data) > 0

    def test_shutdown_command(self, basic_test_node: TestNode) -> None:
        """Test the shutdown admin command."""
        basic_test_node.start_node(testing=True)

        with TestClient(basic_test_node.rest_api) as client:
            time.sleep(0.5)
            response = client.post("/admin/shutdown")
            assert response.status_code == 200
            validated_response = AdminCommandResponse.model_validate(response.json())
            assert validated_response.success is True
            assert not validated_response.errors
            assert basic_test_node.shutdown_has_run


class TestNodeConfiguration:
    """Test node configuration and settings."""

    def test_node_factory_basic_config(self, test_node_factory) -> None:
        """Test basic node configuration through factory."""
        node = test_node_factory(
            node_name="Config Test Node",
            module_name="config_test",
            config_overrides={"test_required_param": 42},
        )
        assert node.node_definition.node_name == "Config Test Node"
        assert node.node_definition.module_name == "config_test"
        assert node.config.test_required_param == 42

    def test_node_factory_with_optional_params(self, test_node_factory) -> None:
        """Test node configuration with optional parameters."""
        node = test_node_factory(
            config_overrides={
                "test_required_param": 100,
                "test_optional_param": 200,
                "test_default_param": 300,
            }
        )
        assert node.config.test_required_param == 100
        assert node.config.test_optional_param == 200
        assert node.config.test_default_param == 300

    def test_client_factory_custom_config(self, client_factory) -> None:
        """Test client factory with custom node configuration."""
        client = client_factory(
            node_name="Custom Config Node", node_config={"test_required_param": 999}
        )
        with client as c:
            response = c.get("/status")
            assert response.status_code == 200


class TestBasicActions:
    """Test fundamental action creation and execution."""

    def test_create_action(self, test_client: TestClient) -> None:
        """Test creating a new action."""
        with test_client as client:
            time.sleep(0.5)

            # Create action
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            assert response.status_code == 200
            result = response.json()
            assert "action_id" in result
            action_id = result["action_id"]
            assert ULID.from_str(action_id)  # Validate it's a valid ULID

    def test_start_action(self, test_client: TestClient) -> None:
        """Test starting an action."""
        with test_client as client:
            time.sleep(0.5)

            # Create action
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            assert response.status_code == 200
            action_id = response.json()["action_id"]

            # Start action
            response = client.post(f"/action/test_action/{action_id}/start")
            assert response.status_code == 200
            result = ActionResult.model_validate(response.json())
            assert result.action_id == action_id
            assert result.status in [ActionStatus.RUNNING, ActionStatus.SUCCEEDED]

    def test_action_execution_success(self, test_client: TestClient) -> None:
        """Test successful action execution from start to finish."""
        with test_client as client:
            result = execute_action_with_validation(
                client, "test_action", {"test_param": 1}, ActionStatus.SUCCEEDED
            )
            assert result["status"] == "succeeded"

    def test_action_execution_failure(self, test_client: TestClient) -> None:
        """Test action execution that fails."""
        with test_client as client:
            result = execute_action_with_validation(
                client, "test_fail", {"test_param": 1}, ActionStatus.FAILED
            )
            assert result["status"] == "failed"

    def test_get_action_result(self, test_client: TestClient) -> None:
        """Test retrieving action results."""
        with test_client as client:
            time.sleep(0.5)

            # Create and start action
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            action_id = response.json()["action_id"]

            response = client.post(f"/action/test_action/{action_id}/start")
            assert response.status_code == 200

            # Wait a bit then get result
            time.sleep(0.5)
            response = client.get(f"/action/{action_id}/result")
            assert response.status_code == 200
            result = ActionResult.model_validate(response.json())
            assert result.action_id == action_id

    def test_get_action_result_by_name(self, test_client: TestClient) -> None:
        """Test retrieving action results by action name."""
        with test_client as client:
            time.sleep(0.5)

            # Create and start action
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            action_id = response.json()["action_id"]

            response = client.post(f"/action/test_action/{action_id}/start")
            assert response.status_code == 200

            # Wait a bit then get result by name
            time.sleep(0.5)
            response = client.get(f"/action/test_action/{action_id}/result")
            assert response.status_code == 200
            result = ActionResult.model_validate(response.json())
            assert result.action_id == action_id

    def test_nonexistent_action(self, test_client: TestClient) -> None:
        """Test handling of nonexistent actions."""
        with test_client as client:
            time.sleep(0.5)
            response = client.post("/action/nonexistent_action", json={})
            assert response.status_code == 404

    def test_invalid_action_id(self, test_client: TestClient) -> None:
        """Test handling of invalid action IDs."""
        with test_client as client:
            time.sleep(0.5)
            # Try to get result with invalid ID
            response = client.get("/action/invalid_id/result")
            assert response.status_code == 200
            result = response.json()
            # Should have an error indicating the action wasn't found
            assert "errors" in result
            assert len(result["errors"]) > 0
            assert "not found" in result["errors"][0]["message"].lower()

    def test_action_with_optional_parameters(self, test_client: TestClient) -> None:
        """Test action execution with optional parameters."""
        with test_client as client:
            result = execute_action_with_validation(
                client,
                "test_optional_param_action",
                {"test_param": 42, "optional_param": "test"},
                ActionStatus.SUCCEEDED,
            )
            assert result["status"] == "succeeded"

    def test_action_with_missing_required_params(self, test_client: TestClient) -> None:
        """Test action creation with missing required parameters."""
        with test_client as client:
            time.sleep(0.5)
            # Try to create action without required parameters
            response = client.post("/action/test_action", json={})
            assert response.status_code == 422  # Validation error

    def test_action_history(self, test_client: TestClient) -> None:
        """Test retrieving action history."""
        with test_client as client:
            time.sleep(0.5)

            # Execute a few actions
            response = client.post(
                "/action/test_action", json={"args": {"test_param": 1}}
            )
            action_id_1 = response.json()["action_id"]
            client.post(f"/action/test_action/{action_id_1}/start")

            response = client.post(
                "/action/test_action", json={"args": {"test_param": 2}}
            )
            action_id_2 = response.json()["action_id"]
            client.post(f"/action/test_action/{action_id_2}/start")

            time.sleep(0.5)

            # Get history
            response = client.get("/action")
            assert response.status_code == 200
            history = response.json()
            assert isinstance(history, dict)
            # Should have some history structure
            assert isinstance(history, dict)


class TestAdminCommands:
    """Test admin command functionality using parametrized tests."""

    @parametrize_admin_commands()
    def test_admin_commands(
        self, test_client: TestClient, command: str, expected_state: dict
    ) -> None:
        """Parametrized test for all admin commands."""
        with test_client as client:
            time.sleep(0.1)
            validate_admin_command_response(client, command, expected_state)

    def test_lock_and_unlock_sequence(self, test_client: TestClient) -> None:
        """Test lock/unlock command sequence."""
        with test_client as client:
            time.sleep(0.1)

            # Lock
            response = client.post("/admin/lock")
            assert response.status_code == 200
            validated_response = AdminCommandResponse.model_validate(response.json())
            assert validated_response.success is True

            response = client.get("/status")
            status = NodeStatus.model_validate(response.json())
            assert status.ready is False
            assert status.locked is True

            # Unlock
            response = client.post("/admin/unlock")
            assert response.status_code == 200
            validated_response = AdminCommandResponse.model_validate(response.json())
            assert validated_response.success is True

            response = client.get("/status")
            status = NodeStatus.model_validate(response.json())
            assert status.ready is True
            assert status.locked is False

    def test_pause_and_resume_sequence(self, test_client: TestClient) -> None:
        """Test pause/resume command sequence."""
        with test_client as client:
            time.sleep(0.1)

            # Pause
            response = client.post("/admin/pause")
            assert response.status_code == 200
            response = client.get("/status")
            status = NodeStatus.model_validate(response.json())
            assert status.paused is True
            assert status.ready is False

            # Resume
            response = client.post("/admin/resume")
            assert response.status_code == 200
            response = client.get("/status")
            status = NodeStatus.model_validate(response.json())
            assert status.paused is False
            assert status.ready is True

    def test_safety_stop_and_reset_sequence(self, test_client: TestClient) -> None:
        """Test safety_stop/reset command sequence."""
        with test_client as client:
            time.sleep(0.1)

            # Safety stop
            response = client.post("/admin/safety_stop")
            assert response.status_code == 200
            response = client.get("/status")
            status = NodeStatus.model_validate(response.json())
            assert status.stopped is True

            # Reset
            response = client.post("/admin/reset")
            assert response.status_code == 200
            validated_response = AdminCommandResponse.model_validate(response.json())
            assert validated_response.success is True
