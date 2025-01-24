"""MADSci Resource Manager Types."""

from madsci.common.types.lab_types import ManagerDefinition
from madsci.common.types.workcell_types import WorkcellConfig
from sqlmodel.main import Field


class WorkcellManagerDefinition(ManagerDefinition):
    """Definition for a MADSci Resource Manager."""

    plugin_type: str = Field(
        default="workcell_manager",
        title="Plugin Type",
        description="The type of the plugin, used by other components or plugins to find matching plugins.",
    )
    plugin_config: "WorkcellConfig" = Field(
        default_factory=lambda: WorkcellConfig(),
        title="Plugin Configuration",
        description="The configuration for the workcell manager plugin.",
    )
