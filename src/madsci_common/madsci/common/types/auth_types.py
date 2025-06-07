"""Types related to authentication and ownership of MADSci objects."""

from typing import Any, Optional

from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.validators import optional_ulid_validator, ulid_validator
from pydantic import (
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
)
from pydantic.functional_validators import field_validator


class OwnershipInfo(MadsciBaseModel):
    """Information about the ownership of a MADSci object."""

    user_id: Optional[str] = Field(
        title="User ID",
        description="The ID of the user who owns the object.",
        default=None,
    )
    experiment_id: Optional[str] = Field(
        title="Experiment ID",
        description="The ID of the experiment that owns the object.",
        default=None,
    )
    campaign_id: Optional[str] = Field(
        title="Campaign ID",
        description="The ID of the campaign that owns the object.",
        default=None,
    )
    project_id: Optional[str] = Field(
        title="Project ID",
        description="The ID of the project that owns the object.",
        default=None,
    )
    node_id: Optional[str] = Field(
        title="Node ID",
        description="The ID of the node that owns the object.",
        default=None,
    )
    workcell_id: Optional[str] = Field(
        title="Workcell ID",
        description="The ID of the workcell that owns the object.",
        default=None,
    )
    lab_id: Optional[str] = Field(
        title="Lab ID",
        description="The ID of the lab that owns the object.",
        default=None,
    )
    step_id: Optional[str] = Field(
        title="Step ID",
        description="The ID of the step that owns the object.",
        default=None,
    )
    workflow_id: Optional[str] = Field(
        title="Workflow ID",
        description="The ID of the workflow that owns the object.",
        default=None,
    )
    manager_id: Optional[str] = Field(
        title="Manager ID",
        description="The ID of the manager that owns the object.",
        default=None,
    )

    is_ulid = field_validator(
        "user_id",
        "experiment_id",
        "campaign_id",
        "project_id",
        "node_id",
        "workcell_id",
        "step_id",
        "lab_id",
        "workflow_id",
        "manager_id",
        mode="after",
    )(optional_ulid_validator)

    @model_serializer(mode="wrap")
    def exclude_unset_by_default(
        self, nxt: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Exclude unset fields by default."""
        serialized = nxt(self, info)
        return {k: v for k, v in serialized.items() if v is not None}

    def check(self, other: "OwnershipInfo") -> bool:
        """Check if this ownership is the same as another."""
        for key in self.model_dump(exclude_none=True):
            if getattr(self, key) != getattr(other, key):
                return False
        return True


class UserInfo(MadsciBaseModel):
    """Information about a user."""

    user_id: str = Field(title="User ID", description="The ID of the user.")
    user_name: str = Field(title="User Name", description="The name of the user.")
    user_email: str = Field(title="User Email", description="The email of the user.")

    is_ulid = field_validator("user_id", mode="after")(ulid_validator)


class ProjectInfo(MadsciBaseModel):
    """Information about a project."""

    project_id: str = Field(title="Project ID", description="The ID of the project.")
    project_name: str = Field(
        title="Project Name",
        description="The name of the project.",
    )
    project_description: str = Field(
        title="Project Description",
        description="The description of the project.",
    )
    project_owner: UserInfo = Field(
        title="Project Owner",
        description="The owner of the project.",
    )
    project_members: list[UserInfo] = Field(
        title="Project Members",
        description="The members of the project.",
    )

    is_ulid = field_validator("project_id", mode="after")(ulid_validator)
