Module madsci.common.types.condition_types
==========================================
Types for MADSci Conditions.

Classes
-------

`Condition(**data: Any)`
:   A model for the conditions a step needs to be run

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.condition_types.NoResourceInLocationCondition
    * madsci.common.types.condition_types.ResourceChildFieldCheckCondition
    * madsci.common.types.condition_types.ResourceFieldCheckCondition
    * madsci.common.types.condition_types.ResourceInLocationCondition

    ### Class variables

    `condition_name: str`
    :

    `condition_type: madsci.common.types.condition_types.ConditionTypeEnum | None`
    :

    `model_config`
    :

`ConditionTypeEnum(*args, **kwds)`
:   Types of conditional check for a step

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `NO_RESOURCE_PRESENT`
    :

    `RESOURCE_CHILD_FIELD_CHECK`
    :

    `RESOURCE_FIELD_CHECK`
    :

    `RESOURCE_PRESENT`
    :

`NoResourceInLocationCondition(**data: Any)`
:   A condition that checks if a resource is present

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.condition_types.Condition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `condition_type: Literal[<ConditionTypeEnum.NO_RESOURCE_PRESENT: 'no_resource_present'>]`
    :

    `key: str | int | tuple[int | str, int | str] | tuple[int | str, int | str, int | str]`
    :

    `location_id: str | None`
    :

    `location_name: str`
    :

    `model_config`
    :

`OperatorTypeEnum(*args, **kwds)`
:   Comparison operators for value checks

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `IS_EQUAL_TO`
    :

    `IS_GREATER_THAN`
    :

    `IS_GREQUAL_TO`
    :

    `IS_LEQUAL_TO`
    :

    `IS_LESS_THAN`
    :

`ResourceChildFieldCheckCondition(**data: Any)`
:   A condition that checks if a resource is present

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.condition_types.Condition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `condition_type: Literal[<ConditionTypeEnum.RESOURCE_CHILD_FIELD_CHECK: 'resource_child_field_check'>]`
    :

    `field: str`
    :

    `key: str | int | tuple[int | str, int | str] | tuple[int | str, int | str, int | str]`
    :

    `model_config`
    :

    `operator: madsci.common.types.condition_types.OperatorTypeEnum`
    :

    `resource_id: str | None`
    :

    `resource_name: str | None`
    :

    `target_value: Any`
    :

`ResourceFieldCheckCondition(**data: Any)`
:   A condition that checks if a resource is present

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.condition_types.Condition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `condition_type: Literal[<ConditionTypeEnum.RESOURCE_FIELD_CHECK: 'resource_field_check'>]`
    :

    `field: str`
    :

    `model_config`
    :

    `operator: madsci.common.types.condition_types.OperatorTypeEnum`
    :

    `resource_id: str | None`
    :

    `resource_name: str | None`
    :

    `target_value: Any`
    :

`ResourceInLocationCondition(**data: Any)`
:   A condition that checks if a resource is present

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.condition_types.Condition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `condition_type: Literal[<ConditionTypeEnum.RESOURCE_PRESENT: 'resource_present'>]`
    :

    `key: str | int | tuple[int | str, int | str] | tuple[int | str, int | str, int | str]`
    :

    `location_id: str | None`
    :

    `location_name: str | None`
    :

    `model_config`
    :

    `resource_class: str | None`
    :
