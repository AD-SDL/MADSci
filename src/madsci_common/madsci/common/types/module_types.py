"""Types for MADSci Node Modules and their configuration.

This module provides the base settings classes for developing MADSci node modules.
A Module is a complete package (typically a git repository) containing the node,
interfaces, drivers, types, tests, and deployment configurations.

The settings hierarchy is:
    ModuleSettings (module-level metadata)
        └── NodeSettings (node runtime config, extends NodeConfig)

Usage:
    For module development, create a `foo_types.py` file that contains all
    type definitions for your module:

    ```python
    # src/foo_types.py
    from madsci.common.types.module_types import ModuleSettings
    from madsci.common.types.node_types import RestNodeConfig

    class FooModuleSettings(ModuleSettings):
        module_name: str = "foo"

    class FooNodeSettings(RestNodeConfig):
        # Foo-specific settings
        max_speed: float = Field(default=100.0, description="Maximum speed in mm/s")
    ```
"""

from typing import Literal, Optional

from madsci.common.types.base_types import MadsciBaseSettings
from pydantic import Field


class ModuleSettings(
    MadsciBaseSettings,
    env_file=(".env", "module.env"),
    toml_file=("settings.toml", "module.settings.toml"),
    yaml_file=("settings.yaml", "module.settings.yaml"),
    json_file=("settings.json", "module.settings.json"),
    env_prefix="MODULE_",
):
    """Base settings for MADSci node modules.

    Contains module-level metadata that applies to the entire module,
    not just a single node instance. This includes version information,
    repository URLs, and interface variant selection.

    Module developers should inherit from this class and customize
    the module_name and other fields as needed.
    """

    module_name: str = Field(
        title="Module Name",
        description="Name of the module (e.g., 'liquidhandler', 'pf400'). "
        "This should match the package name.",
    )
    module_version: str = Field(
        default="0.0.1",
        title="Module Version",
        description="Semantic version of the module.",
    )
    repository_url: Optional[str] = Field(
        default=None,
        title="Repository URL",
        description="URL of the module's git repository.",
    )
    documentation_url: Optional[str] = Field(
        default=None,
        title="Documentation URL",
        description="URL to the module's documentation.",
    )
    interface_variant: Literal["real", "fake", "sim"] = Field(
        default="real",
        title="Interface Variant",
        description="Which interface variant to use: "
        "'real' for actual hardware, 'fake' for in-memory testing, "
        "'sim' for physics simulation.",
    )


class NodeModuleSettings(
    ModuleSettings,
    env_file=(".env", "node.env", "module.env"),
    toml_file=("settings.toml", "node.settings.toml", "module.settings.toml"),
    yaml_file=("settings.yaml", "node.settings.yaml", "module.settings.yaml"),
    json_file=("settings.json", "node.settings.json", "module.settings.json"),
    env_prefix="NODE_",
):
    """Settings for a node instance within a module.

    Combines module-level settings with node-specific runtime configuration.
    This class bridges the gap between ModuleSettings and NodeConfig,
    providing a unified configuration surface for node modules.

    Node developers typically don't use this directly; instead, they
    create a custom settings class that inherits from RestNodeConfig
    or NodeConfig and adds module-specific fields.
    """

    # Node identity (for ID registry lookup)
    name: str = Field(
        title="Node Name",
        description="Name of this node instance. Used for ID registry lookup "
        "and display purposes.",
    )
    description: Optional[str] = Field(
        default=None,
        title="Node Description",
        description="Human-readable description of this node instance.",
    )

    # Lab connection settings
    lab_url: Optional[str] = Field(
        default=None,
        title="Lab Manager URL",
        description="URL of the lab manager for registry sync and event logging.",
    )
    workcell_url: Optional[str] = Field(
        default=None,
        title="Workcell Manager URL",
        description="URL of the workcell manager this node belongs to.",
    )

    # Behavior settings
    simulate: bool = Field(
        default=False,
        title="Simulation Mode",
        description="Run in simulation mode. When True, the node will use "
        "a simulated interface instead of real hardware.",
    )
