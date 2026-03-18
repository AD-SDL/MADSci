"""MADSci Location Manager using AbstractManagerBase."""

import asyncio
import contextlib
import warnings
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, AsyncGenerator, Optional

import yaml
from classy_fastapi import delete, get, post
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from madsci.client.resource_client import ResourceClient
from madsci.common.context import get_current_madsci_context
from madsci.common.db_handlers import DocumentStorageHandler, RedisHandler
from madsci.common.document_db_version_checker import (
    DocumentDBVersionChecker,
    ensure_schema_indexes,
)
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import ownership_class
from madsci.common.settings_dir import walk_up_find
from madsci.common.types.document_db_migration_types import DocumentDBMigrationSettings
from madsci.common.types.event_types import EventType
from madsci.common.types.location_types import (
    CreateLocationFromTemplateRequest,
    Location,
    LocationImportResult,
    LocationManagerHealth,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from madsci.common.types.resource_types import Slot
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.location_manager.location_state_handler import LocationStateHandler
from madsci.location_manager.transfer_planner import TransferPlanner

# Module-level constants for Body() calls to avoid B008 linting errors
REPRESENTATION_VAL_BODY = Body(...)


@ownership_class()
class LocationManager(AbstractManagerBase[LocationManagerSettings]):
    """MADSci Location Manager using the new AbstractManagerBase pattern.

    This class is decorated with @ownership_class() which automatically
    establishes ownership context for all public methods, eliminating the
    need for manual `with ownership_context():` blocks in each endpoint.
    """

    SETTINGS_CLASS = LocationManagerSettings

    transfer_planner: Optional[TransferPlanner] = None

    def __init__(
        self,
        settings: Optional[LocationManagerSettings] = None,
        redis_connection: Optional[Any] = None,
        redis_handler: Optional[RedisHandler] = None,
        document_handler: Optional[DocumentStorageHandler] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the LocationManager."""
        if redis_connection is not None:
            warnings.warn(
                "The 'redis_connection' parameter is deprecated. Use 'redis_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.redis_connection = redis_connection
        self.redis_handler = redis_handler
        self.document_handler = document_handler
        super().__init__(settings=settings, **kwargs)

    def initialize(self, **_kwargs: Any) -> None:
        """Initialize manager-specific components."""

        manager_name = self._resolve_name()
        manager_id = self.settings.manager_id

        # Skip version validation if external handler was provided (e.g., in tests)
        if self.document_handler is not None:
            self.logger.info(
                "External document handler provided, skipping document DB version validation",
                event_type=EventType.MANAGER_START,
                manager_name=manager_name,
                manager_id=manager_id,
                manager_type="location",
                document_handler_external=True,
            )
        else:
            # Production path: validate document DB schema version
            self.logger.info(
                "Validating document DB schema version",
                event_type=EventType.MANAGER_START,
                manager_name=manager_name,
                manager_id=manager_id,
                manager_type="location",
                document_db=str(self.settings.document_db_url),
                database_name=self.settings.database_name,
            )

            schema_file_path = Path(__file__).parent / "schema.json"
            mig_cfg = DocumentDBMigrationSettings(database=self.settings.database_name)
            version_checker = DocumentDBVersionChecker(
                db_url=str(self.settings.document_db_url),
                database_name=self.settings.database_name,
                schema_file_path=str(schema_file_path),
                backup_dir=str(mig_cfg.backup_dir),
                logger=self.logger,
            )

            try:
                version_checker.validate_or_fail()
                self.logger.info(
                    "Document DB version validation completed successfully",
                    event_type=EventType.MANAGER_START,
                    manager_name=manager_name,
                    manager_id=manager_id,
                    manager_type="location",
                    database_name=self.settings.database_name,
                )
            except RuntimeError:
                self.logger.error(
                    "DATABASE VERSION MISMATCH DETECTED! SERVER STARTUP ABORTED!",
                    event_type=EventType.MANAGER_ERROR,
                    manager_name=manager_name,
                    manager_id=manager_id,
                    manager_type="location",
                    database_name=self.settings.database_name,
                    exc_info=True,
                )
                raise

        # Initialize state handler with dual handlers
        self.state_handler = LocationStateHandler(
            settings=self.settings,
            manager_id=self.settings.manager_id,
            redis_connection=self.redis_connection,
            redis_handler=self.redis_handler,
            document_handler=self.document_handler,
        )

        # Ensure all schema-defined indexes exist (idempotent).
        # This covers in-memory test handlers (which skip validate_or_fail)
        # and is idempotent with the version checker call for real document DB.
        schema_file = Path(__file__).parent / "schema.json"
        ensure_schema_indexes(
            self.state_handler._document_handler, schema_file, self.logger
        )

        # Initialize resource client with resource server URL from context
        # (must happen before seed file loading, which may create resources)
        context = get_current_madsci_context()
        resource_server_url = context.resource_server_url
        self.resource_client = ResourceClient(resource_server_url=resource_server_url)

        # Register default location container template
        self._register_default_resource_template()

        # Auto-migration: if document database is empty but cache has old-format data, migrate
        self._auto_migrate_from_redis()

        # Seed file loading: if document database is still empty and seed file exists, load it once
        self._seed_from_file()

        self.transfer_planner = TransferPlanner(
            state_handler=self.state_handler,
            transfer_capabilities=self.settings.transfer_capabilities,
            resource_client=self.resource_client,
        )

    def _register_default_resource_template(self) -> None:
        """Register a default location container template with the resource manager.

        This provides a generic Slot template that locations can reference via
        ``resource_template_name`` in seed files, ensuring container resources
        are created even before node-specific templates are registered.
        """
        try:
            location_slot = Slot(
                resource_name="location_container",
                resource_class="LocationContainer",
                capacity=1,
                attributes={
                    "slot_type": "location_container",
                    "description": "Default container resource for a lab location",
                },
            )
            self.resource_client.init_template(
                resource=location_slot,
                template_name="location_container",
                description="Default container resource for a lab location. Holds a single discrete item (e.g. a plate).",
                required_overrides=["resource_name"],
                tags=["location", "container", "slot"],
                version="1.0.0",
            )
        except Exception as e:
            self.logger.warning(
                "Failed to register default location container template",
                error=str(e),
            )

    def _auto_migrate_from_redis(self) -> None:
        """Auto-migrate locations from old Redis format to document database if document database is empty."""
        existing_locations = self.state_handler.get_locations()
        if existing_locations:
            return  # Document database already has data, skip migration

        # Check if cache has data at the old key prefix
        old_prefix = f"madsci:location_manager:{self.settings.manager_id}"
        old_dict_key = f"{old_prefix}:locations"
        try:
            old_locations = self.state_handler._redis_handler.create_dict(old_dict_key)
            if not old_locations:
                return  # No old cache data either

            self.logger.warning(
                "Auto-migrating locations from cache to document database. "
                "This is a one-time migration from the 0.7.1 format.",
                event_type=EventType.MANAGER_START,
                manager_id=self.settings.manager_id,
            )

            migrated_count = 0
            for _name, loc_data in old_locations.to_dict().items():
                try:
                    location = Location.model_validate(loc_data)
                    result = self.state_handler.add_location(location)
                    if result is not None:
                        migrated_count += 1
                except Exception as e:
                    self.logger.warning(
                        "Failed to migrate location from cache",
                        location_data=str(loc_data),
                        error=str(e),
                    )

            self.logger.info(
                "Cache to document database migration completed",
                event_type=EventType.MANAGER_START,
                migrated_count=migrated_count,
            )
        except Exception as e:
            self.logger.debug(
                "No legacy cache data to migrate (expected on fresh installs)",
                error=str(e),
            )

    def _seed_from_file(self) -> None:
        """Load seed locations from file if document database is empty and seed file exists.

        Supports two formats:
        - **Old format** (list): A flat list of Location objects. Loaded directly.
        - **New format** (dict): Keys ``representation_templates``, ``location_templates``,
          and ``locations``. Templates are registered first; locations may reference
          templates or be inline (old-style).
        """
        existing_locations = self.state_handler.get_locations()
        if existing_locations:
            return  # Document database already has data, skip seeding

        if not self.settings.seed_locations_file:
            return

        seed_path = Path(self.settings.seed_locations_file)
        if not seed_path.is_absolute():
            # Use walk-up discovery for relative paths
            resolved = walk_up_find(self.settings.seed_locations_file, Path.cwd())
            if resolved is not None:
                seed_path = resolved

        if not seed_path.exists():
            return  # Seed file doesn't exist, no error

        try:
            with seed_path.open() as f:
                data = yaml.safe_load(f)

            if not data:
                return

            if isinstance(data, list):
                # Old format: flat list of locations
                self._seed_locations_list(data)
            elif isinstance(data, dict):
                # New format: dict with optional template + location keys
                self._seed_from_dict(data)
            else:
                self.logger.warning(
                    "Unexpected seed file format",
                    seed_file=str(seed_path),
                    data_type=type(data).__name__,
                )
                return

            self.logger.info(
                "Loaded seed data from file",
                event_type=EventType.MANAGER_START,
                seed_file=str(seed_path),
            )
        except Exception as e:
            self.logger.warning(
                "Failed to read seed locations file",
                seed_file=str(seed_path),
                error=str(e),
            )

    def _seed_locations_list(self, locations_data: list) -> None:
        """Seed locations from a flat list (old format)."""
        seeded_count = 0
        for loc_data in locations_data:
            try:
                location = Location.model_validate(loc_data)
                # Clear stale resource_id from seed data
                location.resource_id = None
                # Initialize resource from template if configured (lazy on failure)
                try:
                    location.resource_id = self._initialize_location_resource(location)
                except Exception:
                    location.resource_id = None
                    self.logger.info(
                        "Resource template not available, will reconcile later",
                        resource_template_name=location.resource_template_name,
                        location_name=location.location_name,
                    )
                result = self.state_handler.add_location(location)
                if result is not None:
                    seeded_count += 1
            except Exception as e:
                self.logger.warning(
                    "Failed to load location from seed file",
                    location_data=loc_data,
                    error=str(e),
                )

        self.logger.info(
            "Seeded locations from list format",
            seeded_count=seeded_count,
        )

    def _seed_from_dict(self, data: dict) -> None:
        """Seed from new dict format with templates and locations."""
        # 1. Load representation templates
        for tmpl_data in data.get("representation_templates", []):
            self._seed_repr_template(tmpl_data)

        # 2. Load location templates
        for tmpl_data in data.get("location_templates", []):
            self._seed_location_template(tmpl_data)

        # 3. Load locations (may be template-based or inline)
        for loc_data in data.get("locations", []):
            self._seed_location_entry(loc_data)

    def _seed_repr_template(self, tmpl_data: dict) -> None:
        """Seed a single representation template from dict data."""
        try:
            tmpl = LocationRepresentationTemplate.model_validate(tmpl_data)
            if (
                self.state_handler.get_representation_template(tmpl.template_name)
                is None
            ):
                self.state_handler.add_representation_template(tmpl)
        except Exception as e:
            self.logger.warning(
                "Failed to load representation template from seed",
                template_data=tmpl_data,
                error=str(e),
            )

    def _seed_location_template(self, tmpl_data: dict) -> None:
        """Seed a single location template from dict data."""
        try:
            tmpl = LocationTemplate.model_validate(tmpl_data)
            if self.state_handler.get_location_template(tmpl.template_name) is None:
                self.state_handler.add_location_template(tmpl)
        except Exception as e:
            self.logger.warning(
                "Failed to load location template from seed",
                template_data=tmpl_data,
                error=str(e),
            )

    def _seed_location_entry(self, loc_data: dict) -> None:
        """Seed a single location entry (template-based or inline)."""
        try:
            if "template_name" in loc_data and "node_bindings" in loc_data:
                request = CreateLocationFromTemplateRequest.model_validate(loc_data)
                self._create_location_from_template(request)
            else:
                location = Location.model_validate(loc_data)
                location.resource_id = None
                try:
                    location.resource_id = self._initialize_location_resource(location)
                except Exception:
                    location.resource_id = None
                self.state_handler.add_location(location)
        except Exception as e:
            self.logger.warning(
                "Failed to load location from seed file",
                location_data=loc_data,
                error=str(e),
            )

    def _initialize_location_resource(self, location_def: Location) -> Optional[str]:
        """Initialize a resource for a location based on its resource_template_name.

        Args:
            location_def: Location containing the resource_template_name and optional overrides

        Returns:
            Optional[str]: The resource_id of the created resource, or None if no resource created
        """
        if not location_def.resource_template_name:
            return None

        try:
            resource_name = location_def.location_name

            # Create resource from template
            created_resource = self.resource_client.create_resource_from_template(
                template_name=location_def.resource_template_name,
                resource_name=resource_name,
                overrides=location_def.resource_template_overrides or {},
                add_to_database=True,
            )

            if created_resource:
                return created_resource.resource_id

        except Exception as e:
            # Log the error but continue - locations can still function without associated resources
            self.logger.warning(
                "Failed to create resource from template",
                event_type=EventType.RESOURCE_CREATE,
                template_name=location_def.resource_template_name,
                location_id=location_def.location_id,
                location_name=location_def.location_name,
                error=str(e),
                exc_info=True,
            )
            return None

        return None

    def _validate_or_recreate_location_resource(
        self, location_def: Location, existing_resource_id: str
    ) -> Optional[str]:
        """Check if existing resource still exists. If so, reuse it. If not, create a new one.

        Args:
            location_def: Location containing the resource_template_name and overrides
            existing_resource_id: The existing resource ID to validate

        Returns:
            Optional[str]: The resource_id (existing or newly created), or None if failed
        """
        if not location_def.resource_template_name:
            return None

        try:
            # Simply check if the existing resource still exists in the resource manager
            existing_resource = self.resource_client.get_resource(existing_resource_id)

            if existing_resource:
                # Resource exists, reuse it
                self.logger.debug(
                    "Reusing existing resource for location",
                    existing_resource_id=existing_resource_id,
                    location_id=location_def.location_id,
                    location_name=location_def.location_name,
                )
                return existing_resource_id
            self.logger.info(
                "Existing resource missing; recreating for location",
                event_type=EventType.RESOURCE_CREATE,
                existing_resource_id=existing_resource_id,
                location_id=location_def.location_id,
                location_name=location_def.location_name,
            )

        except Exception as e:
            self.logger.info(
                "Failed to validate existing location resource; recreating",
                event_type=EventType.RESOURCE_CREATE,
                existing_resource_id=existing_resource_id,
                location_id=location_def.location_id,
                location_name=location_def.location_name,
                error=str(e),
                exc_info=True,
            )

        # Existing resource doesn't exist, create a new one
        return self._initialize_location_resource(location_def)

    def get_health(self) -> LocationManagerHealth:
        """Get the health status of the Location Manager."""
        health = LocationManagerHealth()

        try:
            # Test document DB connection
            if hasattr(self.state_handler, "_document_handler"):
                health.document_db_connected = (
                    self.state_handler._document_handler.ping()
                )
            else:
                health.document_db_connected = None

            # Test cache connection if configured
            if hasattr(self.state_handler, "_redis_handler"):
                health.cache_connected = self.state_handler._redis_handler.ping()
            else:
                health.cache_connected = None

            # Count managed locations
            locations = self.state_handler.get_locations()
            health.num_locations = len(locations)

            # Count templates
            health.num_representation_templates = len(
                self.state_handler.get_representation_templates()
            )
            health.num_location_templates = len(
                self.state_handler.get_location_templates()
            )

            # Count unresolved locations (have resource_template_name but no resource_id)
            health.num_unresolved_locations = sum(
                1
                for loc in locations
                if loc.resource_template_name and loc.resource_id is None
            )

            health.healthy = True
            health.description = "Location Manager is running normally"

        except Exception as e:
            health.healthy = False
            if "redis" in str(e).lower():
                health.cache_connected = False
            if "mongo" in str(e).lower() or "document" in str(e).lower():
                health.document_db_connected = False
            health.description = f"Health check failed: {e!s}"

        return health

    def close(self) -> None:
        """Override to close state handler and release DB connections."""
        if hasattr(self, "state_handler"):
            self.state_handler.close()
        super().close()

    @get("/locations", tags=["Locations"])
    def get_locations(self) -> list[Location]:
        """Get all locations."""
        return self.state_handler.get_locations()

    @post("/location", tags=["Locations"])
    def add_location(self, location: Location) -> Location:
        """Add a new location."""
        with self.span(
            "location.create",
            attributes={"location.name": location.location_name},
        ):
            if location.resource_id is not None:
                resource_id = self._validate_or_recreate_location_resource(
                    location, location.resource_id
                )
            else:
                resource_id = self._initialize_location_resource(location)
            location.resource_id = resource_id
            result = self.state_handler.add_location(location)

            if result is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Location with name '{location.location_name}' already exists",
                )

            # Rebuild transfer graph since new location may affect transfer capabilities
            self.transfer_planner.rebuild_transfer_graph()

            return result

    @get("/location", tags=["Locations"])
    def get_location_by_query(
        self, location_id: Optional[str] = None, name: Optional[str] = None
    ) -> Location:
        """Get a specific location by ID or name."""
        # Exactly one of location_id or name must be provided
        if (location_id is None) == (name is None):
            raise HTTPException(
                status_code=400,
                detail="Exactly one of 'location_id' or 'name' query parameter must be provided",
            )

        if location_id is not None:
            # Search by ID
            location = self.state_handler.get_location_by_id(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Location with ID '{location_id}' not found",
                )
            return location
        # Search by name
        location = self.state_handler.get_location(name)
        if location is not None:
            return location
        raise HTTPException(
            status_code=404, detail=f"Location with name '{name}' not found"
        )

    @get("/location/{location_name}", tags=["Locations"])
    def get_location(self, location_name: str) -> Location:
        """Get a specific location by name."""
        with self.span(
            "location.get",
            attributes={"location.name": location_name},
        ):
            location = self.state_handler.get_location(location_name)

            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_name} not found"
                )
        return location

    @delete("/location/{location_name}", tags=["Locations"])
    def delete_location(self, location_name: str) -> dict[str, str]:
        """Delete a specific location by name."""
        success = self.state_handler.delete_location(location_name)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Location {location_name} not found"
            )
        # Rebuild transfer graph since deleted location affects transfer capabilities
        self.transfer_planner.rebuild_transfer_graph()
        return {"message": f"Location {location_name} deleted successfully"}

    @post(
        "/location/{location_name}/set_representation/{node_name}", tags=["Locations"]
    )
    def set_representation(
        self,
        location_name: str,
        node_name: str,
        representation_val: Annotated[Any, REPRESENTATION_VAL_BODY],
    ) -> Location:
        """Set representations for a location for a specific node."""
        location = self.state_handler.get_location(location_name)

        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_name} not found"
            )

        # Update the location with new representations
        if location.representations is None:
            location.representations = {}
        location.representations[node_name] = representation_val

        result = self.state_handler.update_location(location)
        # Rebuild transfer graph since representations affect transfer capabilities
        self.transfer_planner.rebuild_transfer_graph()
        return result

    @delete(
        "/location/{location_name}/remove_representation/{node_name}",
        tags=["Locations"],
    )
    def remove_representation(
        self,
        location_name: str,
        node_name: str,
    ) -> Location:
        """Remove representations for a location for a specific node."""
        location = self.state_handler.get_location(location_name)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_name} not found"
            )

        # Check if representations exist and if the node_name exists
        if (
            location.representations is None
            or node_name not in location.representations
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Representation for node '{node_name}' not found in location {location_name}",
            )

        # Remove the representation for the specified node
        del location.representations[node_name]

        # If no representations remain, set to empty dict (consistent with existing behavior)
        if not location.representations:
            location.representations = {}

        result = self.state_handler.update_location(location)
        # Rebuild transfer graph since representations affect transfer capabilities
        self.transfer_planner.rebuild_transfer_graph()
        return result

    @post("/location/{location_name}/attach_resource", tags=["Locations"])
    def attach_resource(
        self,
        location_name: str,
        resource_id: str,
    ) -> Location:
        """Attach a resource to a location."""
        with self.span(
            "attachment.create",
            attributes={
                "location.name": location_name,
                "resource.id": resource_id,
            },
        ):
            location = self.state_handler.get_location(location_name)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_name} not found"
                )

            location.resource_id = resource_id

            # Note: We don't sync resource_id changes to definition as resource_id is runtime-only
            # The definition uses resource_template_name for resource initialization
            return self.state_handler.update_location(location)

    @delete("/location/{location_name}/detach_resource", tags=["Locations"])
    def detach_resource(
        self,
        location_name: str,
    ) -> Location:
        """Detach the resource from a location."""
        location = self.state_handler.get_location(location_name)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_name} not found"
            )

        # Check if location has a resource attached
        if location.resource_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"No resource attached to location {location_name}",
            )

        # Detach the resource
        location.resource_id = None

        # Note: We don't sync resource_id changes to definition as resource_id is runtime-only
        # The definition uses resource_template_name for resource initialization
        return self.state_handler.update_location(location)

    @post("/locations/import", tags=["Locations"])
    def import_locations(
        self, locations: list[Location], overwrite: bool = False
    ) -> LocationImportResult:
        """Import multiple locations in bulk.

        Parameters
        ----------
        locations:
            List of Location objects to import.
        overwrite:
            If True, overwrite existing locations with the same name.
            If False (default), skip duplicates.

        Returns
        -------
        LocationImportResult with counts and imported locations.
        """
        result = LocationImportResult()
        for location in locations:
            try:
                existing = self.state_handler.get_location(location.location_name)
                if existing is not None:
                    if overwrite:
                        # Update the existing location, preserving the existing ID
                        location.location_id = existing.location_id
                        self.state_handler.update_location(location)
                        result.imported += 1
                        result.locations.append(location)
                    else:
                        result.skipped += 1
                else:
                    added = self.state_handler.add_location(location)
                    if added is not None:
                        result.imported += 1
                        result.locations.append(added)
                    else:
                        result.skipped += 1
            except Exception as e:
                result.errors.append(
                    f"Error importing location '{location.location_name}': {e!s}"
                )

        # Rebuild transfer graph after bulk import
        if result.imported > 0:
            self.transfer_planner.rebuild_transfer_graph()

        return result

    @get("/locations/export", tags=["Locations"])
    def export_locations(self) -> list[Location]:
        """Export all locations as a JSON list.

        Semantically distinct from GET /locations for import/export workflows.
        """
        return self.state_handler.get_locations()

    # --- Representation Template Endpoints ---

    @get("/representation_templates", tags=["Representation Templates"])
    def get_representation_templates(self) -> list[LocationRepresentationTemplate]:
        """Get all representation templates."""
        return self.state_handler.get_representation_templates()

    @get(
        "/representation_template/{template_name}",
        tags=["Representation Templates"],
    )
    def get_representation_template(
        self, template_name: str
    ) -> LocationRepresentationTemplate:
        """Get a representation template by name."""
        template = self.state_handler.get_representation_template(template_name)
        if template is None:
            raise HTTPException(
                status_code=404,
                detail=f"Representation template '{template_name}' not found",
            )
        return template

    @post("/representation_template", tags=["Representation Templates"])
    def create_representation_template(
        self, template: LocationRepresentationTemplate
    ) -> LocationRepresentationTemplate:
        """Create a new representation template."""
        result = self.state_handler.add_representation_template(template)
        if result is None:
            raise HTTPException(
                status_code=409,
                detail=f"Representation template '{template.template_name}' already exists",
            )
        return result

    @post("/representation_template/init", tags=["Representation Templates"])
    def init_representation_template(
        self, template: LocationRepresentationTemplate
    ) -> LocationRepresentationTemplate:
        """Idempotent init: get-or-create, version-update.

        If template exists with same version, return it unchanged.
        If template exists with different version, update and return.
        If template doesn't exist, create and return.
        """
        existing = self.state_handler.get_representation_template(
            template.template_name
        )

        if existing is None:
            # Create new
            result = self.state_handler.add_representation_template(template)
            if result is None:
                # Race condition: another request created it
                result = self.state_handler.get_representation_template(
                    template.template_name
                )
                if result is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create or retrieve representation template '{template.template_name}'",
                    )
                return result
            # Trigger reconciliation for locations referencing this template
            self._reconcile_for_repr_template(template.template_name)
            return result

        if existing.version == template.version:
            # Same version, return existing
            return existing

        # Version differs, update
        template.template_id = existing.template_id
        template.updated_at = datetime.now()
        result = self.state_handler.update_representation_template(template)
        # Trigger reconciliation for locations referencing this template
        self._reconcile_for_repr_template(template.template_name)
        return result

    @delete(
        "/representation_template/{template_name}",
        tags=["Representation Templates"],
    )
    def delete_representation_template(self, template_name: str) -> dict[str, str]:
        """Delete a representation template by name."""
        success = self.state_handler.delete_representation_template(template_name)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Representation template '{template_name}' not found",
            )
        return {
            "message": f"Representation template '{template_name}' deleted successfully"
        }

    # --- Location Template Endpoints ---

    @get("/location_templates", tags=["Location Templates"])
    def get_location_templates(self) -> list[LocationTemplate]:
        """Get all location templates."""
        return self.state_handler.get_location_templates()

    @get("/location_template/{template_name}", tags=["Location Templates"])
    def get_location_template(self, template_name: str) -> LocationTemplate:
        """Get a location template by name."""
        template = self.state_handler.get_location_template(template_name)
        if template is None:
            raise HTTPException(
                status_code=404,
                detail=f"Location template '{template_name}' not found",
            )
        return template

    @post("/location_template", tags=["Location Templates"])
    def create_location_template(self, template: LocationTemplate) -> LocationTemplate:
        """Create a new location template."""
        result = self.state_handler.add_location_template(template)
        if result is None:
            raise HTTPException(
                status_code=409,
                detail=f"Location template '{template.template_name}' already exists",
            )
        return result

    @post("/location_template/init", tags=["Location Templates"])
    def init_location_template(self, template: LocationTemplate) -> LocationTemplate:
        """Idempotent init: get-or-create, version-update.

        If template exists with same version, return it unchanged.
        If template exists with different version, update and return.
        If template doesn't exist, create and return.
        """
        existing = self.state_handler.get_location_template(template.template_name)

        if existing is None:
            result = self.state_handler.add_location_template(template)
            if result is None:
                result = self.state_handler.get_location_template(
                    template.template_name
                )
                if result is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create or retrieve location template '{template.template_name}'",
                    )
                return result
            return result

        if existing.version == template.version:
            return existing

        template.template_id = existing.template_id
        template.updated_at = datetime.now()
        return self.state_handler.update_location_template(template)

    @delete("/location_template/{template_name}", tags=["Location Templates"])
    def delete_location_template(self, template_name: str) -> dict[str, str]:
        """Delete a location template by name."""
        success = self.state_handler.delete_location_template(template_name)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Location template '{template_name}' not found",
            )
        return {"message": f"Location template '{template_name}' deleted successfully"}

    # --- Create Location from Template ---

    @post("/location/from_template", tags=["Location Templates"])
    def create_location_from_template(
        self, request: CreateLocationFromTemplateRequest
    ) -> Location:
        """Create a new location by instantiating a LocationTemplate.

        Requires node bindings to map abstract roles to concrete node instance names.
        Representation data is merged from template defaults + overrides.
        """
        return self._create_location_from_template(request)

    def _create_location_from_template(
        self, request: CreateLocationFromTemplateRequest
    ) -> Location:
        """Internal implementation for creating a location from a template."""
        # Look up the location template
        loc_template = self.state_handler.get_location_template(request.template_name)
        if loc_template is None:
            raise HTTPException(
                status_code=404,
                detail=f"Location template '{request.template_name}' not found",
            )

        # Build representations by merging template defaults with overrides
        representations: dict[str, Any] = {}
        for role, repr_template_name in loc_template.representation_templates.items():
            node_name = request.node_bindings.get(role)
            if node_name is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Missing node binding for role '{role}'",
                )

            # Look up representation template
            repr_template = self.state_handler.get_representation_template(
                repr_template_name
            )

            overrides = request.representation_overrides.get(role, {})

            if repr_template is not None:
                # Validate required overrides are provided
                missing = [
                    field
                    for field in repr_template.required_overrides
                    if field not in overrides
                ]
                if missing:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Missing required overrides for role '{role}' "
                        f"(repr template '{repr_template_name}'): {missing}",
                    )

                # Merge defaults + overrides (overrides win)
                merged = {**repr_template.default_values, **overrides}
            else:
                # Template doesn't exist yet (lazy tolerance)
                merged = overrides

            representations[node_name] = merged

        # Determine resource template
        resource_template_name = loc_template.resource_template_name
        resource_template_overrides = loc_template.resource_template_overrides or {}
        if request.resource_template_overrides:
            resource_template_overrides = {
                **resource_template_overrides,
                **request.resource_template_overrides,
            }

        # Determine allow_transfers
        allow_transfers = (
            request.allow_transfers
            if request.allow_transfers is not None
            else loc_template.default_allow_transfers
        )

        # Create the location
        location = Location(
            location_name=request.location_name,
            description=request.description,
            representations=representations,
            resource_template_name=resource_template_name,
            resource_template_overrides=resource_template_overrides or None,
            allow_transfers=allow_transfers,
            location_template_name=request.template_name,
            node_bindings=request.node_bindings,
        )

        # Attempt resource creation (lazy: set to None if template doesn't exist yet)
        try:
            location.resource_id = self._initialize_location_resource(location)
        except Exception:
            location.resource_id = None
            self.logger.info(
                "Resource template not available yet, will reconcile later",
                resource_template_name=resource_template_name,
                location_name=request.location_name,
            )

        # Store the location
        result = self.state_handler.add_location(location)
        if result is None:
            raise HTTPException(
                status_code=409,
                detail=f"Location '{request.location_name}' already exists",
            )

        # Rebuild transfer graph
        self.transfer_planner.rebuild_transfer_graph()

        return result

    @post("/reconcile", tags=["Reconciliation"])
    def trigger_reconcile(self) -> dict[str, Any]:
        """Manually trigger reconciliation of unresolved template references."""
        return self._reconcile()

    def _reconcile(self) -> dict[str, Any]:
        """Reconcile unresolved locations.

        - Resolves null resource_ids when resource templates become available.
        - Fills in missing representation data when repr templates arrive.

        Returns a summary of what was reconciled.
        """
        results: dict[str, Any] = {
            "resources_resolved": 0,
            "representations_updated": 0,
        }

        for location in self.state_handler.get_locations():
            results["resources_resolved"] += self._reconcile_resource(location)
            results["representations_updated"] += self._reconcile_representations(
                location
            )

        if results["resources_resolved"] > 0 or results["representations_updated"] > 0:
            self.logger.info("Reconciliation completed", **results)

        return results

    def _reconcile_resource(self, location: Location) -> int:
        """Attempt to resolve a null resource_id for a location. Returns 1 if resolved, 0 otherwise."""
        if not location.resource_template_name or location.resource_id is not None:
            return 0
        try:
            resource_id = self._initialize_location_resource(location)
            if resource_id is not None:
                location.resource_id = resource_id
                self.state_handler.update_location(location)
                return 1
        except Exception:
            self.logger.debug(
                "Resource template still not available",
                resource_template_name=location.resource_template_name,
                location_name=location.location_name,
            )
        return 0

    def _merge_template_representations(
        self, location: Location, loc_template: LocationTemplate
    ) -> bool:
        """Merge representation template defaults into a location's representations.

        For each role in the location template, looks up the representation template
        and merges its default values with the location's existing representation data.
        Existing user data is preserved (defaults only fill in missing keys).

        Returns True if any representations were updated, False otherwise.
        """
        if location.node_bindings is None:
            return False

        updated = False
        for role, repr_template_name in loc_template.representation_templates.items():
            node_name = location.node_bindings.get(role)
            if node_name is None:
                continue

            repr_template = self.state_handler.get_representation_template(
                repr_template_name
            )
            if repr_template is None:
                continue

            current_repr = location.representations.get(node_name, {})
            merged = {**repr_template.default_values, **current_repr}
            if merged != current_repr:
                location.representations[node_name] = merged
                updated = True

        return updated

    def _reconcile_representations(self, location: Location) -> int:
        """Fill in missing representation defaults from templates. Returns 1 if updated, 0 otherwise."""
        if not location.location_template_name or not location.node_bindings:
            return 0

        loc_template = self.state_handler.get_location_template(
            location.location_template_name
        )
        if loc_template is None:
            return 0

        if self._merge_template_representations(location, loc_template):
            try:
                self.state_handler.update_location(location)
                return 1
            except Exception:
                self.logger.warning(
                    "Failed to reconcile location representations",
                    location_name=location.location_name,
                    exc_info=True,
                )
        return 0

    def _reconcile_for_repr_template(self, template_name: str) -> None:
        """Trigger reconciliation for locations that reference a specific repr template.

        This is a lightweight event-driven reconciliation triggered when a repr template
        is registered or updated.
        """
        # Find locations created from templates that reference this repr template
        for loc_template in self.state_handler.get_location_templates():
            if template_name in loc_template.representation_templates.values():
                self._reconcile_locations_for_template(loc_template)

    def _reconcile_locations_for_template(self, loc_template: LocationTemplate) -> None:
        """Re-merge representations for locations created from a specific template."""
        locations = self.state_handler.get_locations()
        for location in locations:
            if location.location_template_name != loc_template.template_name:
                continue

            if self._merge_template_representations(location, loc_template):
                try:
                    self.state_handler.update_location(location)
                except Exception:
                    self.logger.warning(
                        "Failed to reconcile location",
                        location_name=location.location_name,
                        exc_info=True,
                    )

    @post("/transfer/plan", tags=["Transfer"])
    def plan_transfer(
        self,
        source_location_id: str,
        target_location_id: str,
    ) -> WorkflowDefinition:
        """
        Plan a transfer workflow from source to target.

        Args:
            source_location: Source location ID
            target_location: Target location ID

        Returns:
            Composite workflow definition to execute the transfer

        Raises:
            HTTPException: If no transfer path exists
        """
        with self.span(
            "transfer.plan",
            attributes={
                "transfer.source_location": source_location_id,
                "transfer.target_location": target_location_id,
            },
        ):
            try:
                return self.transfer_planner.plan_transfer(
                    source_location_id, target_location_id
                )
            except ValueError as e:
                error_message = str(e)
                # Check if this is a "does not allow transfers" error
                if "does not allow transfers" in error_message:
                    raise HTTPException(
                        status_code=400,
                        detail=error_message,
                    ) from e
                # Check if this is a "not found" or "no transfer path" error
                if (
                    "not found" in error_message
                    or "No transfer path exists" in error_message
                ):
                    raise HTTPException(
                        status_code=404,
                        detail=error_message,
                    ) from e
                # Default to 400 for other ValueError cases
                raise HTTPException(
                    status_code=400,
                    detail=error_message,
                ) from e

    @get("/transfer/graph", tags=["Transfer"])
    def get_transfer_graph(self) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs
        """
        return self.transfer_planner.get_transfer_graph_adjacency_list()

    @get("/location/{location_name}/resources", tags=["Resources"])
    def get_location_resources(self, location_name: str) -> Optional[ResourceHierarchy]:
        """
        Get the resource hierarchy for resources currently at a specific location.

        Args:
            location_name: Location name to query

        Returns:
            ResourceHierarchy: Hierarchy of resources at the location, or empty hierarchy if no attached resource

        Raises:
            HTTPException: If location not found
        """
        location = self.state_handler.get_location(location_name)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_name} not found"
            )

        # If no resource is attached to this location, return empty hierarchy
        if not location.resource_id:
            return ResourceHierarchy(ancestor_ids=[], resource_id="", descendant_ids={})

        try:
            # Query the resource hierarchy for the attached resource
            return self.resource_client.query_resource_hierarchy(location.resource_id)
        except Exception:
            self.logger.warning(
                "Failed to query resource hierarchy for location",
                location_name=location_name,
                resource_id=location.resource_id,
                exc_info=True,
            )
            # Return empty hierarchy if query fails
            return ResourceHierarchy(
                ancestor_ids=[],
                resource_id=location.resource_id or "",
                descendant_ids={},
            )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the application lifespan with background reconciliation."""
    manager = getattr(app.state, "manager", None)
    task = None

    if manager and getattr(manager.settings, "reconciliation_enabled", False):

        async def reconciliation_loop() -> None:
            interval = manager.settings.reconciliation_interval_seconds
            while True:
                await asyncio.sleep(interval)
                try:
                    manager._reconcile()
                except Exception:
                    manager.logger.warning(
                        "Background reconciliation failed",
                        exc_info=True,
                    )

        task = asyncio.create_task(reconciliation_loop())

    yield

    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app(
    settings: Optional[LocationManagerSettings] = None,
    document_handler: Optional[DocumentStorageHandler] = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    manager = LocationManager(settings=settings, document_handler=document_handler)
    app = manager.create_server(
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.manager = manager
    return app


if __name__ == "__main__":
    manager = LocationManager()
    manager.run_server()
