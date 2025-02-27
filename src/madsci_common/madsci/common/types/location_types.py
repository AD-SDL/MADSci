"""Location types for MADSci."""

from typing import Optional

from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import Field
from pydantic.functional_validators import field_validator
from pydantic.types import Json


class Location(BaseModel):
    """A location in the lab."""

    location_name: str = Field(
        title="Location Name",
        description="The name of the location.",
    )
    location_id: str = Field(
        title="Location ID",
        description="The ID of the location.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        title="Description",
        description="A description of the location.",
        default=None,
    )
    poses: list["Pose"] = Field(
        title="Poses",
        description="A dictionary of poses representing the location. Keys are node names.",
        default=[],
    )
    resource_id: Optional[str] = Field(
        title="Resource ID",
        description="The resource ID linked to the location, typically a container ID.",
        default=None,
    )

    is_ulid = field_validator("lab_id")(ulid_validator)


class Pose(BaseModel):
    """A pose for a location in in the lab."""

    node_id: str = Field(title="Node ID", description="The ID of the node in the lab.")
    pose_id: str = Field(
        title="Pose ID",
        description="The ID of the pose.",
        default_factory=new_ulid_str,
    )
    pose_name: str = Field(title="Pose Name", description="The name of the pose.")
    pose_description: Optional[str] = Field(
        title="Pose Description",
        description="A description of the pose.",
        default=None,
    )
    pose_value: Json = Field(
        title="Pose Value",
        description="The value of the pose. Any JSON serializable object, representing the pose.",
    )

    is_ulid = field_validator("pose_id")(ulid_validator)
