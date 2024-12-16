"""Types for configuring components of MADSci"""

from typing import Any, Optional

from pydantic import Field

from madsci.common.types.base_types import BaseModel


class ConfigParameterDefinition(BaseModel, extra="allow"):
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
        description="Whether the configured object should restart/reset whenever the parameter changes.",
        default=True,
    )


class ConfigParameterWithValue(ConfigParameterDefinition):
    """A configuration parameter definition with value set"""

    value: Optional[Any] = Field(
        title="Parameter Value",
        description="The value of the parameter, if set",
        default=None,
    )
