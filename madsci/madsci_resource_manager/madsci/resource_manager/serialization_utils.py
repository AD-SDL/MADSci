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

    # Handle the `children` field if it exists
    if hasattr(resource, "children") and resource.children:
        if isinstance(resource.children, dict):
            # Serialize children recursively for dictionary-type children
            resource_dict["children"] = {
                key: serialize_resource(child) if isinstance(child, ResourceBase) else child
                for key, child in resource.children.items()
            }
        elif isinstance(resource.children, list):
            # For `Stack` and `Queue`, store only the resource IDs
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
    # Get the resource type and corresponding class
    resource_class = map_resource_type(data)

    # Recursively reconstruct `children` if it exists
    if "children" in data:
        if isinstance(data["children"], dict):
            # Ensure children is a proper dictionary and recursively deserialize
            deserialized_children = {}
            for key, child in data["children"].items():
                if isinstance(child, dict):  # Check if it's a serialized child
                    deserialized_children[key] = deserialize_resource(child)
                else:
                    deserialized_children[key] = child  # Non-dict children (e.g., strings or IDs)
            data["children"] = deserialized_children
        elif isinstance(data["children"], list):
            # Leave lists as-is (for `Stack` and `Queue`, which use resource IDs)
            pass

    # Debugging: Log the deserialized data
    print(f"Deserialized resource data: {data}")

    # Create the resource instance
    return resource_class(**data)