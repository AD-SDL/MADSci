Module madsci.common.types.location_types
=========================================
Location types for MADSci.

Classes
-------

`CapacityCostConfig(**data: Any)`
:   Configuration for capacity-aware cost adjustments.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `enabled: bool`
    :

    `full_capacity_multiplier: float`
    :

    `full_capacity_threshold: float`
    :

    `high_capacity_multiplier: float`
    :

    `high_capacity_threshold: float`
    :

    `model_config`
    :

`Location(**data: Any)`
:   A location in the lab.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `allow_transfers: bool`
    :

    `description: str | None`
    :

    `location_id: str`
    :

    `location_name: str`
    :

    `model_config`
    :

    `representations: dict[str, typing.Any] | None`
    :

    `reservation: madsci.common.types.location_types.LocationReservation | None`
    :

    `resource_id: str | None`
    :

    ### Instance variables

    `name: str`
    :   Get the name of the location.

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`LocationArgument(**data: Any)`
:   Location Argument to be used by MADSCI nodes.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `location_name: str | None`
    :   the name of the given location

    `model_config`
    :

    `representation: Any`
    :   Representation of the location specific to the node.

    `reservation: madsci.common.types.location_types.LocationReservation | None`
    :   whether existing location is reserved

    `resource_id: str | None`
    :   The ID of the corresponding resource, if any

    ### Instance variables

    `location: Any`
    :   Return the representation of the location.

    `location_setter: Any`
    :   Return the representation of the location.

    `name: str | None`
    :   Return the name of the location, if available.

`LocationDefinition(**data: Any)`
:   The Definition of a Location in a setup.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `allow_transfers: bool`
    :

    `description: str | None`
    :

    `location_id: str`
    :

    `location_name: str`
    :

    `model_config`
    :

    `representations: dict[str, typing.Any]`
    :

    `resource_template_name: str | None`
    :

    `resource_template_overrides: dict[str, typing.Any] | None`
    :

    ### Instance variables

    `name: str`
    :   Get the name of the location.

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`LocationManagerDefinition(**data: Any)`
:   Definition for a LocationManager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `locations: list[madsci.common.types.location_types.LocationDefinition]`
    :

    `manager_type: Literal[<ManagerType.LOCATION_MANAGER: 'location_manager'>]`
    :

    `model_config`
    :

    `transfer_capabilities: madsci.common.types.location_types.LocationTransferCapabilities | None`
    :

    ### Static methods

    `sort_locations(locations: list[madsci.common.types.location_types.LocationDefinition]) ‑> list[madsci.common.types.location_types.LocationDefinition]`
    :   Sort locations by name after validation.

`LocationManagerHealth(**data: Any)`
:   Health status for the Location Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `num_locations: int`
    :

    `redis_connected: bool | None`
    :

`LocationManagerSettings(**values: Any)`
:   Settings for the LocationManager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `manager_definition: str | pathlib.Path`
    :

    `redis_host: str`
    :

    `redis_password: str | None`
    :

    `redis_port: int`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

`LocationReservation(**data: Any)`
:   Reservation of a MADSci Location.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created: datetime.datetime`
    :

    `end: datetime.datetime`
    :

    `model_config`
    :

    `owned_by: madsci.common.types.auth_types.OwnershipInfo`
    :

    `start: datetime.datetime`
    :

    ### Methods

    `check(self, ownership: madsci.common.types.auth_types.OwnershipInfo) ‑> bool`
    :   Check if the reservation is 1.) active or not, and 2.) owned by the given ownership.

`LocationTransferCapabilities(**data: Any)`
:   Transfer capabilities for a location manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `capacity_cost_config: madsci.common.types.location_types.CapacityCostConfig | None`
    :

    `model_config`
    :

    `override_transfer_templates: madsci.common.types.location_types.TransferTemplateOverrides | None`
    :

    `transfer_templates: list[madsci.common.types.location_types.TransferStepTemplate]`
    :

`TransferGraphEdge(**data: Any)`
:   Represents a transfer path between two locations.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `cost: float`
    :

    `model_config`
    :

    `source_location_id: str`
    :

    `target_location_id: str`
    :

    `transfer_template: madsci.common.types.location_types.TransferStepTemplate`
    :

`TransferStepTemplate(**data: Any)`
:   Template for transfer steps between compatible locations.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `action: str`
    :

    `additional_args: dict[str, typing.Any]`
    :

    `additional_location_args: dict[str, str]`
    :

    `cost_weight: float | None`
    :

    `model_config`
    :

    `node_name: str`
    :

    `source_argument_name: str`
    :

    `target_argument_name: str`
    :

`TransferTemplateOverrides(**data: Any)`
:   Override transfer templates for specific source/destination patterns.

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

    `pair_overrides: dict[str, dict[str, list[madsci.common.types.location_types.TransferStepTemplate]]] | None`
    :

    `source_overrides: dict[str, list[madsci.common.types.location_types.TransferStepTemplate]] | None`
    :

    `target_overrides: dict[str, list[madsci.common.types.location_types.TransferStepTemplate]] | None`
    :
