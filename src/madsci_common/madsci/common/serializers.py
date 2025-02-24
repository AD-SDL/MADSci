"""Custom serializers for use in MADSci dataclasses."""

from typing import Any, Union


def dict_to_list(dct: Union[list[Any], dict[str, Any]]) -> list[Any]:
    """Converts a dictionary to a list of values.

    Example Usage:
        from pydantic import field_serializer

        serialize_nodes_to_list = field_serializer("nodes")(dict_to_list)
    """
    if isinstance(dct, list):
        return dct
    return list(dct.values())
