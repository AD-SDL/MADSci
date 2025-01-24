from typing import Any, Dict
from db_tables import map_resource_type, ResourceBase


def serialize_resource(resource: ResourceBase) -> Dict[str, Any]:
    """
    Recursively serialize a resource, including its `children`.

    Args:
        resource (ResourceBase): The resource to serialize.

    Returns:
        dict: Serialized dictionary of the resource.
    """
    resource_dict = resource.dict()
    if hasattr(resource, "children") and resource.children:
        if isinstance(resource.children, dict):
            resource_dict["children"] = {
                key: serialize_resource(child) if isinstance(child, ResourceBase) else child
                for key, child in resource.children.items()
            }
        elif isinstance(resource.children, list):
            resource_dict["children"] = list(resource.children)
    return resource_dict

def deserialize_resource(data: Dict[str, Any]) -> ResourceBase:
    """
    Recursively deserialize a resource dictionary into a `ResourceBase` object.

    Args:
        data (dict): Serialized dictionary of the resource.

    Returns:
        ResourceBase: Reconstructed resource object.
    """
    resource_class = map_resource_type(data)
    if "children" in data:
        if isinstance(data["children"], dict):
            data["children"] = {
                key: deserialize_resource(child) if isinstance(child, dict) else child
                for key, child in data["children"].items()
            }
        elif isinstance(data["children"], list):
            pass
    return resource_class(**data)