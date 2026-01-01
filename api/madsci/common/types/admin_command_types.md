Module madsci.common.types.admin_command_types
==============================================
Types for Admin Commands.

Classes
-------

`AdminCommandResponse(**data: Any)`
:   Response from an Admin Command

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `data: Any | None`
    :

    `errors: list[madsci.common.types.base_types.Error]`
    :

    `model_config`
    :

    `success: bool`
    :

`AdminCommands(*args, **kwds)`
:   Valid Admin Commands to send to a Node

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `CANCEL`
    :

    `GET_LOCATION`
    :

    `LOCK`
    :

    `PAUSE`
    :

    `RESET`
    :

    `RESUME`
    :

    `SAFETY_STOP`
    :

    `SHUTDOWN`
    :

    `UNLOCK`
    :
