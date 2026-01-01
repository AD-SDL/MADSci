Module madsci.common.types.docker_types
=======================================
Docker Helper Types (used for the automatic example.env and Configuration.md generation)

Classes
-------

`DockerComposeSettings(**values: Any)`
:   These environment variables are used to configure the default Docker Compose in the MADSci example lab.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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
