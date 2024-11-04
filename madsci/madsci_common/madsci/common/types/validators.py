"""Common validators for MADSci-derived types."""

from pydantic import ValidationInfo
from ulid import ULID


def ulid_validator(id: str, info: ValidationInfo) -> str:
    """Validates that a string field is a valid ULID."""
    try:
        ULID.from_str(id)
        return id
    except ValueError as e:
        raise ValueError(f"Invalid ULID {id} for field {info.field_name}") from e


def alphanumeric_with_underscores_validator(v: str, info: ValidationInfo) -> str:
    """Validates that a string field is alphanumeric with underscores."""
    if not str(v).replace("_", "").isalnum():
        raise ValueError(
            f"Field {info.field_name} must contain only alphanumeric characters and underscores"
        )
    return v
