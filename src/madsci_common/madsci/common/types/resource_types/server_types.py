"""Types used by the Resource Manager's Server"""

from typing import Any, Optional, Union

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.resource_types import (
    GridIndex,
    GridIndex2D,
    GridIndex3D,
    ResourceDataModels,
)
from pydantic import model_validator
from pydantic.config import ConfigDict
from pydantic.types import datetime


class ResourceRequestBase(MadsciBaseModel):
    """Base class for all resource request models."""

    model_config = ConfigDict(
        extra="forbid",
    )


class ResourceGetQuery(ResourceRequestBase):
    """A request to get a resource from the database."""

    resource_id: Optional[str] = None
    """The ID of the resource"""
    resource_name: Optional[str] = None
    """The name of the resource."""
    resource_description: Optional[str] = None
    """The description of the resource."""
    parent_id: Optional[str] = None
    """The ID of the parent resource"""
    resource_class: Optional[str] = None
    """The class of the resource."""
    base_type: Optional[str] = None
    """The base type of the resource"""
    owner: Optional[OwnershipInfo] = None
    """The owner(s) of the resource"""
    unique: Optional[bool] = False
    """Whether to require a unique resource or not."""
    multiple: Optional[bool] = True
    """Whether to return multiple resources or just the first."""


class ResourceHistoryGetQuery(ResourceRequestBase):
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


class PushResourceBody(ResourceRequestBase):
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
            raise ValueError(
                "Either a child ID or child resource data must be provided."
            )
        return values


class SetChildBody(ResourceRequestBase):
    """A request to set a child resource."""

    key: Union[str, GridIndex, GridIndex2D, GridIndex3D]
    """The key to identify the child resource's location in the parent container. If the parent is a grid/voxel grid, the key should be a 2D or 3D index."""
    child: Union[str, ResourceDataModels]
    """The ID of the child resource or the child resource data."""


class RemoveChildBody(ResourceRequestBase):
    """A request to remove a child resource."""

    key: Union[str, GridIndex2D, GridIndex3D]
    """The key to identify the child resource's location in the parent container. If the parent is a grid/voxel grid, the key should be a 2D or 3D index."""


class TemplateCreateBody(ResourceRequestBase):
    """A request to create a template from a resource."""

    resource: ResourceDataModels
    """The resource to use as a template."""
    template_name: str
    """Unique name for the template."""
    description: Optional[str] = ""
    """Description of what this template creates."""
    required_overrides: Optional[list[str]] = None
    """Fields that must be provided when using template."""
    tags: Optional[list[str]] = None
    """Tags for categorization."""
    created_by: Optional[str] = None
    """Creator identifier."""
    version: Optional[str] = "1.0.0"
    """Template version."""


class TemplateGetQuery(ResourceRequestBase):
    """A request to list/filter templates."""

    base_type: Optional[str] = None
    """Filter by base resource type."""
    tags: Optional[list[str]] = None
    """Filter by templates that have any of these tags."""
    created_by: Optional[str] = None
    """Filter by creator."""


class TemplateUpdateBody(ResourceRequestBase):
    """A request to update a template."""

    updates: dict[str, Any]
    """Fields to update."""


class CreateResourceFromTemplateBody(ResourceRequestBase):
    """A request to create a resource from a template."""

    resource_name: str
    """Name for the new resource."""
    overrides: Optional[dict[str, Any]] = None
    """Values to override template defaults."""
    add_to_database: Optional[bool] = True
    """Whether to add the resource to the database."""
