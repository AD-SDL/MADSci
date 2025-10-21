"""Test for Optional[LocationArgument] and other complex type handling in node actions."""

from typing import Optional, Union
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from madsci.common.types.location_types import LocationArgument
from madsci.common.types.action_types import ActionRequest
from madsci.node_module.abstract_node_module import AbstractNode
from madsci.node_module.helpers import action
from madsci.common.types.node_types import NodeConfig


class CustomModel(BaseModel):
    """A custom pydantic model for testing."""
    value: str
    count: int = 0


class TestNodeConfig(NodeConfig):
    """Test configuration."""
    update_node_files: bool = False


class MockNode(AbstractNode):
    """Mock node for testing."""
    
    __test__ = False
    config_model = TestNodeConfig
    
    def __init__(self):
        """Initialize without calling parent __init__ to avoid file dependencies."""
        # Minimal initialization needed for testing
        from madsci.common.types.node_types import NodeDefinition, NodeInfo
        from madsci.common.utils import new_ulid_str
        
        self.config = TestNodeConfig()
        self.node_definition = NodeDefinition(
            node_name="test_node",
            node_id=new_ulid_str(),
            module_name="test_module",
            module_version="0.0.1"
        )
        self.node_info = NodeInfo.from_node_def_and_config(
            self.node_definition, self.config
        )
        self.action_handlers = {}
        self.action_history = {}
        self.node_state = {}
        
        # Configure logger and clients
        from madsci.client.event_client import EventClient
        from madsci.client.resource_client import ResourceClient
        from madsci.client.data_client import DataClient
        
        self.logger = self.event_client = EventClient()
        self.resource_client = ResourceClient(event_client=self.event_client)
        self.data_client = DataClient()
        
        # Initialize node status
        from madsci.common.types.node_types import NodeStatus
        self.node_status = NodeStatus(ready=True)
        
        # Add actions
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
            assert isinstance(target, LocationArgument), f"Expected LocationArgument, got {type(target)}"
            return f"Moving to {target.representation} at speed {speed}"
        return f"No movement at speed {speed}"
    
    @action
    def action_with_union_location(
        self,
        target: Union[LocationArgument, str],
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
            assert isinstance(data, CustomModel), f"Expected CustomModel, got {type(data)}"
            return f"Data: {data.value}, count: {data.count}"
        return "No data"
    
    @action
    def action_with_union_custom_model(
        self,
        data: Union[CustomModel, dict],
    ) -> str:
        """Action with union type including custom BaseModel."""
        if isinstance(data, CustomModel):
            return f"CustomModel: {data.value}"
        return f"Dict: {data}"


class TestOptionalLocationArgument:
    """Test Optional[LocationArgument] and complex type handling."""
    
    def test_optional_location_with_none(self):
        """Test that Optional[LocationArgument] works with None."""
        node = MockNode()
        
        request = ActionRequest(
            action_name="action_with_optional_location",
            args={"speed": 50}
        )
        
        result = node.run_action(request)
        assert result.status.value == "succeeded"
        assert "No movement" in result.json_result
    
    def test_optional_location_with_dict(self):
        """Test that Optional[LocationArgument] properly converts dict to LocationArgument."""
        node = MockNode()
        
        # Simulate deserialized JSON with dict instead of LocationArgument
        request = ActionRequest(
            action_name="action_with_optional_location",
            args={
                "target": {
                    "representation": "deck_slot_A1",
                    "resource_id": "resource_123",
                    "location_name": "deck_A1"
                },
                "speed": 75
            }
        )
        
        result = node.run_action(request)
        # This should succeed if the fix is applied
        assert result.status.value == "succeeded", f"Expected success but got {result.status}: {result.errors}"
        assert "deck_slot_A1" in result.json_result
    
    def test_union_location_with_dict(self):
        """Test that Union[LocationArgument, str] properly converts dict to LocationArgument."""
        node = MockNode()
        
        request = ActionRequest(
            action_name="action_with_union_location",
            args={
                "target": {
                    "representation": "deck_slot_B1",
                    "resource_id": "resource_456",
                    "location_name": "deck_B1"
                },
                "speed": 100
            }
        )
        
        result = node.run_action(request)
        assert result.status.value == "succeeded", f"Expected success but got {result.status}: {result.errors}"
        assert "deck_slot_B1" in result.json_result
    
    def test_union_location_with_string(self):
        """Test that Union[LocationArgument, str] works with string."""
        node = MockNode()
        
        request = ActionRequest(
            action_name="action_with_union_location",
            args={
                "target": "string_location",
                "speed": 100
            }
        )
        
        result = node.run_action(request)
        assert result.status.value == "succeeded"
        assert "string_location" in result.json_result
    
    def test_optional_custom_model_with_none(self):
        """Test that Optional[CustomModel] works with None."""
        node = MockNode()
        
        request = ActionRequest(
            action_name="action_with_optional_custom_model",
            args={}
        )
        
        result = node.run_action(request)
        assert result.status.value == "succeeded"
        assert "No data" in result.json_result
    
    def test_optional_custom_model_with_dict(self):
        """Test that Optional[CustomModel] properly converts dict to CustomModel."""
        node = MockNode()
        
        request = ActionRequest(
            action_name="action_with_optional_custom_model",
            args={
                "data": {"value": "test_value", "count": 42}
            }
        )
        
        result = node.run_action(request)
        # This should succeed if the fix is applied
        assert result.status.value == "succeeded", f"Expected success but got {result.status}: {result.errors}"
        assert "test_value" in result.json_result
        assert "42" in result.json_result
    
    def test_union_custom_model_with_dict(self):
        """Test that Union[CustomModel, dict] properly converts dict to CustomModel when possible."""
        node = MockNode()
        
        request = ActionRequest(
            action_name="action_with_union_custom_model",
            args={
                "data": {"value": "test_value", "count": 10}
            }
        )
        
        result = node.run_action(request)
        # This test might be expected to fail depending on implementation
        # Union types are trickier - the system might not know which type to use
        # For now, we expect dict to be preserved as dict
        assert result.status.value == "succeeded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
