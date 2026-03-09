"""
State management for the LocationManager
"""

import warnings
from typing import Any, Optional, Union

from madsci.common.db_handlers import PyRedisHandler, RedisHandler
from madsci.common.types.location_types import Location, LocationManagerSettings
from pydantic import ValidationError


class LocationStateHandler:
    """
    Manages state for a MADSci Location Manager, providing transactional access to reading and writing location state
    with optimistic check-and-set and locking.
    """

    state_change_marker = "0"
    shutdown: bool = False

    def __init__(
        self,
        settings: LocationManagerSettings,
        manager_id: str,
        redis_connection: Optional[Any] = None,
        redis_handler: Optional[RedisHandler] = None,
    ) -> None:
        """
        Initialize a LocationStateHandler.
        """
        if redis_connection is not None:
            warnings.warn(
                "The 'redis_connection' parameter is deprecated. Use 'redis_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.settings = settings
        self._manager_id = manager_id

        # Initialize Redis handler
        if redis_handler is not None:
            self._redis_handler = redis_handler
        elif redis_connection is not None:
            self._redis_handler = PyRedisHandler(redis_connection)
        else:
            self._redis_handler = PyRedisHandler.from_settings(
                host=str(settings.redis_host),
                port=int(settings.redis_port),
                password=settings.redis_password or None,
            )

        # Suppress InefficientAccessWarning from pottery if using PyRedisHandler
        try:
            from pottery import InefficientAccessWarning  # noqa: PLC0415

            warnings.filterwarnings("ignore", category=InefficientAccessWarning)
        except ImportError:
            pass

    @property
    def _location_prefix(self) -> str:
        return f"madsci:location_manager:{self._manager_id}"

    @property
    def _locations(self) -> Any:
        return self._redis_handler.create_dict(f"{self._location_prefix}:locations")

    def location_state_lock(self) -> Any:
        """
        Gets a lock on the location state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us.
        """
        return self._redis_handler.create_lock(
            f"{self._location_prefix}:state_lock",
            auto_release_time=60,
        )

    def mark_state_changed(self) -> int:
        """Marks the state as changed and returns the current state change counter"""
        return int(self._redis_handler.incr(f"{self._location_prefix}:state_changed"))

    def has_state_changed(self) -> bool:
        """Returns True if the state has changed since the last time this method was called"""
        state_change_marker = self._redis_handler.get(
            f"{self._location_prefix}:state_changed"
        )
        if state_change_marker != self.state_change_marker:
            self.state_change_marker = state_change_marker
            return True
        return False

    def close(self) -> None:
        """Release Redis connections and resources."""
        self._redis_handler.close()

    # Location Management Methods
    def get_location(self, location_name: str) -> Optional[Location]:
        """
        Returns a location by ID
        """
        try:
            location_data = self._locations.get(location_name)
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
        for location_name in self._locations:
            try:
                location_data = self._locations[location_name]
                valid_locations.append(Location.model_validate(location_data))
            except ValidationError:
                continue
        return valid_locations

    def add_location(
        self, location: Union[Location, dict[str, Any]]
    ) -> Optional[Location]:
        """
        Sets a location by ID and returns the stored location
        """
        if isinstance(location, Location):
            location_dump = location.model_dump(mode="json")
        else:
            location_obj = Location.model_validate(location)
            location_dump = location_obj.model_dump(mode="json")
            location = location_obj
        if location_dump["location_name"] in self._locations:
            return None
        self._locations[location_dump["location_name"]] = location_dump
        self.mark_state_changed()
        return location

    def delete_location(self, location_name: str) -> bool:
        """
        Deletes a location by ID. Returns True if the location was deleted, False if it didn't exist.
        """
        try:
            if location_name in self._locations:
                del self._locations[location_name]
                self.mark_state_changed()
                return True
            return False
        except KeyError:
            return False

    def update_location(self, location: Union[Location, dict]) -> Location:
        """
        Updates a location and returns the updated location.
        """
        if isinstance(location, Location):
            location_dump = location.model_dump(mode="json")
        else:
            location_obj = Location.model_validate(location)
            location_dump = location_obj.model_dump(mode="json")
            location = location_obj
        if location_dump["location_name"] not in self._locations:
            raise KeyError(f"Location {location['location_name']} does not exist")
        if (
            self.get_location(location_dump["location_name"]).location_id
            != location.location_id
        ):
            raise ValueError(
                f"Location name {location_dump['location_name']} is already in use by a different location. make sure to use the right id"
            )
        self._locations[location_dump["location_name"]] = location_dump
        self.mark_state_changed()
        return location
