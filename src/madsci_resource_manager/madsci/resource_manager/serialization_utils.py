"""Serialization Methods"""

from typing import Any

from madsci.resource_manager.resource_tables import Resource, map_resource_type


def serialize_resource(resource: Resource) -> dict[str, Any]:
    """
    Recursively serialize a resource, including its `children`, converting
    datetime objects to ISO-formatted strings.

    Args:
        resource (Resource): The resource to serialize.

    Returns:
        dict: A serialized dictionary representation of the resource.
    """
    return resource.model_dump(mode="json")


def deserialize_resource(data: dict[str, Any]) -> Resource:
    """
    Recursively deserialize a resource dictionary into a `Resource` object,
    converting ISO datetime strings back to datetime objects.

    Args:
        data (dict): Serialized dictionary of the resource.

    Returns:
        Resource: Reconstructed resource object.
    """
    resource_class: Resource = map_resource_type(data)
    return resource_class.validate_subtype(data)
