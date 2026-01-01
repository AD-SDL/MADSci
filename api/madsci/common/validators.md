Module madsci.common.validators
===============================
Common validators for MADSci-derived types.

Functions
---------

`alphanumeric_with_underscores_validator(v: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
:   Validates that a string field is alphanumeric with underscores.

`create_dict_promoter(key_func: Callable[[Any], str]) ‑> Callable[[Any], dict[str, Any]]`
:   Creates a validator that promotes a list to a dictionary using a specified attribute as the key.

    Example usage:
        from pydantic import field_validator
        validate_nodes_to_dict = field_validator("nodes", mode="before")(create_dict_promoter("node_name"))

`optional_ulid_validator(id: str | None, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
:   Validates that a string field is a valid ULID.

`ulid_validator(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
:   Validates that a string field is a valid ULID.
