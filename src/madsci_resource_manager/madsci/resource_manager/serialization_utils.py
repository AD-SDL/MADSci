"""Serialization Methods"""

from typing import Any

from madsci.resource_manager.resource_tables import ResourceBase, map_resource_type


def serialize_resource(resource: ResourceBase) -> dict[str, Any]:
    """
    Recursively serialize a resource, including its `children`, converting
    datetime objects to ISO-formatted strings.

    Args:
        resource (ResourceBase): The resource to serialize.

    Returns:
        dict: A serialized dictionary representation of the resource.
    """
    return resource.model_dump(mode="json")


def deserialize_resource(data: dict[str, Any]) -> ResourceBase:
    """
    Recursively deserialize a resource dictionary into a `ResourceBase` object,
    converting ISO datetime strings back to datetime objects.

    Args:
        data (dict): Serialized dictionary of the resource.

    Returns:
        ResourceBase: Reconstructed resource object.
    """
    resource_class: ResourceBase = map_resource_type(data)
    return resource_class.model_validate(data)
