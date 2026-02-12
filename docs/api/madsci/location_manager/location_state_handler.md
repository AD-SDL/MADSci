Module madsci.location_manager.location_state_handler
=====================================================
State management for the LocationManager

Classes
-------

`LocationStateHandler(settings: madsci.common.types.location_types.LocationManagerSettings, manager_id: str, redis_connection: Any | None = None)`
:   Manages state for a MADSci Location Manager, providing transactional access to reading and writing location state
    with optimistic check-and-set and locking.

    Initialize a LocationStateHandler.

    ### Class variables

    `shutdown: bool`
    :

    `state_change_marker`
    :

    ### Methods

    `delete_location(self, location_id: str) ‑> bool`
    :   Deletes a location by ID. Returns True if the location was deleted, False if it didn't exist.

    `get_location(self, location_id: str) ‑> madsci.common.types.location_types.Location | None`
    :   Returns a location by ID

    `get_locations(self) ‑> list[madsci.common.types.location_types.Location]`
    :   Returns all locations as a list

    `has_state_changed(self) ‑> bool`
    :   Returns True if the state has changed since the last time this method was called

    `location_state_lock(self) ‑> pottery.redlock.Redlock`
    :   Gets a lock on the location state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us.

    `mark_state_changed(self) ‑> int`
    :   Marks the state as changed and returns the current state change counter

    `set_location(self, location_id: str, location: madsci.common.types.location_types.Location | dict[str, typing.Any]) ‑> madsci.common.types.location_types.Location`
    :   Sets a location by ID and returns the stored location

    `update_location(self, location_id: str, location: madsci.common.types.location_types.Location) ‑> madsci.common.types.location_types.Location`
    :   Updates a location and returns the updated location.
