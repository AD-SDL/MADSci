"""Resource table objects"""

from datetime import datetime
from typing import Optional, Union

from madsci.common.types.resource_types import (
    RESOURCE_TYPE_MAP,
    ResourceBase,
    ResourceBaseTypes,
    ResourceDataModels,
)
from pydantic.config import ConfigDict
from sqlalchemy import event
from sqlalchemy.sql.schema import FetchedValue, UniqueConstraint
from sqlalchemy.sql.sqltypes import TIMESTAMP, Numeric
from sqlmodel import (
    Field,
    Relationship,
    Session,
    text,
)


class ResourceTableBase(ResourceBase):
    """
    Base class for all resource-based tables.
    """

    model_config = ConfigDict(
        validate_assignment=False,
    )

    parent_id: Optional[str] = Field(
        title="Parent Resource ID",
        description="The ID of the parent resource.",
        nullable=True,
        default=None,
        foreign_key="resource.resource_id",
    )
    key: Optional[str] = Field(
        title="Resource Key",
        description="The key to identify the child resource's location in the parent container.",
        nullable=True,
        default=None,
    )
    quantity: Optional[Union[float, int]] = Field(
        title="Quantity",
        description="The quantity of the resource, if any.",
        nullable=True,
        default=None,
        sa_type=Numeric,
    )
    capacity: Optional[Union[float, int]] = Field(
        title="Capacity",
        description="The maximum capacity of the resource, if any.",
        nullable=True,
        default=None,
        sa_type=Numeric,
    )
    row_dimension: Optional[int] = Field(
        title="Row Dimension",
        description="The size of a row (used by Grids and Voxel Grids).",
        nullable=True,
        default=None,
        sa_type=Numeric,
    )
    column_dimension: Optional[int] = Field(
        title="Column Dimension",
        description="The size of a column (used by Grids and Voxel Grids).",
        nullable=True,
        default=None,
        sa_type=Numeric,
    )
    layer_dimension: Optional[int] = Field(
        title="Layer Dimension",
        description="The size of a layer (used by Voxel Grids).",
        nullable=True,
        default=None,
        sa_type=Numeric,
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

    def to_data_model(self, include_children: bool = True) -> ResourceDataModels:
        """
        Convert the table entry to a data model.

        Returns:
            ResourceDataModels: The resource data model.
        """
        resource: ResourceDataModels = RESOURCE_TYPE_MAP[self.base_type][
            "model"
        ].model_validate(**self.model_dump())
        if self.children and include_children:
            flat_children = {}
            for key, child in self.children.items():
                flat_children[key] = child.to_data_model()
            resource.children = resource.populate_children(flat_children)
        return resource


class ResourceTable(ResourceTableBase, table=True):
    """The table for storing information about active Resources, with various utility methods."""

    __tablename__ = "resource"

    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "key",
            name="uix_parent_key",
        ),  # * Prevent Two Children with Same Key in the same Parent
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

    def _remove(self, session: Session, commit: bool = True) -> None:
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.removed = True
        session.merge(self)
        if commit:
            session.commit()

    @classmethod
    def from_data_model(
        cls, resource: Union[ResourceDataModels, ResourceBaseTypes]
    ) -> "ResourceTable":
        """
        Create a table entry from a data model.

        Args:
            ResourceTable: a SQL model entry corresponding to a row related to the .
        """
        return cls.model_validate(**resource.model_dump())

    def to_data_model(self, include_children: bool = True) -> ResourceDataModels:
        """
        Convert the table entry to a data model.

        Returns:
            ResourceDataModels: The resource data model.
        """
        resource: ResourceDataModels = RESOURCE_TYPE_MAP[self.base_type][
            "model"
        ].model_validate(self.model_dump())
        if self.children and include_children:
            flat_children = {}
            for key, child in self.children.items():
                flat_children[key] = child.to_data_model()
            resource.children = resource.populate_children(flat_children)
        return resource


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
    changed: Optional[datetime] = Field(
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
    parent_id: Optional[str] = Field(
        title="Parent Resource ID",
        description="The ID of the parent resource.",
        nullable=True,
        default=None,
    )

    @classmethod
    def from_data_model(
        cls, resource: Union[ResourceDataModels, ResourceBaseTypes]
    ) -> "ResourceHistoryTable":
        """
        Create a table entry from a data model.

        Args:
            ResourceTable: a SQL model entry corresponding to a row related to the .
        """
        return cls.model_validate(resource.model_dump())


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
                history = ResourceHistoryTable.from_data_model(obj.to_data_model())
                session.add(history)
        for obj in session.dirty:
            if isinstance(obj, ResourceTable):
                history = ResourceHistoryTable.from_data_model(obj.to_data_model())
                session.add(history)
        for obj in session.deleted:
            if isinstance(obj, ResourceTable):
                data_model = obj.to_data_model()
                data_model.removed = True
                history = ResourceHistoryTable.from_data_model(data_model)
                session.add(history)
