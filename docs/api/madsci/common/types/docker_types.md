Module madsci.common.types.docker_types
=======================================
Docker Helper Types (used for the automatic example.env and Configuration.md generation)

Classes
-------

`DockerComposeSettings(**kwargs: Any)`
:   These environment variables are used to configure the default Docker Compose in the MADSci example lab.

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

    `GROUP_ID: int`
    :

    `MINIO_CONSOLE_PORT: int`
    :

    `MINIO_PORT: int`
    :

    `MONGODB_PORT: int`
    :

    `POSTGRES_PORT: int`
    :

    `REDIS_PORT: int`
    :

    `REPO_PATH: str`
    :

    `USER_ID: int`
    :
