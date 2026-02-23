Module madsci.common.types.registry_types
=========================================
ID Registry types for MADSci.

This module defines the types used by the ID Registry system for reliable,
persistent mapping between human-readable component names and their unique
identifiers (ULIDs).

Variables
---------

`ComponentType`
:   Valid component types for registry entries.

Classes
-------

`LocalRegistry(**data: Any)`
:   The local registry file structure.

    This represents the contents of ~/.madsci/registry.json,
    the local cache of component identities.

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

    `entries: dict[str, madsci.common.types.registry_types.RegistryEntry]`
    :

    `model_config`
    :

    `updated_at: datetime.datetime`
    :

    `version: int`
    :

`RegistryEntry(**data: Any)`
:   A single entry in the registry.

    Each entry maps a human-readable component name to a unique ULID,
    with optional lock information for conflict prevention.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `component_type: Literal['node', 'module', 'manager', 'experiment', 'workcell']`
    :

    `created_at: datetime.datetime`
    :

    `id: str`
    :

    `last_seen: datetime.datetime`
    :

    `lock: madsci.common.types.registry_types.RegistryLock | None`
    :

    `metadata: dict`
    :

    `model_config`
    :

    `workcell_id: str | None`
    :

    ### Methods

    `is_locked(self) ‑> bool`
    :   Check if entry is currently locked (lock exists and not expired).

    `is_locked_by(self, instance_id: str) ‑> bool`
    :   Check if entry is locked by a specific instance.

        Args:
            instance_id: The instance ID to check

        Returns:
            True if the entry is locked by this instance

`RegistryLock(**data: Any)`
:   Lock information for a registry entry.

    Locks prevent multiple processes from claiming the same component name.
    They use a heartbeat mechanism to detect stale locks from crashed processes.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `acquired_at: datetime.datetime`
    :

    `expires_at: datetime.datetime`
    :

    `heartbeat_at: datetime.datetime`
    :

    `holder_host: str`
    :

    `holder_instance: str`
    :

    `holder_pid: int`
    :

    `model_config`
    :

`RegistryResolveResult(**data: Any)`
:   Result from resolving a name in the registry.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `component_type: Literal['node', 'module', 'manager', 'experiment', 'workcell']`
    :

    `id: str`
    :

    `is_new: bool`
    :

    `model_config`
    :

    `name: str`
    :

    `source: str`
    :
