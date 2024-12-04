"""Types for configuring components of MADSci"""

from typing import Any, Optional

from sqlmodel.main import Field

from madsci.common.types.base_types import BaseModel


class ConfigParameter(BaseModel, extra="allow"):
    """A configuration parameter definition for a MADSci system component."""

    name: str = Field(
        title="Parameter Name",
        description="The name of the parameter.",
    )
    description: Optional[str] = Field(
        title="Parameter Description",
        description="A description of the parameter.",
        default=None,
    )
    default: Optional[Any] = Field(
        title="Parameter Default",
        description="The default value of the parameter.",
        default=None,
    )
    required: bool = Field(
        title="Parameter Required",
        description="Whether the parameter is required.",
        default=False,
    )
    reset_on_change: bool = Field(
        title="Parameter Reset on Change",
        description="Whether the node should restart whenever the parameter changes.",
        default=True,
    )
