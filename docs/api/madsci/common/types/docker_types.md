Module madsci.common.types.docker_types
=======================================
Docker Helper Types (used for the automatic example.env and Configuration.md generation)

Classes
-------

`DockerComposeSettings(**kwargs: Any)`
:   These environment variables are used to configure the default Docker Compose in the MADSci example lab.
    
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