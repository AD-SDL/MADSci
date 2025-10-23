"""Test that AbstractNode correctly handles Annotated[Path] in action parameters."""

from pathlib import Path
from typing import Annotated, Optional
import pytest


def test_is_file_type_helper():
    """Test the _is_file_type helper method logic."""
    from madsci.node_module.abstract_node_module import AbstractNode
    from typing import get_origin, get_args
    
    # Create a dummy node to access the method
    class DummyNode(AbstractNode):
        pass
    
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


def test_annotated_path_extraction_in_parse_action_arg():
    """Test that Annotated[Path] is correctly extracted and recognized as a file parameter."""
    from madsci.node_module.abstract_node_module import AbstractNode
    from madsci.common.types.action_types import ActionDefinition, FileArgumentDefinition
    from typing import get_origin, get_args
    import inspect
    
    # Create test action definition
    action_def = ActionDefinition(
        name="test_action",
        description="Test action",
        blocking=False,
    )
    
    # Create a dummy node
    class DummyNode(AbstractNode):
        pass
    
    node = DummyNode()
    
    # Simulate a function signature
    def test_func(file_param: Annotated[Path, "A file parameter"]):
        pass
    
    signature = inspect.signature(test_func)
    
    # Parse the parameter
    from typing import get_type_hints
    type_hints = get_type_hints(test_func, include_extras=True)
    
    node._parse_action_arg(
        action_def,
        signature,
        "file_param",
        type_hints["file_param"]
    )
    
    # Verify it was added as a file parameter, not a regular argument
    assert "file_param" in action_def.files, "file_param should be in files"
    assert "file_param" not in action_def.args, "file_param should not be in args"
    assert isinstance(action_def.files["file_param"], FileArgumentDefinition)
    assert action_def.files["file_param"].description == "A file parameter"


def test_annotated_list_path_extraction():
    """Test that Annotated[list[Path]] is correctly recognized as a file parameter."""
    from madsci.node_module.abstract_node_module import AbstractNode
    from madsci.common.types.action_types import ActionDefinition, FileArgumentDefinition
    import inspect
    
    # Create test action definition
    action_def = ActionDefinition(
        name="test_action",
        description="Test action",
        blocking=False,
    )
    
    # Create a dummy node
    class DummyNode(AbstractNode):
        pass
    
    node = DummyNode()
    
    # Simulate a function signature
    def test_func(files_param: Annotated[list[Path], "Multiple files"]):
        pass
    
    signature = inspect.signature(test_func)
    
    # Parse the parameter
    from typing import get_type_hints
    type_hints = get_type_hints(test_func, include_extras=True)
    
    node._parse_action_arg(
        action_def,
        signature,
        "files_param",
        type_hints["files_param"]
    )
    
    # Verify it was added as a file parameter, not a regular argument
    assert "files_param" in action_def.files, "files_param should be in files"
    assert "files_param" not in action_def.args, "files_param should not be in args"
    assert isinstance(action_def.files["files_param"], FileArgumentDefinition)
    assert action_def.files["files_param"].description == "Multiple files"


def test_plain_list_path_recognition():
    """Test that list[Path] without Annotated is correctly recognized as a file parameter."""
    from madsci.node_module.abstract_node_module import AbstractNode
    from madsci.common.types.action_types import ActionDefinition, FileArgumentDefinition
    import inspect
    
    # Create test action definition
    action_def = ActionDefinition(
        name="test_action",
        description="Test action",
        blocking=False,
    )
    
    # Create a dummy node
    class DummyNode(AbstractNode):
        pass
    
    node = DummyNode()
    
    # Simulate a function signature
    def test_func(files_param: list[Path]):
        pass
    
    signature = inspect.signature(test_func)
    
    # Parse the parameter
    from typing import get_type_hints
    type_hints = get_type_hints(test_func, include_extras=True)
    
    node._parse_action_arg(
        action_def,
        signature,
        "files_param",
        type_hints["files_param"]
    )
    
    # Verify it was added as a file parameter, not a regular argument
    assert "files_param" in action_def.files, "files_param should be in files"
    assert "files_param" not in action_def.args, "files_param should not be in args"
    assert isinstance(action_def.files["files_param"], FileArgumentDefinition)


def test_optional_annotated_path():
    """Test that Optional[Annotated[Path, ...]] is correctly handled."""
    from madsci.node_module.abstract_node_module import AbstractNode
    from madsci.common.types.action_types import ActionDefinition, FileArgumentDefinition
    import inspect
    
    # Create test action definition
    action_def = ActionDefinition(
        name="test_action",
        description="Test action",
        blocking=False,
    )
    
    # Create a dummy node
    class DummyNode(AbstractNode):
        pass
    
    node = DummyNode()
    
    # Simulate a function signature
    def test_func(optional_file: Optional[Annotated[Path, "An optional file"]] = None):
        pass
    
    signature = inspect.signature(test_func)
    
    # Parse the parameter
    from typing import get_type_hints
    type_hints = get_type_hints(test_func, include_extras=True)
    
    node._parse_action_arg(
        action_def,
        signature,
        "optional_file",
        type_hints["optional_file"]
    )
    
    # Verify it was added as a file parameter
    assert "optional_file" in action_def.files, "optional_file should be in files"
    assert "optional_file" not in action_def.args, "optional_file should not be in args"
    assert isinstance(action_def.files["optional_file"], FileArgumentDefinition)
    assert action_def.files["optional_file"].description == "An optional file"
