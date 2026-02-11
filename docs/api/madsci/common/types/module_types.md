Module madsci.common.types.module_types
=======================================
Types for MADSci Node Modules and their configuration.

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

Classes
-------

`ModuleSettings(**values: Any)`
:   Base settings for MADSci node modules.

    Contains module-level metadata that applies to the entire module,
    not just a single node instance. This includes version information,
    repository URLs, and interface variant selection.

    Module developers should inherit from this class and customize
    the module_name and other fields as needed.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.module_types.NodeModuleSettings

    ### Class variables

    `documentation_url: str | None`
    :

    `interface_variant: Literal['real', 'fake', 'sim']`
    :

    `module_name: str`
    :

    `module_version: str`
    :

    `repository_url: str | None`
    :

`NodeModuleSettings(**values: Any)`
:   Settings for a node instance within a module.

    Combines module-level settings with node-specific runtime configuration.
    This class bridges the gap between ModuleSettings and NodeConfig,
    providing a unified configuration surface for node modules.

    Node developers typically don't use this directly; instead, they
    create a custom settings class that inherits from RestNodeConfig
    or NodeConfig and adds module-specific fields.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.module_types.ModuleSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `lab_url: str | None`
    :

    `name: str`
    :

    `simulate: bool`
    :

    `workcell_url: str | None`
    :
