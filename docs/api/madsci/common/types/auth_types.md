Module madsci.common.types.auth_types
=====================================
Types related to authentication and ownership of MADSci objects.

Classes
-------

`OwnershipInfo(**data: Any)`
:   Information about the ownership of a MADSci object.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `campaign_id: str | None`
    :

    `experiment_id: str | None`
    :

    `lab_id: str | None`
    :

    `manager_id: str | None`
    :

    `model_config`
    :

    `node_id: str | None`
    :

    `project_id: str | None`
    :

    `step_id: str | None`
    :

    `user_id: str | None`
    :

    `workcell_id: str | None`
    :

    `workflow_id: str | None`
    :

    ### Methods

    `check(self, other: OwnershipInfo) ‑> bool`
    :   Check if this ownership is the same as another.

    `exclude_unset_by_default(self, nxt: pydantic_core.core_schema.SerializerFunctionWrapHandler, info: pydantic_core.core_schema.SerializationInfo) ‑> dict[str, typing.Any]`
    :   Exclude unset fields by default.

    `is_ulid(id: str | None, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`ProjectInfo(**data: Any)`
:   Information about a project.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `project_description: str`
    :

    `project_id: str`
    :

    `project_members: list[madsci.common.types.auth_types.UserInfo]`
    :

    `project_name: str`
    :

    `project_owner: madsci.common.types.auth_types.UserInfo`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`UserInfo(**data: Any)`
:   Information about a user.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `user_email: str`
    :

    `user_id: str`
    :

    `user_name: str`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.
