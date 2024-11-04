"""Types related to MADSci Modules."""

from typing import Optional

from aenum._enum import Enum
from pydantic.functional_validators import field_validator, model_validator
from pydantic.networks import AnyUrl
from sqlmodel.main import Field

from madsci.common.types import BaseModel, new_ulid_str
from madsci.common.types.validators import ulid_validator


class ModuleDefinition(BaseModel):
    """Definition for a MADSci Module."""

    name: str = Field(
        title="Module Name",
        description="The name of the module.",
    )
    description: Optional[str] = Field(
        default=None,
        title="Module Description",
        description="A description of the module.",
    )
    url: AnyUrl = Field(
        title="Module URL",
        description="The URL to the module.",
    )


class Module(ModuleDefinition):
    """A runtime representation of a MADSci Module used in a Workcell."""

    module_id: Optional[str] = Field(
        title="Module ID",
        description="The ID of the module. This is defined by the module itself, and will be used to uniquely identify the module in the workcell.",
        default=None,
    )
    info: Optional["ModuleInfo"] = Field(
        default=None,
        title="Module Info",
        description="Information about the module, provided by the module itself.",
    )

    is_ulid = field_validator("module_id")(ulid_validator)

    @model_validator(mode="after")
    def validate_module_id(self) -> "Module":
        """Validate that the module ID matches the ID in the module info."""
        if self.module_id and self.info and self.info.module_id:
            if self.module_id != self.info.module_id:
                raise ValueError(
                    "Module ID does not match the ID returned in the module info."
                )
        return self


class ModuleInfo(BaseModel):
    """Information about a MADSci Module."""

    module_id: str = Field(
        title="Module ID",
        description="The ID of the module.",
        default_factory=new_ulid_str,
    )
    capabilities: "ModuleCapabilities" = Field(
        default_factory=lambda: ModuleCapabilities(),
        title="Module Capabilities",
        description="The capabilities of the module.",
    )

    is_ulid = field_validator("module_id")(ulid_validator)


class ModuleCapabilities(BaseModel):
    """Capabilities of a MADSci Module. All capabilities are optional (though a module with no capabilities set will not be able to do anything). The server will not use any capabilities that are not set to True. If a module does not support a capability, it should not set it to True. If a module does not support the /info endpoint, the server will test the other capabilities by sending the appropriate requests and seeing if they fail or not."""

    info: bool = Field(
        default=False,
        title="Module Info",
        description="Whether the module supports the /info endpoint.",
    )
    state: bool = Field(
        default=False,
        title="Module State",
        description="Whether the module supports the /state endpoint.",
    )
    action: bool = Field(
        default=False,
        title="Module Action",
        description="Whether the module supports the /action endpoint.",
    )
    admin_commands: Optional[set["AdminCommands"]] = Field(
        default=None,
        title="Module Admin Commands",
        description="Whether the module supports the /admin endpoint, and if so, the commands it supports.",
    )
    resources: bool = Field(
        default=False,
        title="Module Resources",
        description="Whether the module supports the /resources endpoint.",
    )
    websockets: bool = Field(
        default=False,
        title="Module Websockets Interface",
        description="Whether the module supports the /ws endpoint.",
    )


class AdminCommands(str, Enum):
    """Valid Admin Commands to send to a Module"""

    SAFETY_STOP = "safety_stop"
    RESET = "reset"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"
    SHUTDOWN = "shutdown"
    LOCK = "lock"
    UNLOCK = "unlock"
