"""
State management for the LocationManager
"""

import warnings
from typing import Any, Optional, Union

import redis
from madsci.common.types.location_types import Location, LocationManagerSettings
from pottery import InefficientAccessWarning, RedisDict, Redlock
from pydantic import ValidationError


class LocationStateHandler:
    """
    Manages state for a MADSci Location Manager, providing transactional access to reading and writing location state
    with optimistic check-and-set and locking.
    """

    state_change_marker = "0"
    _redis_connection: Any = None
    shutdown: bool = False

    def __init__(
        self,
        settings: LocationManagerSettings,
        redis_connection: Optional[Any] = None,
    ) -> None:
        """
        Initialize a LocationStateHandler.
        """
        self.settings = settings
        self._manager_id = settings.manager_id
        self._redis_host = settings.redis_host
        self._redis_port = settings.redis_port
        self._redis_password = settings.redis_password
        self._redis_connection = redis_connection
        warnings.filterwarnings("ignore", category=InefficientAccessWarning)

    @property
    def _location_prefix(self) -> str:
        return f"madsci:location_manager:{self._manager_id}"

    @property
    def _redis_client(self) -> Any:
        """
        Returns a redis.Redis client, but only creates one connection.
        MyPy can't handle Redis object return types for some reason, so no type-hinting.
        """
        if self._redis_connection is None:
            self._redis_connection = redis.Redis(
                host=str(self._redis_host),
                port=int(self._redis_port),
                db=0,
                decode_responses=True,
                password=self._redis_password if self._redis_password else None,
            )
        return self._redis_connection

    @property
    def _locations(self) -> RedisDict:
        return RedisDict(
            key=f"{self._location_prefix}:locations", redis=self._redis_client
        )

    def location_state_lock(self) -> Redlock:
        """
        Gets a lock on the location state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us.
        """
        return Redlock(
            key=f"{self._location_prefix}:state_lock",
            masters={self._redis_client},
            auto_release_time=60,
        )

    def mark_state_changed(self) -> int:
        """Marks the state as changed and returns the current state change counter"""
        return int(self._redis_client.incr(f"{self._location_prefix}:state_changed"))

    def has_state_changed(self) -> bool:
        """Returns True if the state has changed since the last time this method was called"""
        state_change_marker = self._redis_client.get(
            f"{self._location_prefix}:state_changed"
        )
        if state_change_marker != self.state_change_marker:
            self.state_change_marker = state_change_marker
            return True
        return False

    # Location Management Methods
    def get_location(self, location_id: str) -> Optional[Location]:
        """
        Returns a location by ID
        """
        try:
            location_data = self._locations.get(location_id)
            if location_data is None:
                return None
            return Location.model_validate(location_data)
        except (ValidationError, KeyError):
            return None

    def get_locations(self) -> list[Location]:
        """
        Returns all locations as a list
        """
        valid_locations = []
        for location_id in self._locations:
            try:
                location_data = self._locations[location_id]
                valid_locations.append(Location.model_validate(location_data))
            except ValidationError:
                continue
        return valid_locations

    def set_location(
        self, location_id: str, location: Union[Location, dict[str, Any]]
    ) -> Location:
        """
        Sets a location by ID and returns the stored location
        """
        if isinstance(location, Location):
            location_dump = location.model_dump(mode="json")
        else:
            location_obj = Location.model_validate(location)
            location_dump = location_obj.model_dump(mode="json")
            location = location_obj

        self._locations[location_id] = location_dump
        self.mark_state_changed()
        return location

    def delete_location(self, location_id: str) -> bool:
        """
        Deletes a location by ID. Returns True if the location was deleted, False if it didn't exist.
        """
        try:
            if location_id in self._locations:
                del self._locations[location_id]
                self.mark_state_changed()
                return True
            return False
        except KeyError:
            return False

    def update_location(self, location_id: str, location: Location) -> Location:
        """
        Updates a location and returns the updated location.
        """
        return self.set_location(location_id, location)
