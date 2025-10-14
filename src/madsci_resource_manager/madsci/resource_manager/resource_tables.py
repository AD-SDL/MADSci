"""Resource table objects"""

from datetime import datetime
from typing import Any, Optional

from madsci.common.types.resource_types import (
    RESOURCE_TYPE_MAP,
    CustomResourceAttributeDefinition,  # noqa: F401
    Resource,
    ResourceDataModels,
    ResourceTypeEnum,
)
from pydantic.config import ConfigDict
from pydantic.types import Decimal
from sqlalchemy import Index, event
from sqlalchemy.sql.schema import FetchedValue, UniqueConstraint
from sqlalchemy.sql.sqltypes import TIMESTAMP, Numeric
from sqlmodel import (
    JSON,
    Enum,
    Field,
    Relationship,
    Session,
    text,
)
from typing_extensions import Self  # type: ignore


def create_session(*args: Any, **kwargs: Any) -> Session:
    """Create a new SQLModel session."""
    session = Session(*args, **kwargs)
    add_automated_history(session)
    return session


def add_automated_history(session: Session) -> None:
    """
    Add automated history to the session.

    Args:
        session (Session): SQLAlchemy session.
    """

    @event.listens_for(session, "before_flush")
    def before_flush(session: Session, flush_context, instances) -> None:  # noqa: ANN001, ARG001
        for obj in session.new:
            if isinstance(obj, ResourceTable):
                history = ResourceHistoryTable.model_validate(obj)
                history.change_type = "Added"
                session.add(history)
        for obj in session.dirty:
            if isinstance(obj, ResourceTable):
                history = ResourceHistoryTable.model_validate(obj)
                history.change_type = "Updated"
                session.add(history)
        for obj in session.deleted:
            if isinstance(obj, ResourceTable):
                child_ids = delete_descendants(session, obj)
                history = ResourceHistoryTable.model_validate(obj)
                history.change_type = "Removed"
                history.removed = True
                history.child_ids = child_ids
                session.add(history)


def delete_descendants(session: Session, resource_entry: "ResourceTable") -> list[str]:
    """
    Recursively delete all children of a resource entry.
    Args:
        session (Session): SQLAlchemy session.
        resource_entry (ResourceTable): The resource entry.
    """
    child_ids = [child.resource_id for child in resource_entry.children_list]
    for child in resource_entry.children_list:
        grandchild_ids = delete_descendants(session, child)
        history = ResourceHistoryTable.model_validate(child)
        history.change_type = "Removed"
        history.removed = True
        history.child_ids = grandchild_ids
        session.add(history)
        session.delete(child)
    return child_ids


class ResourceTableBase(Resource):
    """
    Base class for all resource-based tables.
    """

    model_config = ConfigDict(
        validate_assignment=False,
        extra="ignore",
    )

    parent_id: Optional[str] = Field(
        title="Parent Resource ID",
        description="The ID of the parent resource.",
        nullable=True,
        default=None,
        foreign_key="resource.resource_id",
    )
    base_type: str = Field(
        title="Base Type",
        description="The base type of the resource.",
        nullable=False,
        sa_type=Enum(ResourceTypeEnum),
        default=ResourceTypeEnum.resource,
    )

    owner: dict[str, str] = Field(
        title="Owner",
        description="The ownership info for the resource",
        sa_type=JSON,
        default_factory=dict,
    )
    key: Optional[str] = Field(
        title="Resource Key",
        description="The key to identify the child resource's location in the parent container.",
        nullable=True,
        default=None,
    )
    quantity: Optional[Decimal] = Field(
        title="Quantity",
        description="The quantity of the resource, if any.",
        nullable=True,
        default=None,
        sa_type=Numeric,
    )
    capacity: Optional[Decimal] = Field(
        title="Capacity",
        description="The maximum capacity of the resource, if any.",
        nullable=True,
        default=None,
        sa_type=Numeric,
    )
    columns: Optional[int] = Field(
        title="Number of Columns",
        description="The size of a row (used by Grids and Voxel Grids).",
        nullable=True,
        default=None,
    )
    rows: Optional[int] = Field(
        title="Number of Rows",
        description="The size of a column (used by Grids and Voxel Grids).",
        nullable=True,
        default=None,
    )
    layers: Optional[int] = Field(
        title="Number of Layers",
        description="The size of a layer (used by Voxel Grids).",
        nullable=True,
        default=None,
    )
    created_at: Optional[datetime] = Field(
        title="Created Datetime",
        description="The timestamp of when the resource was created.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    template_name: Optional[str] = Field(
        title="Template Name",
        description="Name of the template this resource was created from.",
        nullable=True,
        default=None,
    )
    locked_until: Optional[datetime] = Field(
        title="Locked Until",
        description="Timestamp when the resource lock expires.",
        nullable=True,
        default=None,
        sa_type=TIMESTAMP(timezone=True),
    )
    locked_by: Optional[str] = Field(
        title="Locked By",
        description="Identifier of the client/session that locked the resource.",
        nullable=True,
        default=None,
    )

    def to_data_model(self, include_children: bool = True) -> ResourceDataModels:
        """
        Convert the table entry to a data model.

        Returns:
            ResourceDataModels: The resource data model.
        """
        try:
            resource: ResourceDataModels = RESOURCE_TYPE_MAP[self.base_type][
                "model"
            ].model_validate(self.model_dump(exclude={"children"}))
        except KeyError as e:
            raise ValueError(
                f"Resource Type {self.base_type} not found in RESOURCE_TYPE_MAP"
            ) from e
        if getattr(self, "children", None) and include_children:
            flat_children = {}
            for key, child in self.children.items():
                flat_children[key] = child.to_data_model()
            if flat_children and hasattr(resource, "children"):
                resource.populate_children(flat_children)

        return resource

    @classmethod
    def from_data_model(cls, resource: ResourceDataModels) -> Self:
        """Create a new Resource Table entry from a resource data model."""
        return cls.model_validate(resource.model_dump(mode="json"))


class ResourceTable(ResourceTableBase, table=True):
    """The table for storing information about active Resources, with various utility methods."""

    __tablename__ = "resource"

    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "key",
            name="uix_parent_key",
        ),  # * Prevent Two Children with Same Key in the same Parent
        Index(
            "idx_resource_locks", "locked_until", "locked_by"
        ),  # Add index for efficient lock queries
    )

    parent: Optional["ResourceTable"] = Relationship(
        back_populates="children_list",
        sa_relationship_kwargs={"remote_side": "ResourceTable.resource_id"},
    )
    updated_at: Optional[datetime] = Field(
        title="Updated Datetime",
        description="The timestamp of when the resource was last updated.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
            "server_onupdate": FetchedValue(),
        },
    )
    children_list: list["ResourceTable"] = Relationship(back_populates="parent")

    @property
    def children(self) -> dict[str, "ResourceTable"]:
        """
        Get the children resources as a dictionary.

        Returns:
            dict: Dictionary of children resources.
        """
        return {child.key: child for child in self.children_list}

    def check_no_recursive_parent(self) -> None:
        """
        Check for recursive parent relationships (cycles) in the parent chain.
        Raises ValueError if a cycle is detected.
        """
        visited = set()
        current = self
        while current.parent is not None:
            parent_id = getattr(current.parent, "resource_id", None)
            if parent_id is None:
                break
            if parent_id == self.resource_id or parent_id in visited:
                raise ValueError(
                    f"Recursive parent relationship detected for resource_id {self.resource_id}"
                )
            visited.add(parent_id)
            current = current.parent


# Add event listener to check for recursive parent relationships before flush
@event.listens_for(Session, "before_flush")
def prevent_recursive_parent_relationships(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    """
    Event listener to prevent recursive parent relationships in ResourceTable before flush.
    Raises ValueError if a cycle is detected.
    """
    for obj in session.new.union(session.dirty):
        if isinstance(obj, ResourceTable):
            obj.check_no_recursive_parent()


class ResourceHistoryTable(ResourceTableBase, table=True):
    """The table for storing information about historical Resources."""

    __tablename__ = "resource_history"

    version: Optional[int] = Field(
        title="Version",
        description="The version of the resource.",
        default=None,
        primary_key=True,
        sa_column_kwargs={
            "autoincrement": True,
        },
    )
    updated_at: Optional[datetime] = Field(
        title="Updated Datetime",
        description="The timestamp of when the resource was last updated.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    changed_at: Optional[datetime] = Field(
        title="Changed Datetime",
        description="The timestamp of when the resource history was captured.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
            "server_onupdate": FetchedValue(),
        },
    )
    change_type: str = Field(
        title="Change Type",
        description="Information about the change being recorded.",
        default="",
        nullable=False,
    )
    parent_id: Optional[str] = Field(
        title="Parent Resource ID",
        description="The ID of the parent resource.",
        nullable=True,
        default=None,
    )
    child_ids: Optional[list[str]] = Field(
        title="Child Resource IDs",
        description="The IDs of the child resources that were removed along with this resource (if any).",
        nullable=True,
        default=None,
        sa_type=JSON,
    )


class ResourceTemplateTable(ResourceTableBase, table=True):
    """The table for storing Resource Template definitions."""

    __tablename__ = "resource_template"

    template_name: str = Field(
        title="Template Name",
        description="Unique identifier and display name for the template.",
        unique=True,
        nullable=False,
    )
    description: str = Field(
        title="Description",
        description="Detailed description of what this template creates.",
        nullable=False,
    )
    base_type: str = Field(
        title="Base Type",
        description="The base resource type this template creates.",
        nullable=False,
        sa_type=Enum(ResourceTypeEnum),
    )
    resource_class: str = Field(
        title="Resource Class",
        description="The specific resource class for this template.",
        nullable=False,
    )
    default_values: dict[str, Any] = Field(
        title="Default Values",
        description="Default values to apply when creating resources from this template.",
        sa_type=JSON,
        default_factory=dict,
    )
    required_overrides: list[str] = Field(
        title="Required Overrides",
        description="List of fields that must be provided when using this template.",
        sa_type=JSON,
        default_factory=list,
    )
    tags: list[str] = Field(
        title="Tags",
        description="Tags for categorizing and searching templates.",
        sa_type=JSON,
        default_factory=list,
    )
    created_by: Optional[str] = Field(
        title="Created By",
        description="Identifier of the node/user that created this template.",
        nullable=True,
        default=None,
    )
    version: str = Field(
        title="Template Version",
        description="Version string for template compatibility tracking.",
        nullable=False,
        default="1.0.0",
    )
    updated_at: Optional[datetime] = Field(
        title="Updated Datetime",
        description="The timestamp of when the template was last updated.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
            "server_onupdate": FetchedValue(),
        },
    )
