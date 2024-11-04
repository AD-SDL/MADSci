"""MADSci Resource Manager Types."""

from sqlmodel.main import Field

from madsci.common.types import BaseModel
from madsci.common.types.squid_types import SquidPluginDefinition


class ResourceManagerDefinition(SquidPluginDefinition):
    """Definition for a MADSci Resource Manager."""

    plugin_type: str = Field(
        default="resource_manager",
        title="Plugin Type",
        description="The type of the plugin, used by other components or plugins to find matching plugins.",
    )
    plugin_config: "ResourceManagerConfig" = Field(
        default_factory=lambda: ResourceManagerConfig(),
        title="Plugin Configuration",
        description="The configuration for the resource manager plugin.",
    )


class ResourceManagerConfig(BaseModel):
    """Configuration for a MADSci Resource Manager."""

    host: str = Field(
        default="localhost",
        title="Host",
        description="The host to run the resource manager on.",
    )
    port: int = Field(
        default=8012,
        title="Port",
        description="The port to run the resource manager on.",
    )
