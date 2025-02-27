"""Types for configuring components of MADSci"""

from typing import Any, Optional, Union

from madsci.common.types.base_types import BaseModel
from pydantic import Field


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


class ConfigParameterWithValue(ConfigParameterDefinition):
    """A configuration parameter definition with value set"""

    value: Optional[Any] = Field(
        title="Parameter Value",
        description="The value of the parameter, if set",
        default=None,
    )


class ConfigNamespaceDefinition(BaseModel, extra="allow"):
    """A namespace for configuration parameters."""

    namespace: str = Field(
        title="Namespace Name",
        description="The name of the namespace.",
    )
    description: Optional[str] = Field(
        title="Namespace Description",
        description="A description of the namespace.",
        default=None,
    )
    parameters: dict[
        str, Union[ConfigParameterDefinition, "ConfigNamespaceDefinition"]
    ] = Field(
        title="Namespace Parameters",
        description="The config parameters in the namespace.",
        default_factory=dict,
    )
