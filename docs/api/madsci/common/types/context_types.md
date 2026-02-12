Module madsci.common.types.context_types
========================================
Types for managing MADSci contexts and their configurations.

Classes
-------

`MadsciContext(**values: Any)`
:   Base class for MADSci context settings.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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
