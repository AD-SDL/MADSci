"""Types for managing MADSci contexts and their configurations."""

from typing import Any, Optional

from madsci.common.types.base_types import (
    DefinitionSettings,
    MadsciBaseSettings,
)
from pydantic import AnyUrl, Field


class MadsciContext(
    MadsciBaseSettings,
    env_file=(".env", "context.env"),
    toml_file="context.toml",
    yaml_file="context.yaml",
    json_file="context.json",
):
    """Base class for MADSci context settings."""

    lab_server_url: Optional[AnyUrl] = Field(
        title="Lab Server URL",
        description="The URL of the lab server.",
        default=AnyUrl("http://localhost:8000"),
    )
    event_server_url: Optional[AnyUrl] = Field(
        title="Event Server URL",
        description="The URL of the event server.",
        default=None,
    )
    experiment_server_url: Optional[AnyUrl] = Field(
        title="Experiment Server URL",
        description="The URL of the experiment server.",
        default=None,
    )
    data_server_url: Optional[AnyUrl] = Field(
        title="Data Server URL",
        description="The URL of the data server.",
        default=None,
    )
    resource_server_url: Optional[AnyUrl] = Field(
        title="Resource Server URL",
        description="The URL of the resource server.",
        default=None,
    )
    workcell_server_url: Optional[AnyUrl] = Field(
        title="Workcell Server URL",
        description="The URL of the workcell server.",
        default=None,
    )

    @classmethod
    def load_model(cls, *args: Any, **kwargs: Any) -> "MadsciContext":
        """Load the lab settings model."""
        definition_settings = DefinitionSettings()
        if definition_settings.context_definition:
            kwargs["definition_files"] = definition_settings.context_definition
        return super().load_model(*args, **kwargs)
