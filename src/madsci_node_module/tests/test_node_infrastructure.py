"""Test node infrastructure including lifecycle, configuration, and basic actions."""

import inspect
import time
from pathlib import Path
from typing import Annotated, Optional, Union, get_type_hints

from fastapi.testclient import TestClient
from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionRequest,
    ActionResult,
    ActionStatus,
    FileArgumentDefinition,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import (
    NodeConfig,
    NodeDefinition,
    NodeInfo,
    NodeStatus,
)
from madsci.common.utils import new_ulid_str
from madsci.node_module.abstract_node_module import AbstractNode
from madsci.node_module.helpers import action
from pydantic import BaseModel
from ulid import ULID

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig
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


class CustomModel(BaseModel):
    """A custom pydantic model for testing."""

    value: str
    count: int = 0


class LocalTestNodeConfig(NodeConfig):
    """Test configuration."""

    update_node_files: bool = False


class MockNode(AbstractNode):
    """Mock node for testing."""

    __test__ = False
    config_model = LocalTestNodeConfig

    def __init__(self):
        """Initialize without calling parent __init__ to avoid file dependencies."""
        self.config = LocalTestNodeConfig()
        self.node_definition = NodeDefinition(
            node_name="test_node",
            node_id=new_ulid_str(),
            module_name="test_module",
            module_version="0.0.1",
        )
        self.node_info = NodeInfo.from_node_def_and_config(
            self.node_definition, self.config
        )
        self.action_handlers = {}
        self.action_history = {}
        self.node_state = {}
        self.logger = self.event_client = EventClient()
        self.resource_client = ResourceClient(event_client=self.event_client)
        self.data_client = DataClient()
        self.node_status = NodeStatus(ready=True)

        # Add actions
        self._register_actions()

    def _register_actions(self):
        """Register all actions for this mock node."""
        for action_callable in self.__class__.__dict__.values():
            if hasattr(action_callable, "__is_madsci_action__"):
                self._add_action(
                    func=action_callable,
                    action_name=action_callable.__madsci_action_name__,
                    description=action_callable.__madsci_action_description__,
                    blocking=action_callable.__madsci_action_blocking__,
                    result_definitions=action_callable.__madsci_action_result_definitions__,
                )

    @action
    def action_with_optional_location(
        self,
        target: Optional[LocationArgument] = None,
        speed: int = 100,
    ) -> str:
        """Action with optional location argument."""
        if target is not None:
            assert isinstance(target, LocationArgument), (
                f"Expected LocationArgument, got {type(target)}"
            )
            return f"Moving to {target.representation} at speed {speed}"
        return f"No movement at speed {speed}"

    @action
    def action_with_union_location(
        self,
        target: Union[LocationArgument, str] = "default",
        speed: int = 100,
    ) -> str:
        """Action with union type including location argument."""
        if isinstance(target, LocationArgument):
            return f"Moving to location {target.representation} at speed {speed}"
        return f"Moving to string {target} at speed {speed}"

    @action
    def action_with_optional_custom_model(
        self,
        data: Optional[CustomModel] = None,
    ) -> str:
        """Action with optional custom BaseModel."""
        if data is not None:
            assert isinstance(data, CustomModel), (
                f"Expected CustomModel, got {type(data)}"
            )
            return f"Data: {data.value}, count: {data.count}"
        return "No data"

    @action
    def action_with_union_custom_model(
        self,
        data: Union[CustomModel, dict] = None,
    ) -> str:
        """Action with union type including custom BaseModel."""
        if isinstance(data, CustomModel):
            return f"CustomModel: {data.value}"
        return f"Dict: {data}"


class TestComplexTypeHandling:
    """Test Optional[LocationArgument] and other complex type handling in node actions."""

    def _create_mock_node(self) -> MockNode:
        """Create a mock node for testing."""
        return MockNode()

    def test_optional_location_with_none(self) -> None:
        """Test that Optional[LocationArgument] works with None."""
        node = self._create_mock_node()
        request = ActionRequest(
            action_name="action_with_optional_location", args={"speed": 50}
        )
        result = node.run_action(request)
        assert result.status.value == "succeeded"
        assert "No movement" in result.json_result

    def test_optional_location_with_dict(self) -> None:
        """Test that Optional[LocationArgument] properly converts dict to LocationArgument."""
        node = self._create_mock_node()

        # Simulate deserialized JSON with dict instead of LocationArgument
        request = ActionRequest(
            action_name="action_with_optional_location",
            args={
                "target": {
                    "representation": "deck_slot_A1",
                    "resource_id": "resource_123",
                    "location_name": "deck_A1",
                },
                "speed": 75,
            },
        )

        result = node.run_action(request)
        # This should succeed if the fix is applied
        assert result.status.value == "succeeded", (
            f"Expected success but got {result.status}: {result.errors}"
        )
        assert "deck_slot_A1" in result.json_result

    def test_union_location_with_dict(self) -> None:
        """Test that Union[LocationArgument, str] properly converts dict to LocationArgument."""
        node = self._create_mock_node()

        request = ActionRequest(
            action_name="action_with_union_location",
            args={
                "target": {
                    "representation": "deck_slot_B1",
                    "resource_id": "resource_456",
                    "location_name": "deck_B1",
                },
                "speed": 100,
            },
        )

        result = node.run_action(request)
        assert result.status.value == "succeeded", (
            f"Expected success but got {result.status}: {result.errors}"
        )
        assert "deck_slot_B1" in result.json_result

    def test_union_location_with_string(self) -> None:
        """Test that Union[LocationArgument, str] works with string."""
        node = self._create_mock_node()

        request = ActionRequest(
            action_name="action_with_union_location",
            args={"target": "string_location", "speed": 100},
        )

        result = node.run_action(request)
        assert result.status.value == "succeeded"
        assert "string_location" in result.json_result

    def test_optional_custom_model_with_none(self) -> None:
        """Test that Optional[CustomModel] works with None."""
        node = self._create_mock_node()

        request = ActionRequest(
            action_name="action_with_optional_custom_model", args={}
        )

        result = node.run_action(request)
        assert result.status.value == "succeeded"
        assert "No data" in result.json_result

    def test_optional_custom_model_with_dict(self) -> None:
        """Test that Optional[CustomModel] properly converts dict to CustomModel."""
        node = self._create_mock_node()

        request = ActionRequest(
            action_name="action_with_optional_custom_model",
            args={"data": {"value": "test_value", "count": 42}},
        )

        result = node.run_action(request)
        # This should succeed if the fix is applied
        assert result.status.value == "succeeded", (
            f"Expected success but got {result.status}: {result.errors}"
        )
        assert "test_value" in result.json_result
        assert "42" in result.json_result

    def test_union_custom_model_with_dict(self) -> None:
        """Test that Union[CustomModel, dict] properly converts dict to CustomModel when possible."""
        node = self._create_mock_node()

        request = ActionRequest(
            action_name="action_with_union_custom_model",
            args={"data": {"value": "test_value", "count": 10}},
        )

        result = node.run_action(request)
        assert result.status.value == "succeeded"


class TestAnnotatedPathInNode:
    """Test that AbstractNode correctly handles Annotated[Path] in action parameters."""

    def test_is_file_type_helper(self) -> None:
        """Test the _is_file_type helper method logic."""

        # Create a dummy node to access the method
        class DummyNode(AbstractNode):
            __test__ = False
            config_model = TestNodeConfig

            def __init__(self):
                """Initialize without calling parent __init__ to avoid file dependencies."""
                self.config = TestNodeConfig(test_required_param=42)
                self.node_definition = NodeDefinition(
                    node_name="test_node",
                    node_id=new_ulid_str(),
                    module_name="test_module",
                    module_version="0.0.1",
                )
                self.node_info = NodeInfo.from_node_def_and_config(
                    self.node_definition, self.config
                )
                self.action_handlers = {}
                self.action_history = {}
                self.node_state = {}
                self.logger = self.event_client = EventClient()
                self.resource_client = ResourceClient(event_client=self.event_client)
                self.data_client = DataClient()
                self.node_status = NodeStatus(ready=True)

        node = DummyNode()

        # Test Path
        assert node._is_file_type(Path) is True

        # Test list[Path]
        assert node._is_file_type(list[Path]) is True

        # Test str (should not be a file type)
        assert node._is_file_type(str) is False

        # Test list[str] (should not be a file type)
        assert node._is_file_type(list[str]) is False

        # Test int (should not be a file type)
        assert node._is_file_type(int) is False

    def test_annotated_path_extraction_in_parse_action_arg(self) -> None:
        """Test that Annotated[Path] is correctly extracted and recognized as a file parameter."""
        # Create test action definition
        action_def = ActionDefinition(
            name="test_action",
            description="Test action",
            blocking=False,
        )

        # Create a dummy node
        class DummyNode(AbstractNode):
            __test__ = False
            config_model = TestNodeConfig

            def __init__(self):
                """Initialize without calling parent __init__ to avoid file dependencies."""
                self.config = TestNodeConfig(test_required_param=42)
                self.node_definition = NodeDefinition(
                    node_name="test_node",
                    node_id=new_ulid_str(),
                    module_name="test_module",
                    module_version="0.0.1",
                )
                self.node_info = NodeInfo.from_node_def_and_config(
                    self.node_definition, self.config
                )
                self.action_handlers = {}
                self.action_history = {}
                self.node_state = {}
                self.logger = self.event_client = EventClient()
                self.resource_client = ResourceClient(event_client=self.event_client)
                self.data_client = DataClient()
                self.node_status = NodeStatus(ready=True)

        node = DummyNode()

        # Simulate a function signature
        def test_func(file_param: Annotated[Path, "A file parameter"]):
            pass

        signature = inspect.signature(test_func)
        type_hints = get_type_hints(test_func, include_extras=True)

        node._parse_action_arg(
            action_def, signature, "file_param", type_hints["file_param"]
        )

        # Verify it was added as a file parameter, not a regular argument
        assert "file_param" in action_def.files, "file_param should be in files"
        assert "file_param" not in action_def.args, "file_param should not be in args"
        assert isinstance(action_def.files["file_param"], FileArgumentDefinition)
        assert action_def.files["file_param"].description == "A file parameter"

    def test_annotated_list_path_extraction(self) -> None:
        """Test that Annotated[list[Path]] is correctly recognized as a file parameter."""
        # Create test action definition
        action_def = ActionDefinition(
            name="test_action",
            description="Test action",
            blocking=False,
        )

        # Create a dummy node
        class DummyNode(AbstractNode):
            __test__ = False
            config_model = TestNodeConfig

            def __init__(self):
                """Initialize without calling parent __init__ to avoid file dependencies."""
                self.config = TestNodeConfig(test_required_param=42)
                self.node_definition = NodeDefinition(
                    node_name="test_node",
                    node_id=new_ulid_str(),
                    module_name="test_module",
                    module_version="0.0.1",
                )
                self.node_info = NodeInfo.from_node_def_and_config(
                    self.node_definition, self.config
                )
                self.action_handlers = {}
                self.action_history = {}
                self.node_state = {}
                self.logger = self.event_client = EventClient()
                self.resource_client = ResourceClient(event_client=self.event_client)
                self.data_client = DataClient()
                self.node_status = NodeStatus(ready=True)

        node = DummyNode()

        # Simulate a function signature
        def test_func(files_param: Annotated[list[Path], "Multiple files"]):
            pass

        signature = inspect.signature(test_func)
        type_hints = get_type_hints(test_func, include_extras=True)

        node._parse_action_arg(
            action_def, signature, "files_param", type_hints["files_param"]
        )

        # Verify it was added as a file parameter, not a regular argument
        assert "files_param" in action_def.files, "files_param should be in files"
        assert "files_param" not in action_def.args, "files_param should not be in args"
        assert isinstance(action_def.files["files_param"], FileArgumentDefinition)
        assert action_def.files["files_param"].description == "Multiple files"

    def test_plain_list_path_recognition(self) -> None:
        """Test that list[Path] without Annotated is correctly recognized as a file parameter."""
        # Create test action definition
        action_def = ActionDefinition(
            name="test_action",
            description="Test action",
            blocking=False,
        )

        # Create a dummy node
        class DummyNode(AbstractNode):
            __test__ = False
            config_model = TestNodeConfig

            def __init__(self):
                """Initialize without calling parent __init__ to avoid file dependencies."""
                self.config = TestNodeConfig(test_required_param=42)
                self.node_definition = NodeDefinition(
                    node_name="test_node",
                    node_id=new_ulid_str(),
                    module_name="test_module",
                    module_version="0.0.1",
                )
                self.node_info = NodeInfo.from_node_def_and_config(
                    self.node_definition, self.config
                )
                self.action_handlers = {}
                self.action_history = {}
                self.node_state = {}
                self.logger = self.event_client = EventClient()
                self.resource_client = ResourceClient(event_client=self.event_client)
                self.data_client = DataClient()
                self.node_status = NodeStatus(ready=True)

        node = DummyNode()

        # Simulate a function signature
        def test_func(files_param: list[Path]):
            pass

        signature = inspect.signature(test_func)
        type_hints = get_type_hints(test_func, include_extras=True)

        node._parse_action_arg(
            action_def, signature, "files_param", type_hints["files_param"]
        )

        # Verify it was added as a file parameter, not a regular argument
        assert "files_param" in action_def.files, "files_param should be in files"
        assert "files_param" not in action_def.args, "files_param should not be in args"
        assert isinstance(action_def.files["files_param"], FileArgumentDefinition)

    def test_optional_annotated_path(self) -> None:
        """Test that Optional[Annotated[Path, ...]] is correctly handled."""
        # Create test action definition
        action_def = ActionDefinition(
            name="test_action",
            description="Test action",
            blocking=False,
        )

        # Create a dummy node
        class DummyNode(AbstractNode):
            __test__ = False
            config_model = TestNodeConfig

            def __init__(self):
                """Initialize without calling parent __init__ to avoid file dependencies."""
                self.config = TestNodeConfig(test_required_param=42)
                self.node_definition = NodeDefinition(
                    node_name="test_node",
                    node_id=new_ulid_str(),
                    module_name="test_module",
                    module_version="0.0.1",
                )
                self.node_info = NodeInfo.from_node_def_and_config(
                    self.node_definition, self.config
                )
                self.action_handlers = {}
                self.action_history = {}
                self.node_state = {}
                self.logger = self.event_client = EventClient()
                self.resource_client = ResourceClient(event_client=self.event_client)
                self.data_client = DataClient()
                self.node_status = NodeStatus(ready=True)

        node = DummyNode()

        # Simulate a function signature
        def test_func(
            optional_file: Optional[Annotated[Path, "An optional file"]] = None,
        ):
            pass

        signature = inspect.signature(test_func)
        type_hints = get_type_hints(test_func, include_extras=True)

        node._parse_action_arg(
            action_def, signature, "optional_file", type_hints["optional_file"]
        )

        # Verify it was added as a file parameter
        assert "optional_file" in action_def.files, "optional_file should be in files"
        assert "optional_file" not in action_def.args, (
            "optional_file should not be in args"
        )
        assert isinstance(action_def.files["optional_file"], FileArgumentDefinition)
        assert action_def.files["optional_file"].description == "An optional file"
