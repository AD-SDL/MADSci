Module madsci.common.serializers
================================
Custom serializers for use in MADSci dataclasses.

Functions
---------

`dict_to_list(dct: list[typing.Any] | dict[str, typing.Any]) ‑> list[typing.Any]`
:   Converts a dictionary to a list of values.

    Example Usage:
        from pydantic import field_serializer

        serialize_nodes_to_list = field_serializer("nodes")(dict_to_list)

`serialize_to_yaml(model: MadsciBaseModel) ‑> str`
:   Serialize a MADSci model to YAML string.

    Args:
        model: The MADSci model to serialize

    Returns:
        YAML string representation of the model

    Example:
        from madsci.common.serializers import serialize_to_yaml

        yaml_content = serialize_to_yaml(my_pydantic_model)
