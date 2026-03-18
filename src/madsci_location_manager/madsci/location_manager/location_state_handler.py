"""
State management for the LocationManager.

Uses MongoDB (document storage) for persistent location CRUD,
and Redis for transient state (locks, change counters).
"""

import warnings
from typing import Any, Optional, Union

from madsci.common.db_handlers import (
    DocumentStorageHandler,
    PyDocumentStorageHandler,
    PyRedisHandler,
    RedisHandler,
)
from madsci.common.types.location_types import (
    Location,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError


class LocationStateHandler:
    """
    Manages state for a MADSci Location Manager.

    - Document storage handler: persistent location CRUD
    - Redis handler: transient state (locks, change counters)
    """

    state_change_marker = "0"
    shutdown: bool = False

    def __init__(
        self,
        settings: LocationManagerSettings,
        manager_id: str,
        redis_connection: Optional[Any] = None,
        redis_handler: Optional[RedisHandler] = None,
        document_handler: Optional[DocumentStorageHandler] = None,
    ) -> None:
        """
        Initialize a LocationStateHandler.

        Parameters
        ----------
        settings:
            Location manager settings.
        manager_id:
            Unique identifier for this manager instance.
        redis_connection:
            Deprecated. Use redis_handler instead.
        redis_handler:
            Redis handler for transient state (locks, change counters).
        document_handler:
            Document storage handler for persistent location storage.
        """
        if redis_connection is not None:
            warnings.warn(
                "The 'redis_connection' parameter is deprecated. Use 'redis_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.settings = settings
        self._manager_id = manager_id

        # Initialize Redis handler (transient state)
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

        # Initialize document storage handler (persistent locations)
        if document_handler is not None:
            self._document_handler = document_handler
        else:
            self._document_handler = PyDocumentStorageHandler.from_url(
                str(settings.document_db_url),
                settings.database_name,
            )

        # Set up collections
        self._locations_collection = self._document_handler.get_collection("locations")
        self._repr_templates_collection = self._document_handler.get_collection(
            "representation_templates"
        )
        self._location_templates_collection = self._document_handler.get_collection(
            "location_templates"
        )

        # Ensure minimum unique indexes exist for correctness.
        # These are a subset of what schema.json defines; the full set is
        # applied by ensure_schema_indexes() in the manager's initialize().
        self._locations_collection.create_index(
            "location_name", unique=True, name="location_name_unique"
        )
        self._repr_templates_collection.create_index(
            "template_name", unique=True, name="template_name_unique"
        )
        self._location_templates_collection.create_index(
            "template_name", unique=True, name="template_name_unique"
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
        """Marks the state as changed and returns the current state change counter."""
        return int(self._redis_handler.incr(f"{self._location_prefix}:state_changed"))

    def has_state_changed(self) -> bool:
        """Returns True if the state has changed since the last time this method was called."""
        state_change_marker = self._redis_handler.get(
            f"{self._location_prefix}:state_changed"
        )
        if state_change_marker != self.state_change_marker:
            self.state_change_marker = state_change_marker
            return True
        return False

    def close(self) -> None:
        """Release both Redis and document storage connections and resources."""
        self._redis_handler.close()
        self._document_handler.close()

    # Location Management Methods (MongoDB-backed)

    def get_location(self, location_name: str) -> Optional[Location]:
        """Returns a location by name."""
        try:
            location_data = self._locations_collection.find_one(
                {"location_name": location_name}
            )
            if location_data is None:
                return None
            return Location.model_validate(location_data)
        except (ValidationError, KeyError):
            return None

    def get_location_by_id(self, location_id: str) -> Optional[Location]:
        """Returns a location by ID (O(1) with MongoDB index)."""
        try:
            location_data = self._locations_collection.find_one(
                {"location_id": location_id}
            )
            if location_data is None:
                return None
            return Location.model_validate(location_data)
        except (ValidationError, KeyError):
            return None

    def get_locations(self) -> list[Location]:
        """Returns all locations as a list."""
        valid_locations = []
        for location_data in self._locations_collection.find().to_list():
            try:
                valid_locations.append(Location.model_validate(location_data))
            except ValidationError:
                continue
        return valid_locations

    def add_location(
        self, location: Union[Location, dict[str, Any]]
    ) -> Optional[Location]:
        """
        Adds a location by name and returns the stored location.
        Returns None if the name already exists.
        """
        if not isinstance(location, Location):
            location = Location.model_validate(location)

        try:
            self._locations_collection.insert_one(location.model_dump(mode="json"))
        except DuplicateKeyError:
            return None

        self.mark_state_changed()
        return location

    def delete_location(self, location_name: str) -> bool:
        """
        Deletes a location by name.
        Returns True if the location was deleted, False if it didn't exist.
        """
        result = self._locations_collection.delete_one({"location_name": location_name})
        if result.deleted_count > 0:
            self.mark_state_changed()
            return True
        return False

    def update_location(self, location: Union[Location, dict]) -> Location:
        """
        Updates a location and returns the updated location.
        Raises KeyError if the location doesn't exist, ValueError if ID mismatches.
        """
        if not isinstance(location, Location):
            location = Location.model_validate(location)

        existing = self._locations_collection.find_one(
            {"location_name": location.location_name}
        )
        if existing is None:
            raise KeyError(f"Location {location.location_name} does not exist")

        existing_location = Location.model_validate(existing)
        if existing_location.location_id != location.location_id:
            raise ValueError(
                f"Location name {location.location_name} is already in use by a different location. Make sure to use the right ID."
            )

        self._locations_collection.replace_one(
            {"location_name": location.location_name},
            location.model_dump(mode="json"),
        )
        self.mark_state_changed()
        return location

    # Representation Template CRUD (MongoDB-backed)

    def get_representation_template(
        self, template_name: str
    ) -> Optional[LocationRepresentationTemplate]:
        """Returns a representation template by name."""
        try:
            data = self._repr_templates_collection.find_one(
                {"template_name": template_name}
            )
            if data is None:
                return None
            return LocationRepresentationTemplate.model_validate(data)
        except (ValidationError, KeyError):
            return None

    def get_representation_templates(self) -> list[LocationRepresentationTemplate]:
        """Returns all representation templates."""
        templates = []
        for data in self._repr_templates_collection.find().to_list():
            try:
                templates.append(LocationRepresentationTemplate.model_validate(data))
            except ValidationError:
                continue
        return templates

    def add_representation_template(
        self,
        template: Union[LocationRepresentationTemplate, dict[str, Any]],
    ) -> Optional[LocationRepresentationTemplate]:
        """Adds a representation template. Returns None if the name already exists."""
        if not isinstance(template, LocationRepresentationTemplate):
            template = LocationRepresentationTemplate.model_validate(template)

        try:
            self._repr_templates_collection.insert_one(template.model_dump(mode="json"))
        except DuplicateKeyError:
            return None

        return template

    def update_representation_template(
        self,
        template: Union[LocationRepresentationTemplate, dict[str, Any]],
    ) -> LocationRepresentationTemplate:
        """Updates a representation template. Raises KeyError if not found, ValueError if ID mismatch."""
        if not isinstance(template, LocationRepresentationTemplate):
            template = LocationRepresentationTemplate.model_validate(template)

        existing = self._repr_templates_collection.find_one(
            {"template_name": template.template_name}
        )
        if existing is None:
            raise KeyError(
                f"Representation template '{template.template_name}' does not exist"
            )

        existing_template = LocationRepresentationTemplate.model_validate(existing)
        if existing_template.template_id != template.template_id:
            raise ValueError(
                f"Template name '{template.template_name}' is already in use by a different template"
            )

        self._repr_templates_collection.replace_one(
            {"template_name": template.template_name},
            template.model_dump(mode="json"),
        )
        return template

    def delete_representation_template(self, template_name: str) -> bool:
        """Deletes a representation template by name. Returns True if deleted, False if not found."""
        result = self._repr_templates_collection.delete_one(
            {"template_name": template_name}
        )
        return result.deleted_count > 0

    # Location Template CRUD (MongoDB-backed)

    def get_location_template(self, template_name: str) -> Optional[LocationTemplate]:
        """Returns a location template by name."""
        try:
            data = self._location_templates_collection.find_one(
                {"template_name": template_name}
            )
            if data is None:
                return None
            return LocationTemplate.model_validate(data)
        except (ValidationError, KeyError):
            return None

    def get_location_templates(self) -> list[LocationTemplate]:
        """Returns all location templates."""
        templates = []
        for data in self._location_templates_collection.find().to_list():
            try:
                templates.append(LocationTemplate.model_validate(data))
            except ValidationError:
                continue
        return templates

    def add_location_template(
        self,
        template: Union[LocationTemplate, dict[str, Any]],
    ) -> Optional[LocationTemplate]:
        """Adds a location template. Returns None if the name already exists."""
        if not isinstance(template, LocationTemplate):
            template = LocationTemplate.model_validate(template)

        try:
            self._location_templates_collection.insert_one(
                template.model_dump(mode="json")
            )
        except DuplicateKeyError:
            return None

        return template

    def update_location_template(
        self,
        template: Union[LocationTemplate, dict[str, Any]],
    ) -> LocationTemplate:
        """Updates a location template. Raises KeyError if not found, ValueError if ID mismatch."""
        if not isinstance(template, LocationTemplate):
            template = LocationTemplate.model_validate(template)

        existing = self._location_templates_collection.find_one(
            {"template_name": template.template_name}
        )
        if existing is None:
            raise KeyError(
                f"Location template '{template.template_name}' does not exist"
            )

        existing_template = LocationTemplate.model_validate(existing)
        if existing_template.template_id != template.template_id:
            raise ValueError(
                f"Template name '{template.template_name}' is already in use by a different template"
            )

        self._location_templates_collection.replace_one(
            {"template_name": template.template_name},
            template.model_dump(mode="json"),
        )
        return template

    def delete_location_template(self, template_name: str) -> bool:
        """Deletes a location template by name. Returns True if deleted, False if not found."""
        result = self._location_templates_collection.delete_one(
            {"template_name": template_name}
        )
        return result.deleted_count > 0
