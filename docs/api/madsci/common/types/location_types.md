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

`CreateLocationFromTemplateRequest(**data: Any)`
:   Request to create a location from a LocationTemplate.
    
    Requires node bindings to map abstract roles to concrete node instance names.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `allow_transfers: bool | None`
    :

    `description: str | None`
    :

    `location_name: str`
    :

    `model_config`
    :

    `node_bindings: dict[str, str]`
    :

    `representation_overrides: dict[str, dict[str, typing.Any]]`
    :

    `resource_template_overrides: dict[str, typing.Any] | None`
    :

    `template_name: str`
    :

    ### Methods

    `is_url_safe_name(v: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a URL-safe name.
        
        Allows alphanumeric characters, underscores, dots, and hyphens.
        Rejects empty strings.

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

    `location_template_name: str | None`
    :

    `model_config`
    :

    `node_bindings: dict[str, str] | None`
    :

    `representations: dict[str, typing.Any]`
    :

    `reservation: madsci.common.types.location_types.LocationReservation | None`
    :

    `resource_id: str | None`
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

    `is_url_safe_name(v: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a URL-safe name.
        
        Allows alphanumeric characters, underscores, dots, and hyphens.
        Rejects empty strings.

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

`LocationImportResult(**data: Any)`
:   Result of a bulk location import operation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `errors: list[str]`
    :

    `imported: int`
    :

    `locations: list[madsci.common.types.location_types.Location]`
    :

    `model_config`
    :

    `skipped: int`
    :

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

    `locations: list[madsci.common.types.location_types.Location]`
    :

    `manager_type: Literal[<ManagerType.LOCATION_MANAGER: 'location_manager'>]`
    :

    `model_config`
    :

    `transfer_capabilities: madsci.common.types.location_types.LocationTransferCapabilities | None`
    :

    ### Static methods

    `sort_locations(locations: list[madsci.common.types.location_types.Location]) ‑> list[madsci.common.types.location_types.Location]`
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

    `document_db_connected: bool | None`
    :

    `model_config`
    :

    `num_location_templates: int`
    :

    `num_locations: int`
    :

    `num_representation_templates: int`
    :

    `num_unresolved_locations: int`
    :

    `redis_connected: bool | None`
    :

`LocationManagerSettings(**kwargs: Any)`
:   Settings for the LocationManager.
    
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

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `database_name: str`
    :

    `document_db_url: pydantic.networks.AnyUrl`
    :

    `manager_type: madsci.common.types.manager_types.ManagerType | None`
    :

    `reconciliation_enabled: bool`
    :

    `reconciliation_interval_seconds: float`
    :

    `redis_host: str`
    :

    `redis_password: str | None`
    :

    `redis_port: int`
    :

    `seed_locations_file: str | None`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

    `transfer_capabilities: madsci.common.types.location_types.LocationTransferCapabilities | None`
    :

`LocationRepresentationTemplate(**data: Any)`
:   A named, versioned template for node-specific location representation data.
    
    Registered by nodes during startup or by operators via API. Defines the
    schema, defaults, and required overrides for a particular node type's
    representation of locations.
    
    Example: A robot arm registers ``"robotarm_deck_access"`` with defaults
    ``{"gripper_config": "standard", "max_payload": 2.0}`` and
    ``required_overrides=["position"]``.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created_at: datetime.datetime`
    :

    `created_by: str | None`
    :

    `default_values: dict[str, typing.Any]`
    :

    `description: str | None`
    :

    `model_config`
    :

    `required_overrides: list[str]`
    :

    `schema_def: dict[str, typing.Any] | None`
    :

    `tags: list[str]`
    :

    `template_id: str`
    :

    `template_name: str`
    :

    `updated_at: datetime.datetime | None`
    :

    `version: str`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

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

    `expires: datetime.datetime`
    :

    `model_config`
    :

    `owned_by: madsci.common.types.auth_types.OwnershipInfo`
    :

    ### Methods

    `check(self, ownership: madsci.common.types.auth_types.OwnershipInfo) ‑> bool`
    :   Check if the reservation is 1.) active or not, and 2.) owned by the given ownership.

`LocationTemplate(**data: Any)`
:   A named, versioned blueprint for creating locations.
    
    Maps abstract role names to representation template names. Resource-free
    and node-free — no specific node instances or resource IDs. At instantiation
    time, node bindings map roles to concrete node names.
    
    Example: ``"ot2_deck_slot"`` with
    ``representation_templates: {"deck_controller": "lh_deck_repr", "transfer_arm": "robotarm_deck_access"}``
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created_at: datetime.datetime`
    :

    `created_by: str | None`
    :

    `default_allow_transfers: bool`
    :

    `description: str | None`
    :

    `model_config`
    :

    `representation_templates: dict[str, str]`
    :

    `resource_template_name: str | None`
    :

    `resource_template_overrides: dict[str, typing.Any] | None`
    :

    `tags: list[str]`
    :

    `template_id: str`
    :

    `template_name: str`
    :

    `updated_at: datetime.datetime | None`
    :

    `version: str`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

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