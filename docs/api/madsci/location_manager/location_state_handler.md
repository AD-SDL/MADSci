Module madsci.location_manager.location_state_handler
=====================================================
State management for the LocationManager.

Uses document database (FerretDB) for persistent location CRUD,
and cache (Valkey) for transient state (locks, change counters).

Classes
-------

`LocationStateHandler(settings: madsci.common.types.location_types.LocationManagerSettings, manager_id: str, redis_connection: Any | None = None, cache_handler: madsci.common.db_handlers.cache_handler.CacheHandler | None = None, document_handler: madsci.common.db_handlers.document_storage_handler.DocumentStorageHandler | None = None)`
:   Manages state for a MADSci Location Manager.
    
    - Document storage handler: persistent location CRUD
    - Cache handler: transient state (locks, change counters)
    
    Initialize a LocationStateHandler.
    
    Parameters
    ----------
    settings:
        Location manager settings.
    manager_id:
        Unique identifier for this manager instance.
    redis_connection:
        Deprecated. Use cache_handler instead.
    cache_handler:
        Cache handler for transient state (locks, change counters).
    document_handler:
        Document storage handler for persistent location storage.

    ### Methods

    `add_location(self, location: madsci.common.types.location_types.Location | dict[str, typing.Any]) ‑> madsci.common.types.location_types.Location | None`
    :   Adds a location by name and returns the stored location.
        Returns None if the name already exists.

    `add_location_template(self, template: madsci.common.types.location_types.LocationTemplate | dict[str, typing.Any]) ‑> madsci.common.types.location_types.LocationTemplate | None`
    :   Adds a location template. Returns None if the name already exists.

    `add_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate | dict[str, typing.Any]) ‑> madsci.common.types.location_types.LocationRepresentationTemplate | None`
    :   Adds a representation template. Returns None if the name already exists.

    `close(self) ‑> None`
    :   Release both cache and document storage connections and resources.

    `count_location_templates(self) ‑> int`
    :   Returns the total number of location templates.

    `count_locations(self) ‑> int`
    :   Returns the total number of locations.

    `count_representation_templates(self) ‑> int`
    :   Returns the total number of representation templates.

    `count_unresolved_locations(self) ‑> int`
    :   Returns the number of locations with unresolved resource template references.

    `delete_location(self, location_name: str) ‑> bool`
    :   Deletes a location by name.
        Returns True if the location was deleted, False if it didn't exist.

    `delete_location_template(self, template_name: str) ‑> bool`
    :   Deletes a location template by name. Returns True if deleted, False if not found.

    `delete_representation_template(self, template_name: str) ‑> bool`
    :   Deletes a representation template by name. Returns True if deleted, False if not found.

    `get_location(self, location_name: str) ‑> madsci.common.types.location_types.Location | None`
    :   Returns a location by name.

    `get_location_by_id(self, location_id: str) ‑> madsci.common.types.location_types.Location | None`
    :   Returns a location by ID (O(1) with MongoDB index).

    `get_location_template(self, template_name: str) ‑> madsci.common.types.location_types.LocationTemplate | None`
    :   Returns a location template by name.

    `get_location_templates(self) ‑> list[madsci.common.types.location_types.LocationTemplate]`
    :   Returns all location templates.

    `get_locations(self) ‑> list[madsci.common.types.location_types.Location]`
    :   Returns all locations as a list.

    `get_representation_template(self, template_name: str) ‑> madsci.common.types.location_types.LocationRepresentationTemplate | None`
    :   Returns a representation template by name.

    `get_representation_templates(self) ‑> list[madsci.common.types.location_types.LocationRepresentationTemplate]`
    :   Returns all representation templates.

    `has_state_changed(self) ‑> bool`
    :   Returns True if the state has changed since the last time this method was called.

    `location_state_lock(self) ‑> Any`
    :   Gets a lock on the location state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us.

    `mark_state_changed(self) ‑> int`
    :   Marks the state as changed and returns the current state change counter.

    `update_location(self, location: madsci.common.types.location_types.Location | dict) ‑> madsci.common.types.location_types.Location`
    :   Updates a location and returns the updated location.
        Raises KeyError if the location doesn't exist, ValueError if ID mismatches.

    `update_location_template(self, template: madsci.common.types.location_types.LocationTemplate | dict[str, typing.Any]) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Updates a location template. Raises KeyError if not found, ValueError if ID mismatch.

    `update_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate | dict[str, typing.Any]) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Updates a representation template. Raises KeyError if not found, ValueError if ID mismatch.