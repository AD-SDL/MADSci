"""Common validators for MADSci-derived types."""

from typing import Any, Callable, Union

from pydantic import ValidationInfo
from ulid import ULID


def ulid_validator(id: str, info: ValidationInfo) -> str:
    """Validates that a string field is a valid ULID."""
    try:
        ULID.from_str(id)
        return id
    except ValueError as e:
        raise ValueError(f"Invalid ULID {id} for field {info.field_name}") from e


def optional_ulid_validator(id: Union[str, None], info: ValidationInfo) -> str:
    """Validates that a string field is a valid ULID."""
    if id is None:
        return id
    try:
        ULID.from_str(id)
        return id
    except ValueError as e:
        raise ValueError(f"Invalid ULID {id} for field {info.field_name}") from e


def alphanumeric_with_underscores_validator(v: str, info: ValidationInfo) -> str:
    """Validates that a string field is alphanumeric with underscores."""
    if not str(v).replace("_", "").isalnum():
        raise ValueError(
            f"Field {info.field_name} must contain only alphanumeric characters and underscores",
        )
    return v


def create_dict_promoter(
    key_func: Callable[[Any], str],
) -> Callable[[Any], dict[str, Any]]:
    """Creates a validator that promotes a list to a dictionary using a specified attribute as the key.

    Example usage:
        from pydantic import field_validator
        validate_nodes_to_dict = field_validator("nodes", mode="before")(create_dict_promoter("node_name"))
    """

    def list_to_dict(lst: Union[list[Any], dict[str, Any]]) -> dict[str, Any]:
        """Promotes a list to a dictionary using a specified attribute as the key."""
        if isinstance(lst, dict):
            return lst
        return {key_func(item): item for item in lst}

    return list_to_dict
