"""Types related to authentication and ownership of MADSci objects."""

from typing import Optional

from pydantic.functional_validators import field_validator
from sqlmodel.main import Field

from madsci.common.types.base_types import BaseModel
from madsci.common.types.validators import ulid_validator


class OwnershipInfo(BaseModel):
    """Information about the ownership of a MADSci object."""

    auth_id: str = Field(
        title="Auth ID",
        description="The ID of the auth that owns the object.",
    )

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

    is_ulid = field_validator(
        "user_id",
        "experiment_id",
        "campaign_id",
        "project_id",
        "node_id",
        "workcell_id",
        mode="after",
    )(ulid_validator)


class UserInfo(BaseModel):
    """Information about a user."""

    user_id: str = Field(title="User ID", description="The ID of the user.")
    user_name: str = Field(title="User Name", description="The name of the user.")
    user_email: str = Field(title="User Email", description="The email of the user.")

    is_ulid = field_validator("user_id", mode="after")(ulid_validator)


class ProjectInfo(BaseModel):
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
