"""Resource table objects"""

from datetime import datetime
from typing import Optional, Self, Union

from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.resource_types import (
    RESOURCE_TYPE_MAP,
    ResourceBase,
    ResourceBaseTypes,
    ResourceDataModels,
)
from pydantic.config import ConfigDict
from sqlalchemy.sql.schema import FetchedValue
from sqlalchemy.sql.sqltypes import TIMESTAMP, Numeric
from sqlmodel import (
    Field,
    Relationship,
    Session,
    UniqueConstraint,
    select,
    text,
)


class AutomatedTimeFieldMixin:
    """Handle automatic created_at and updated_at fields."""

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


class ManualTimeFieldMixin:
    """Non-automaticly updated timestamp mixin."""

    created_at: Optional[datetime] = Field(
        title="Created Datetime",
        description="The timestamp of when the resource was created.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
        },
    )
    updated_at: Optional[datetime] = Field(
        title="Updated Datetime",
        description="The timestamp of when the resource was last updated.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
        },
    )


class ResourceTableBase(ResourceBase):
    """
    Base class for all resource-based tables.
    """

    model_config = ConfigDict(
        validate_assignment=False,
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


class ResourceTable(AutomatedTimeFieldMixin, ResourceTableBase, table=True):
    """The table for storing information about active Resources, with various utility methods."""

    parent_link: "ResourceLinkTable" = Relationship(back_populates="parent")
    children_links: list["ResourceLinkTable"] = Relationship(back_populates="children")

    @property
    def parent(self) -> Optional["ResourceTable"]:
        """
        Get the parent resource.

        Returns:
            ResourceBase: The parent resource.
        """
        return self.parent_link.parent if self.parent_link else None

    @property
    def children(self) -> dict[str, "ResourceTable"]:
        """
        Get the children resources as a dictionary.

        Returns:
            dict: Dictionary of children resources.
        """
        return {link.key: link.child for link in self.children_links}

    def _archive(self, session: Session, event_type: str = "updated") -> None:
        """
        Archive or update the resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        HistoryTable._log_change(session, self, change_info=event_type)
        session.add(self)
        session.commit()

    def _remove(self, session: Session) -> None:
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        HistoryTable._log_change(session, self, change_info="deleted", removed=True)
        session.delete(self)
        session.commit()

    @classmethod
    def from_data_model(
        cls, resource: Union[ResourceDataModels, ResourceBaseTypes]
    ) -> Self:
        """
        Update the resource from a data model.

        Args:
            resource (Union[ResourceTypes, ResourceBaseTypes]): The resource data model.
        """
        cls.model_validate(**resource.model_dump())

    def to_data_model(self) -> ResourceDataModels:
        """
        Convert the resource to a data model.

        Returns:
            ResourceDataModels: The resource data model.
        """
        return RESOURCE_TYPE_MAP[self.base_type]["model"].model_validate(
            **self.model_dump()
        )


class ResourceLinkTableBase(BaseModel):
    """Association table for resources, connecting parents to children via a "key" property.

    This is a One-to-Many relationship, where a parent can have many children, but a child can only have one parent. Relationships are defined by a "key" property, which is unique for each parent (i.e. a parent can't have two children with the same key).

    Note the following properties:
      - The Parent and Child ID's are both primary keys. This ensures that a child can have exactly one relationship with a given parent.
      - The "key" property is unique for each parent, ensuring that a parent cannot have two children with the same key.
      - The "child_id" property is unique, ensuring that a child can only have one parent. This prevents a single resource from being in multiple places.
    """

    model_config = ConfigDict(
        validate_assignment=False,
    )

    key: str = Field(
        title="Resource Key",
        description="The key to identify the child resource's location in the parent container.",
        nullable=False,
    )


class ResourceLinkTable(AutomatedTimeFieldMixin, ResourceLinkTableBase, table=True):
    """The actual table for storing resource links."""

    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "key",
            name="uix_parent_key",
        ),  # * Prevent Two Children with Same Key in the same Parent
        UniqueConstraint(
            "child_id",
            name="uix_child",
        ),  # * Prevent Multiple Parents
    )

    parent_id: str = Field(
        title="Parent Resource ID",
        description="The ID of the parent resource.",
        nullable=False,
        primary_key=True,
        foreign_key="resource.resource_id",
    )
    child_id: str = Field(
        title="Child Resource ID",
        description="The ID of the child resource.",
        nullable=False,
        primary_key=True,
        foreign_key="resource.resource_id",
    )

    parent: "ResourceTable" = Relationship(back_populates="parent_link")
    child: "ResourceTable" = Relationship(back_populates="children_links")

    @staticmethod
    def link_resource(
        parent: Union[ResourceTable, str],
        child: Union[ResourceTable, str],
        key: str,
        session: Session,
        commit: bool = True,
    ) -> Self:
        """
        Link a child resource to a parent resource. If the child is already linked to a parent, it will be unlinked first.

        Args:
            parent (ResourceTable | str): The parent resource or its ID.
            child (ResourceTable | str): The child resource or its ID.
            key (str): The key to identify the child resource.
            session (Session): SQLAlchemy session for database operations.
        """
        link = session.exec(
            select(ResourceLinkTable).filter_by(
                child_id=child.resource_id
                if isinstance(child, ResourceTable)
                else child
            )
        ).first()
        if link:
            session.delete(link)
        link = ResourceLinkTable(
            parent_id=parent.resource_id
            if isinstance(parent, ResourceTable)
            else parent,
            child_id=child.resource_id if isinstance(child, ResourceTable) else child,
            key=str(key),
        )
        session.add(link)
        if commit:
            session.commit()
        return link

    @staticmethod
    def unlink_resource(
        child: Union[ResourceTable, str],
        session: Session,
        commit: bool = True,
    ) -> None:
        """
        Unlink a child resource from it's parent resource.

        Args:
            child (ResourceTable | str): The child resource or its ID.
            session (Session): SQLAlchemy session for database operations.
        """
        child_id = child.resource_id if isinstance(child, ResourceTable) else child
        link = session.exec(
            select(ResourceLinkTable).filter_by(child_id=child_id)
        ).first()
        if link:
            session.delete(link)
            if commit:
                session.commit()


class HistoryTable(ManualTimeFieldMixin, ResourceTableBase, table=True):
    """
    History table for tracking resource changes.
    """

    history_id: str = Field(
        title="History ID",
        description="The ID of the history entry.",
        primary_key=True,
        default_factory=new_ulid_str,
    )
    change_info: str = Field(
        title="Change Info",
        description="Relevant information about the change.",
        nullable=False,
    )
    removed: bool = Field(
        title="Removed",
        description="Whether the resource has been removed from the lab.",
        nullable=False,
        default=False,
    )
    history_created_at: Optional[datetime] = Field(
        title="History Created Datetime",
        description="The timestamp of when this resource history was created.",
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    parent_link: "ResourceLinkHistoryTable" = Relationship(back_populates="parent")
    children_links: list["ResourceLinkHistoryTable"] = Relationship(
        back_populates="child"
    )

    @property
    def parent(self) -> Optional["HistoryTable"]:
        """
        Get the parent resource.

        Returns:
            HistoryTable: The parent resource.
        """
        return self.parent_link.parent if self.parent_link else None

    @property
    def children(self) -> list["HistoryTable"]:
        """
        Get the children resources as a dictionary.

        Returns:
            dict: Dictionary of children resources.
        """
        return [link.child for link in self.children_links]

    @classmethod
    def _log_change(
        cls,
        session: Session,
        resource: ResourceTable,
        change_info: str,
        removed: bool = False,
    ) -> None:
        """
        Log a resource change in the history table.

        Args:
            session (Session): SQLAlchemy session.
            resource (SQLModel): The resource instance being logged.
            change_info (str): Info about the change that prompted this history entry (created, updated, deleted).
            removed (bool): Whether the resource is removed.
        """

        history_entry = cls(
            ManualTimeFieldMixin ** resource.model_dump(),
            change_info=change_info,
            removed=removed,
        )

        session.add(history_entry)
        session.commit()


class ResourceLinkHistoryTable(ManualTimeFieldMixin, ResourceLinkTableBase, table=True):
    """History of resource links, used in conjunction with HistoryTable."""

    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "key",
            "history_id",
            name="uix_parent_key_history",
        ),  # * Prevent Two Children with Same Key in the same Parent
        UniqueConstraint(
            "child_id",
            "history_id",
            name="uix_child_history",
        ),  # * Prevent Multiple Parents
    )

    history_id: str = Field(
        title="History ID",
        description="The ID of the related history entry.",
        primary_key=True,
        foreign_key="history.history_id",
    )
    parent_history_id: str = Field(
        title="Historical Parent Resource ID",
        description="The ID of the parent resource.",
        nullable=False,
        primary_key=True,
        foreign_key="history.history_id",
    )
    child_history_id: str = Field(
        title="Historical Child Resource ID",
        description="The ID of the child resource.",
        nullable=False,
        primary_key=True,
        foreign_key="history.history_id",
    )
    parent: "HistoryTable" = Relationship(back_populates="parent_link")
    child: "HistoryTable" = Relationship(back_populates="children_links")
