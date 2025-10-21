"""Test to reproduce the Optional[LocationArgument] issue."""

from typing import Optional, Union
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.action_types import ActionRequest
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from madsci.common.types.node_types import RestNodeConfig
from pydantic import BaseModel


class TestConfig(RestNodeConfig):
    """Test configuration."""
    update_node_files: bool = False


class CustomModel(BaseModel):
    """A custom pydantic model for testing."""
    value: str


class TestNodeWithOptionalLocation(RestNode):
    """A test node with optional location argument."""
    
    __test__ = False
    config_model = TestConfig
    
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
            return f"Data: {data.value}"
        return "No data"


if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    from madsci.common.utils import new_ulid_str
    
    # Create a temporary node definition file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        node_id = new_ulid_str()
        f.write(f"""
node_name: test_optional_location_node
node_id: {node_id}
module_name: test_node_with_optional_location
module_version: 0.0.1
        """)
        node_def_path = f.name
    
    try:
        # Create config
        config = TestConfig(node_definition=node_def_path)
        
        # Create node
        node = TestNodeWithOptionalLocation(node_config=config)
        node.start_node()
        
        # Wait for node to be ready
        import time
        for _ in range(10):
            if node.node_status.ready:
                break
            time.sleep(0.5)
        
        if not node.node_status.ready:
            print("WARNING: Node is not ready, tests may fail")
        
        # Test 1: Optional[LocationArgument] with None
        print("\n=== Test 1: Optional[LocationArgument] with None ===")
        request1 = ActionRequest(
            action_name="action_with_optional_location",
            args={"speed": 50}
        )
        result1 = node.run_action(request1)
        print(f"Result: {result1}")
        
        # Test 2: Optional[LocationArgument] with dict (simulating deserialized JSON)
        print("\n=== Test 2: Optional[LocationArgument] with dict ===")
        request2 = ActionRequest(
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
        result2 = node.run_action(request2)
        print(f"Result: {result2}")
        print(f"Result status: {result2.status}")
        if result2.errors:
            print(f"Errors: {result2.errors}")
        
        # Test 3: Union[LocationArgument, str] with dict
        print("\n=== Test 3: Union[LocationArgument, str] with dict ===")
        request3 = ActionRequest(
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
        result3 = node.run_action(request3)
        print(f"Result: {result3}")
        print(f"Result status: {result3.status}")
        if result3.errors:
            print(f"Errors: {result3.errors}")
        
        # Test 4: Optional[CustomModel] with dict
        print("\n=== Test 4: Optional[CustomModel] with dict ===")
        request4 = ActionRequest(
            action_name="action_with_optional_custom_model",
            args={
                "data": {"value": "test_value"}
            }
        )
        result4 = node.run_action(request4)
        print(f"Result: {result4}")
        print(f"Result status: {result4.status}")
        if result4.errors:
            print(f"Errors: {result4.errors}")
        
    finally:
        # Clean up
        Path(node_def_path).unlink()
