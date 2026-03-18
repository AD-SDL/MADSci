"""One-time migration tool for Location Manager: 0.7.1 Redis → document database.

The 0.7.1 system stores locations in Redis indexed by location_id under key
``madsci:location_manager:{manager_id}:locations``. This tool reads from that
old format, maps fields to the current ``Location`` model, and writes to the document database.

Usage (CLI)::

    python -m madsci.location_manager.location_migration \
        --redis-host localhost --redis-port 6379 \
        --mongo-url mongodb://localhost:27017/ \
        --manager-id <MANAGER_ID>
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

from madsci.common.db_handlers import DocumentStorageHandler, RedisHandler
from madsci.common.types.location_types import Location

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Summary of a migration run."""

    migrated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class LocationMigrator:
    """Migrates locations from 0.7.1 Redis format to the document database."""

    def __init__(
        self,
        redis_handler: RedisHandler,
        document_handler: DocumentStorageHandler,
        manager_id: str,
        event_logger: Optional[Any] = None,
    ) -> None:
        """Initialize the migrator with cache/document database handlers and manager ID."""
        self._redis_handler = redis_handler
        self._document_handler = document_handler
        self._manager_id = manager_id
        self._event_logger = event_logger
        self._locations_collection = self._document_handler.get_collection("locations")

    def _log(self, msg: str, **kwargs: Any) -> None:
        if self._event_logger:
            self._event_logger.info(msg, **kwargs)

    def _log_warn(self, msg: str, **kwargs: Any) -> None:
        if self._event_logger:
            self._event_logger.warning(msg, **kwargs)

    def migrate_from_redis(self) -> MigrationResult:
        """Read old Redis data, transform, and write to the document database.

        The 0.7.1 format stores locations in a Redis dict at
        ``madsci:location_manager:{manager_id}:locations`` keyed by
        location name (or in some older deployments, location_id).
        """
        result = MigrationResult()
        old_key = f"madsci:location_manager:{self._manager_id}:locations"

        try:
            old_dict = self._redis_handler.create_dict(old_key)
            if not old_dict:
                self._log("No old Redis data found, nothing to migrate.")
                return result

            raw_data = old_dict.to_dict()
        except Exception as e:
            result.errors.append(f"Failed to read from Redis: {e}")
            return result

        for key, raw_loc in raw_data.items():
            try:
                normalized = self._normalize_reservation_fields(raw_loc)
                location = Location.model_validate(normalized)

                # Check for duplicate in document database
                existing = self._locations_collection.find_one(
                    {"location_name": location.location_name}
                )
                if existing is not None:
                    result.skipped += 1
                    continue

                self._locations_collection.insert_one(location.model_dump(mode="json"))
                result.migrated += 1
            except Exception as e:
                result.errors.append(f"Error migrating entry '{key}': {e}")

        self._log(
            "Redis migration complete",
            migrated=result.migrated,
            skipped=result.skipped,
            errors=len(result.errors),
        )
        return result

    def migrate_from_settings(self, locations: list[dict[str, Any]]) -> MigrationResult:
        """Import from old inline settings format (LocationDefinition list)."""
        result = MigrationResult()

        for raw_loc in locations:
            try:
                normalized = self._normalize_reservation_fields(raw_loc)
                location = Location.model_validate(normalized)

                existing = self._locations_collection.find_one(
                    {"location_name": location.location_name}
                )
                if existing is not None:
                    result.skipped += 1
                    continue

                self._locations_collection.insert_one(location.model_dump(mode="json"))
                result.migrated += 1
            except Exception as e:
                result.errors.append(f"Error migrating location: {e}")

        return result

    @staticmethod
    def _normalize_reservation_fields(
        loc_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle 0.7.1 reservation field mapping: start/end → created/expires."""
        reservation = loc_data.get("reservation")
        if isinstance(reservation, dict):
            if "start" in reservation and "created" not in reservation:
                reservation["created"] = reservation.pop("start")
            if "end" in reservation and "expires" not in reservation:
                reservation["expires"] = reservation.pop("end")
            loc_data["reservation"] = reservation
        return loc_data


class SchemaUpgrader:
    """Handles schema upgrades for the Location Manager document database."""

    def __init__(
        self,
        document_handler: DocumentStorageHandler,
        event_logger: Optional[Any] = None,
    ) -> None:
        """Initialize the schema upgrader."""
        self._document_handler = document_handler
        self._event_logger = event_logger

    def _log(self, msg: str, **kwargs: Any) -> None:
        if self._event_logger:
            self._event_logger.info(msg, **kwargs)

    def upgrade_1_to_2(self) -> MigrationResult:
        """Upgrade schema from 1.0.0 to 2.0.0.

        Additive only: creates new collections (representation_templates,
        location_templates) and their indexes. Existing locations data is
        not modified. Idempotent — safe to run multiple times.
        """
        result = MigrationResult()

        try:
            # Create representation_templates collection (idempotent)
            repr_coll = self._document_handler.get_collection(
                "representation_templates"
            )
            # Accessing the collection creates it; insert a marker if desired
            self._log(
                "Ensured representation_templates collection exists",
                collection="representation_templates",
            )

            # Create location_templates collection (idempotent)
            loc_coll = self._document_handler.get_collection("location_templates")
            self._log(
                "Ensured location_templates collection exists",
                collection="location_templates",
            )

            # Record migration version
            versions_coll = self._document_handler.get_collection("schema_versions")
            existing = versions_coll.find_one({"version": "2.0.0"})
            if existing is None:
                from datetime import datetime, timezone  # noqa: PLC0415

                versions_coll.insert_one(
                    {
                        "version": "2.0.0",
                        "applied_at": datetime.now(timezone.utc).isoformat(),
                        "description": "Added representation_templates and location_templates collections",
                    }
                )
                result.migrated = 1
                self._log("Schema upgraded to 2.0.0")
            else:
                result.skipped = 1
                self._log("Schema 2.0.0 already applied, skipping")

            # Touch collections to verify they work (idempotent read)
            _ = repr_coll.find().to_list()
            _ = loc_coll.find().to_list()

        except Exception as e:
            result.errors.append(f"Schema upgrade 1.0.0 → 2.0.0 failed: {e}")

        return result


def main() -> None:
    """CLI entry point for manual migration."""
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Migrate Location Manager data from 0.7.1 Redis to document database"
    )
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--redis-password", default=None)
    parser.add_argument("--mongo-url", default="mongodb://localhost:27017/")
    parser.add_argument("--database", default="madsci_locations")
    parser.add_argument("--manager-id", required=True)

    args = parser.parse_args()

    from madsci.common.db_handlers import (  # noqa: PLC0415
        PyDocumentStorageHandler,
        PyRedisHandler,
    )

    redis_handler = PyRedisHandler.from_settings(
        host=args.redis_host,
        port=args.redis_port,
        password=args.redis_password,
    )
    document_handler = PyDocumentStorageHandler.from_url(args.mongo_url, args.database)

    migrator = LocationMigrator(
        redis_handler=redis_handler,
        document_handler=document_handler,
        manager_id=args.manager_id,
    )

    result = migrator.migrate_from_redis()
    logger.info(
        "Migration complete: %d migrated, %d skipped",
        result.migrated,
        result.skipped,
    )
    if result.errors:
        logger.error("Errors (%d):", len(result.errors))
        for err in result.errors:
            logger.error("  - %s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()
