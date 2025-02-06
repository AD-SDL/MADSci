import datetime
from typing import Any, Dict
from madsci.madsci_resource_manager.madsci.resource_manager.resource_tables import map_resource_type, ResourceBase

def _convert_datetime(value: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings,
    and process dictionaries and lists.
    """
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _convert_datetime(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_convert_datetime(item) for item in value]
    else:
        return value

def _restore_datetime(value: Any) -> Any:
    """
    Recursively convert ISO format strings to datetime objects.
    If conversion fails (i.e. the string is not a datetime), return the value unchanged.
    """
    if isinstance(value, str):
        try:
            # Attempt to convert the string back to a datetime object.
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            return value
    elif isinstance(value, dict):
        return {k: _restore_datetime(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_restore_datetime(item) for item in value]
    else:
        return value

def serialize_resource(resource: ResourceBase) -> Dict[str, Any]:
    """
    Recursively serialize a resource, including its `children`, converting
    datetime objects to ISO-formatted strings.
    
    Args:
        resource (ResourceBase): The resource to serialize.
    
    Returns:
        dict: A serialized dictionary representation of the resource.
    """
    resource_dict = resource.dict()
    # Convert any datetime objects in the resource dictionary
    resource_dict = _convert_datetime(resource_dict)
    
    if hasattr(resource, "children") and resource.children:
        if isinstance(resource.children, dict):
            resource_dict["children"] = {
                key: serialize_resource(child) if isinstance(child, ResourceBase) else _convert_datetime(child)
                for key, child in resource.children.items()
            }
        elif isinstance(resource.children, list):
            resource_dict["children"] = [
                serialize_resource(child) if isinstance(child, ResourceBase) else _convert_datetime(child)
                for child in resource.children
            ]
    return resource_dict

def deserialize_resource(data: Dict[str, Any]) -> ResourceBase:
    """
    Recursively deserialize a resource dictionary into a `ResourceBase` object,
    converting ISO datetime strings back to datetime objects.
    
    Args:
        data (dict): Serialized dictionary of the resource.
    
    Returns:
        ResourceBase: Reconstructed resource object.
    """
    # First, process the children field if it exists.
    if "children" in data:
        children_data = data["children"]
        if isinstance(children_data, dict):
            data["children"] = {
                key: deserialize_resource(child) if isinstance(child, dict) else child
                for key, child in children_data.items()
            }
        elif isinstance(children_data, list):
            data["children"] = [
                deserialize_resource(child) if isinstance(child, dict) else child
                for child in children_data
            ]
    
    # For all other fields, attempt to restore datetime values.
    for key, value in data.items():
        if key != "children":
            data[key] = _restore_datetime(value)
    
    resource_class = map_resource_type(data)
    return resource_class(**data)