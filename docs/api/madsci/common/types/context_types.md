Module madsci.common.types.context_types
========================================
Types for managing MADSci contexts and their configurations.

Classes
-------

`MadsciContext(**kwargs: Any)`
:   Base class for MADSci context settings.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

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
