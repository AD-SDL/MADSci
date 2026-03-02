Module madsci.common.types.context_types
========================================
Types for managing MADSci contexts and their configurations.

Classes
-------

`MadsciContext(**kwargs: Any)`
:   Base class for MADSci context settings.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `data_server_url: pydantic.networks.AnyUrl | None`
    :

    `event_server_url: pydantic.networks.AnyUrl | None`
    :

    `experiment_server_url: pydantic.networks.AnyUrl | None`
    :

    `lab_server_url: pydantic.networks.AnyUrl | None`
    :

    `location_server_url: pydantic.networks.AnyUrl | None`
    :

    `resource_server_url: pydantic.networks.AnyUrl | None`
    :

    `workcell_server_url: pydantic.networks.AnyUrl | None`
    :