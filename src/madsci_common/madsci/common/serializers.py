"""Custom serializers for use in MADSci dataclasses."""

from typing import TYPE_CHECKING, Any, Union

import yaml

if TYPE_CHECKING:
    from madsci.common.types.base_types import MadsciBaseModel


def serialize_to_yaml(model: "MadsciBaseModel") -> str:
    """Serialize a MADSci model to YAML string.

    Args:
        model: The MADSci model to serialize

    Returns:
        YAML string representation of the model

    Example:
        from madsci.common.serializers import serialize_to_yaml

        yaml_content = serialize_to_yaml(my_pydantic_model)
    """
    return yaml.dump(
        model.model_dump(mode="json"),
        indent=2,
        sort_keys=False,
    )


def dict_to_list(dct: Union[list[Any], dict[str, Any]]) -> list[Any]:
    """Converts a dictionary to a list of values.

    Example Usage:
        from pydantic import field_serializer

        serialize_nodes_to_list = field_serializer("nodes")(dict_to_list)
    """
    if isinstance(dct, list):
        return dct
    return list(dct.values())
