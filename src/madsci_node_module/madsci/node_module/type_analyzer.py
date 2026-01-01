"""Type analysis utilities for MADSci action parsing.

This module provides centralized, recursive type analysis for parsing action
arguments and return types, handling arbitrary nesting of type hints like
Optional, Union, Annotated, list, dict, etc.

## Overview

The type analyzer solves the problem of parsing complex, deeply-nested Python type
hints commonly found in MADSci action signatures. It recursively unwraps type
wrappers and identifies special MADSci types like LocationArgument, Path,
ActionResult, etc., at any nesting level.

## Key Features

- **Recursive Type Unwrapping**: Handles arbitrary nesting of Optional, Union,
  Annotated, list, dict, and tuple types
- **Special Type Detection**: Identifies MADSci-specific types (LocationArgument,
  Path, ActionResult, ActionFiles, ActionJSON) regardless of nesting depth
- **Metadata Preservation**: Collects and preserves metadata from Annotated types
  throughout the type hierarchy
- **Union Validation**: Detects and reports conflicting special types in unions
- **Python 3.9+ Support**: Handles typing.Union and types.UnionType (| operator in Python 3.10+)
- **Depth Protection**: Prevents infinite recursion with configurable depth limits

## Usage Examples

### Basic Type Analysis

```python
from madsci.node_module.type_analyzer import analyze_type
from madsci.common.types.location_types import LocationArgument

# Simple type
info = analyze_type(int)
assert info.base_type == int
assert not info.is_optional

# Optional type
info = analyze_type(Optional[LocationArgument])
assert info.base_type == LocationArgument
assert info.is_optional
assert info.special_type == "location"
```

### Complex Nested Types

```python
from typing import Annotated, Optional

# Deeply nested type
info = analyze_type(Optional[Annotated[LocationArgument, "Transfer source"]])
assert info.base_type == LocationArgument
assert info.is_optional
assert info.special_type == "location"
assert "Transfer source" in info.metadata

# Container with special types
info = analyze_type(list[Path])
assert info.is_list
assert info.special_type == "file"
```

### Helper Functions

```python
from madsci.node_module.type_analyzer import (
    is_optional_type,
    is_location_argument_type,
    is_file_type,
    is_action_result_type,
)

# Quick type checks
assert is_optional_type(Optional[int])
assert is_location_argument_type(LocationArgument)
assert is_file_type(Path)
assert is_action_result_type(ActionFailed)
```

## Architecture

The module uses a two-phase approach:

1. **Type Unwrapping**: Recursively unwraps type wrappers (Annotated, Union, etc.)
   to extract the base type and characteristics
2. **Classification**: Identifies special MADSci types and validates type combinations

This allows the action parser to correctly handle types like:
- `Optional[Annotated[LocationArgument, "description"]]`
- `list[Annotated[Path, FileArgumentDefinition(...)]]`
- `Union[str, int] | None` (Python 3.10+)

## Error Handling

The analyzer raises `ValueError` for:
- Unions with conflicting special types (e.g., `Union[Path, LocationArgument]`)
- Excessive recursion depth (configurable, default 20 levels)
- Other invalid type combinations

All errors include detailed messages with the problematic type hint for debugging.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Annotated, Any, Optional, Union, get_args, get_origin

from madsci.common.types.action_types import (
    ActionDatapoints,
    ActionFiles,
    ActionJSON,
    ActionResult,
)
from madsci.common.types.location_types import LocationArgument

# Python 3.10+ has types.UnionType for the | operator
# In Python 3.9, we only have typing.Union
if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = None  # type: ignore[assignment, misc]


@dataclass
class TypeInfo:
    """Complete information about an analyzed type hint.

    This dataclass contains all relevant information extracted from a type hint
    through recursive analysis, including type characteristics, container details,
    union types, metadata from Annotated, and special type classification.
    """

    # The innermost, fully unwrapped base type
    base_type: Any

    # Type characteristics
    is_optional: bool = False  # Whether None is in a Union
    is_union: bool = False  # Whether this is a Union (non-Optional)
    is_list: bool = False  # Whether this is list[T]
    is_dict: bool = False  # Whether this is dict[K, V]
    is_tuple: bool = False  # Whether this is tuple[...]

    # Container element types (if applicable)
    list_element_type: Optional[Any] = None
    dict_key_type: Optional[Any] = None
    dict_value_type: Optional[Any] = None
    tuple_element_types: Optional[tuple[Any, ...]] = None

    # Union types (if applicable)
    union_types: Optional[list[Any]] = None

    # Metadata from Annotated
    metadata: list[Any] = field(default_factory=list)

    # Special type classification
    special_type: Optional[str] = None  # 'location', 'file', 'action_result', etc.

    # For special types, the actual class
    special_type_class: Optional[type] = None


def analyze_type(type_hint: Any, depth: int = 0, max_depth: int = 20) -> TypeInfo:  # noqa: PLR0911
    """Recursively analyze a type hint to extract all relevant information.

    This function performs deep analysis of Python type hints, unwrapping all
    layers of type wrappers (Optional, Union, Annotated, list, dict, tuple) and
    identifying special MADSci types at any nesting level.

    Args:
        type_hint: The type hint to analyze
        depth: Current recursion depth (for safety)
        max_depth: Maximum recursion depth before raising an error

    Returns:
        TypeInfo object with complete type information

    Raises:
        ValueError: If recursion depth exceeds max_depth or unsupported
                   combinations are found
    """
    # Check recursion depth
    if depth >= max_depth:
        raise ValueError(
            f"Type analysis exceeded maximum recursion depth of {max_depth}. "
            f"Type hint may be too complex or circular: {type_hint}"
        )

    # Handle None specially
    if type_hint is None:
        return TypeInfo(base_type=type(None))

    # Initialize result
    result = TypeInfo(base_type=type_hint)

    # Get origin and args for generic types
    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Handle Annotated - extract metadata and continue analysis
    if origin is Annotated:
        base_type, metadata = extract_metadata_from_annotated(type_hint)
        # Recursively analyze the base type
        inner_info = analyze_type(base_type, depth + 1, max_depth)
        # Merge metadata
        result = inner_info
        result.metadata.extend(metadata)
        return result

    # Handle Union types (including Optional)
    # Note: Python 3.10+ uses types.UnionType for | operator
    is_union_type = UnionType is not None and isinstance(type_hint, UnionType)
    if origin is Union or is_union_type:
        if not args:  # For types.UnionType, get_args works directly
            args = get_args(type_hint)
        return _analyze_union_type(type_hint, args, depth, max_depth)

    # Handle list types
    if origin is list:
        return _analyze_list_type(type_hint, args, depth, max_depth)

    # Handle dict types
    if origin is dict:
        return _analyze_dict_type(type_hint, args, depth, max_depth)

    # Handle tuple types
    if origin is tuple:
        return _analyze_tuple_type(type_hint, args, depth, max_depth)

    # At this point, we have a base type - classify it
    result.base_type = type_hint
    result.special_type = _classify_special_type(type_hint)
    if result.special_type:
        result.special_type_class = type_hint

    return result


def is_optional_type(type_hint: Any) -> bool:
    """Check if a type hint represents an Optional type (Union with None).

    Args:
        type_hint: The type hint to check

    Returns:
        True if the type is Optional[T] or Union[T, None]
    """
    origin = get_origin(type_hint)
    if origin is Union or (UnionType is not None and origin is UnionType):
        args = get_args(type_hint)
        return type(None) in args
    return False


def is_location_argument_type(type_hint: Any) -> bool:
    """Check if a type hint contains LocationArgument at any level.

    Args:
        type_hint: The type hint to check

    Returns:
        True if LocationArgument is the base type
    """
    try:
        return type_hint == LocationArgument or (
            isinstance(type_hint, type) and issubclass(type_hint, LocationArgument)
        )
    except TypeError:
        return False


def is_file_type(type_hint: Any) -> bool:
    """Check if a type hint represents a file parameter (Path or subclass).

    Args:
        type_hint: The type hint to check

    Returns:
        True if the type is Path, PurePath, or subclass
    """
    try:
        return type_hint == Path or (
            isinstance(type_hint, type)
            and (issubclass(type_hint, Path) or issubclass(type_hint, PurePath))
        )
    except TypeError:
        return False


def is_action_result_type(type_hint: Any) -> bool:
    """Check if a type hint is ActionResult or a subclass.

    Args:
        type_hint: The type hint to check

    Returns:
        True if the type is ActionResult or a subclass
    """
    try:
        return type_hint == ActionResult or (
            isinstance(type_hint, type) and issubclass(type_hint, ActionResult)
        )
    except TypeError:
        return False


def extract_metadata_from_annotated(type_hint: Any) -> tuple[Any, list[Any]]:
    """Extract the base type and metadata from an Annotated type hint.

    Args:
        type_hint: The type hint to extract from

    Returns:
        Tuple of (base_type, metadata_list)
    """
    origin = get_origin(type_hint)
    if origin is Annotated:
        args = get_args(type_hint)
        if args:
            return args[0], list(args[1:])
    return type_hint, []


# =============================================================================
# Internal Helper Functions
# =============================================================================


def _classify_special_type(type_hint: Any) -> Optional[str]:  # noqa: PLR0911
    """Classify a type hint as a special MADSci type.

    Args:
        type_hint: The type hint to classify

    Returns:
        String identifying the special type, or None if not special
    """
    # Check for LocationArgument
    if is_location_argument_type(type_hint):
        return "location"

    # Check for file types (Path and subclasses)
    if is_file_type(type_hint):
        return "file"

    # Check for ActionResult and subclasses
    if is_action_result_type(type_hint):
        return "action_result"

    # Check for ActionFiles
    try:
        if type_hint == ActionFiles or (
            isinstance(type_hint, type) and issubclass(type_hint, ActionFiles)
        ):
            return "action_files"
    except TypeError:
        # type_hint is not a class, so issubclass() raises TypeError; not ActionFiles
        pass

    # Check for ActionJSON
    try:
        if type_hint == ActionJSON or (
            isinstance(type_hint, type) and issubclass(type_hint, ActionJSON)
        ):
            return "action_json"
    except TypeError:
        # type_hint is not a class, so issubclass() raises TypeError; not ActionJSON
        pass

    # Check for ActionDatapoints
    try:
        if type_hint == ActionDatapoints or (
            isinstance(type_hint, type) and issubclass(type_hint, ActionDatapoints)
        ):
            return "action_datapoints"
    except TypeError:
        # type_hint is not a class, so issubclass() raises TypeError; not ActionDatapoints
        pass

    return None


def _analyze_union_type(
    type_hint: Any, args: tuple, depth: int, max_depth: int
) -> TypeInfo:
    """Analyze a Union type hint.

    Args:
        type_hint: The original type hint
        args: The Union arguments
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        TypeInfo for the union

    Raises:
        ValueError: If union contains conflicting special types
    """
    # Check if None is in the union (making it Optional)
    has_none = type(None) in args
    non_none_types = [arg for arg in args if arg is not type(None)]

    # If only one non-None type, this is Optional[T]
    if len(non_none_types) == 1:
        inner_info = analyze_type(non_none_types[0], depth + 1, max_depth)
        inner_info.is_optional = True
        return inner_info

    # Multiple non-None types - true union
    result = TypeInfo(
        base_type=type_hint,
        is_optional=has_none,
        is_union=True,
        union_types=non_none_types,
    )

    # Check for conflicting special types
    special_types = set()
    for arg in non_none_types:
        arg_info = analyze_type(arg, depth + 1, max_depth)
        if arg_info.special_type:
            special_types.add(arg_info.special_type)

    if len(special_types) > 1:
        raise ValueError(
            f"Union contains conflicting special types: {special_types}. "
            f"Cannot combine different special types in a single Union. "
            f"Type hint: {type_hint}"
        )

    # If there's a single special type across all union members, set it
    if len(special_types) == 1:
        result.special_type = special_types.pop()
        # Find the special type class
        for arg in non_none_types:
            if _classify_special_type(arg) == result.special_type:
                result.special_type_class = arg
                break

    return result


def _analyze_list_type(
    type_hint: Any, args: tuple, depth: int, max_depth: int
) -> TypeInfo:
    """Analyze a list[T] type hint.

    Args:
        type_hint: The original type hint
        args: The list arguments
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        TypeInfo for the list
    """
    result = TypeInfo(base_type=type_hint, is_list=True)

    if args:
        element_type = args[0]
        result.list_element_type = element_type

        # Analyze the element type to check for special types and metadata
        elem_info = analyze_type(element_type, depth + 1, max_depth)
        if elem_info.special_type:
            result.special_type = elem_info.special_type
            result.special_type_class = elem_info.special_type_class

        # Bubble up metadata from element type
        if elem_info.metadata:
            result.metadata.extend(elem_info.metadata)

    return result


def _analyze_dict_type(
    type_hint: Any, args: tuple, depth: int, max_depth: int
) -> TypeInfo:
    """Analyze a dict[K, V] type hint.

    Args:
        type_hint: The original type hint
        args: The dict arguments
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        TypeInfo for the dict
    """
    result = TypeInfo(base_type=type_hint, is_dict=True)

    if args and len(args) >= 2:
        result.dict_key_type = args[0]
        result.dict_value_type = args[1]

        # Analyze the value type to check for special types
        value_info = analyze_type(args[1], depth + 1, max_depth)
        if value_info.special_type:
            result.special_type = value_info.special_type
            result.special_type_class = value_info.special_type_class

    return result


def _analyze_tuple_type(
    type_hint: Any, args: tuple, _depth: int, _max_depth: int
) -> TypeInfo:
    """Analyze a tuple type hint.

    Args:
        type_hint: The original type hint
        args: The tuple arguments
        _depth: Current recursion depth (unused but kept for interface consistency)
        _max_depth: Maximum recursion depth (unused but kept for interface consistency)

    Returns:
        TypeInfo for the tuple
    """
    result = TypeInfo(base_type=type_hint, is_tuple=True)

    if args:
        result.tuple_element_types = args

    return result
