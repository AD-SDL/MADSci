Module madsci.node_module.type_analyzer
=======================================
Type analysis utilities for MADSci action parsing.

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

Functions
---------

`analyze_type(type_hint: Any, depth: int = 0, max_depth: int = 20) ‑> madsci.node_module.type_analyzer.TypeInfo`
:   Recursively analyze a type hint to extract all relevant information.

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

`extract_metadata_from_annotated(type_hint: Any) ‑> tuple[typing.Any, list[typing.Any]]`
:   Extract the base type and metadata from an Annotated type hint.

    Args:
        type_hint: The type hint to extract from

    Returns:
        Tuple of (base_type, metadata_list)

`is_action_result_type(type_hint: Any) ‑> bool`
:   Check if a type hint is ActionResult or a subclass.

    Args:
        type_hint: The type hint to check

    Returns:
        True if the type is ActionResult or a subclass

`is_file_type(type_hint: Any) ‑> bool`
:   Check if a type hint represents a file parameter (Path or subclass).

    Args:
        type_hint: The type hint to check

    Returns:
        True if the type is Path, PurePath, or subclass

`is_location_argument_type(type_hint: Any) ‑> bool`
:   Check if a type hint contains LocationArgument at any level.

    Args:
        type_hint: The type hint to check

    Returns:
        True if LocationArgument is the base type

`is_optional_type(type_hint: Any) ‑> bool`
:   Check if a type hint represents an Optional type (Union with None).

    Args:
        type_hint: The type hint to check

    Returns:
        True if the type is Optional[T] or Union[T, None]

Classes
-------

`TypeInfo(base_type: Any, is_optional: bool = False, is_union: bool = False, is_list: bool = False, is_dict: bool = False, is_tuple: bool = False, list_element_type: Optional[Any] = None, dict_key_type: Optional[Any] = None, dict_value_type: Optional[Any] = None, tuple_element_types: Optional[tuple[Any, ...]] = None, union_types: Optional[list[Any]] = None, metadata: list[Any] = <factory>, special_type: Optional[str] = None, special_type_class: Optional[type] = None)`
:   Complete information about an analyzed type hint.

    This dataclass contains all relevant information extracted from a type hint
    through recursive analysis, including type characteristics, container details,
    union types, metadata from Annotated, and special type classification.

    ### Instance variables

    `base_type: Any`
    :

    `dict_key_type: Any | None`
    :

    `dict_value_type: Any | None`
    :

    `is_dict: bool`
    :

    `is_list: bool`
    :

    `is_optional: bool`
    :

    `is_tuple: bool`
    :

    `is_union: bool`
    :

    `list_element_type: Any | None`
    :

    `metadata: list[typing.Any]`
    :

    `special_type: str | None`
    :

    `special_type_class: type | None`
    :

    `tuple_element_types: tuple[typing.Any, ...] | None`
    :

    `union_types: list[typing.Any] | None`
    :
