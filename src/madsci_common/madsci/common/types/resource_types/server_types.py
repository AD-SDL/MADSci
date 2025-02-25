"""Types used by the Resource Manager's Server"""


from typing import Optional, Union

from madsci.common.types.base_types import BaseModel
from madsci.common.types.resource_types import (
    GridIndex2D,
    GridIndex3D,
    ResourceDataModels,
)
from pydantic import model_validator
from pydantic.types import datetime


class ResourceGetQuery(BaseModel):
    """A request to get a resource from the database."""
    resource_id: Optional[str] = None
    """The ID of the resource"""
    resource_name: Optional[str] = None
    """The name of the resource."""
    parent_id: Optional[str] = None
    """The ID of the parent resource"""
    resource_type: Optional[str] = None
    """The custom type of the resource."""
    resource_base_type: Optional[str] = None
    """The base type of the resource"""
    unique: Optional[bool] = False
    """Whether to require a unique resource or not."""
    multiple: Optional[bool] = False
    """Whether to return multiple resources or just the first."""

class ResourceHistoryGetQuery(BaseModel):
    """A request to get the history of a resource from the database."""
    resource_id: Optional[str] = None
    """The ID of the resource."""
    version: Optional[int] = None
    """The version of the resource."""
    removed: Optional[bool] = None
    """Whether the resource was removed."""
    change_type: Optional[str] = None
    """The type of change to the resource."""
    start_date: Optional[datetime] = None
    """The start a range from which to get history. If not specified, all history before the end date is returned."""
    end_date: Optional[datetime] = None
    """The end of a range from which to get history. If not specified, all history after the start date is returned."""
    limit: Optional[int] = None
    """The maximum number of entries to return."""

class PushResourceBody(BaseModel):
    """A request to push a resource to the database."""

    child_id: Optional[str] = None
    """The ID of the child resource."""
    child: Optional[ResourceDataModels] = None
    """The child resource data."""

    @model_validator(mode="before")
    @classmethod
    def validate_push_resource(cls, values: dict) -> dict:
        """Ensure that either a child ID or child resource data is provided."""
        if not values.get("child_id") and not values.get("child"):
            raise ValueError("Either a child ID or child resource data must be provided.")
        return values

class SetChildBody(BaseModel):
    """A request to set a child resource."""

    key: Union[str, GridIndex2D, GridIndex3D]
    """The key to identify the child resource's location in the parent container. If the parent is a grid/voxel grid, the key should be a 2D or 3D index."""
    child: Union[str, ResourceDataModels]
    """The ID of the child resource or the child resource data."""

class RemoveChildBody(BaseModel):
    """A request to remove a child resource."""

    key: Union[str, GridIndex2D, GridIndex3D]
    """The key to identify the child resource's location in the parent container. If the parent is a grid/voxel grid, the key should be a 2D or 3D index."""
