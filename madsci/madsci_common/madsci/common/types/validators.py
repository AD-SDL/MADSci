"""Common validators for MADSci-derived types."""

from pydantic import ValidationError, ValidationInfo
from ulid import ULID


def ulid_validator(id: str, info: ValidationInfo) -> str:
    """Validates that a string field is a valid ULID."""
    try:
        ULID.from_str(id)
        return id
    except ValueError as e:
        raise ValidationError(f"Invalid ULID {id} for field {info.field_name}") from e
