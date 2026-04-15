"""Tests for the 0.7.1 Redis → document database migration tool."""

from datetime import datetime, timedelta

import pytest
from madsci.common.db_handlers.cache_handler import InMemoryCacheHandler
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.types.location_types import Location
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_migration import LocationMigrator

MANAGER_ID = "test_manager_001"


@pytest.fixture
def document_handler():
    handler = InMemoryDocumentStorageHandler(database_name="test_migration")
    yield handler
    handler.close()


@pytest.fixture
def cache_handler():
    handler = InMemoryCacheHandler()
    yield handler
    handler.close()


@pytest.fixture
def migrator(cache_handler, document_handler):
    return LocationMigrator(
        cache_handler=cache_handler,
        document_handler=document_handler,
        manager_id=MANAGER_ID,
    )


def _seed_cache(cache_handler, locations_dict):
    """Seed old-format cache data: ID-indexed dict under the legacy key."""
    old_dict = cache_handler.create_dict(
        f"madsci:location_manager:{MANAGER_ID}:locations"
    )
    for key, val in locations_dict.items():
        old_dict[key] = val


class TestMigrateFromRedis:
    def test_migrate_empty_redis_no_error(self, migrator):
        """Empty Redis → no-op, no errors."""
        result = migrator.migrate_from_redis()
        assert result.migrated == 0
        assert result.skipped == 0
        assert result.errors == []

    def test_migrate_redis_locations_to_mongo(
        self, migrator, cache_handler, document_handler
    ):
        """Seed cache with 0.7.1 format, run migration, verify all in document database."""
        loc1_id = new_ulid_str()
        loc2_id = new_ulid_str()
        _seed_cache(
            cache_handler,
            {
                "station_a": {
                    "location_name": "station_a",
                    "location_id": loc1_id,
                    "description": "First",
                },
                "station_b": {
                    "location_name": "station_b",
                    "location_id": loc2_id,
                    "description": "Second",
                },
            },
        )

        result = migrator.migrate_from_redis()
        assert result.migrated == 2
        assert result.skipped == 0

        # Verify in document database
        collection = document_handler.get_collection("locations")
        docs = collection.find().to_list()
        assert len(docs) == 2
        names = {d["location_name"] for d in docs}
        assert names == {"station_a", "station_b"}

    def test_migrate_preserves_all_fields(
        self, migrator, cache_handler, document_handler
    ):
        """Verify representations, resource_id, allow_transfers are preserved."""
        loc_id = new_ulid_str()
        _seed_cache(
            cache_handler,
            {
                "full_location": {
                    "location_name": "full_location",
                    "location_id": loc_id,
                    "description": "Has everything",
                    "representations": {"robot1": {"x": 1, "y": 2}},
                    "resource_id": "res_001",
                    "allow_transfers": False,
                },
            },
        )

        result = migrator.migrate_from_redis()
        assert result.migrated == 1

        collection = document_handler.get_collection("locations")
        doc = collection.find_one({"location_name": "full_location"})
        loc = Location.model_validate(doc)
        assert loc.representations == {"robot1": {"x": 1, "y": 2}}
        assert loc.resource_id == "res_001"
        assert loc.allow_transfers is False

    def test_migrate_handles_reservation_field_mapping(
        self, migrator, cache_handler, document_handler
    ):
        """Reservation start/end → created/expires."""
        now = datetime.now()
        later = now + timedelta(hours=1)
        loc_id = new_ulid_str()
        user_id = new_ulid_str()
        _seed_cache(
            cache_handler,
            {
                "reserved_loc": {
                    "location_name": "reserved_loc",
                    "location_id": loc_id,
                    "reservation": {
                        "owned_by": {"user_id": user_id},
                        "start": now.isoformat(),
                        "end": later.isoformat(),
                    },
                },
            },
        )

        result = migrator.migrate_from_redis()
        assert result.migrated == 1

        collection = document_handler.get_collection("locations")
        doc = collection.find_one({"location_name": "reserved_loc"})
        loc = Location.model_validate(doc)
        assert loc.reservation is not None
        assert loc.reservation.created is not None
        assert loc.reservation.expires is not None

    def test_migrate_skips_duplicate_names(
        self, migrator, cache_handler, document_handler
    ):
        """If document database already has a location with the same name, skip it."""
        loc_id = new_ulid_str()
        # Pre-populate document database
        collection = document_handler.get_collection("locations")
        existing = Location(
            location_name="Existing",
            location_id=new_ulid_str(),
        )
        collection.insert_one(existing.model_dump(mode="json"))

        _seed_cache(
            cache_handler,
            {
                "Existing": {
                    "location_name": "Existing",
                    "location_id": loc_id,
                },
            },
        )

        result = migrator.migrate_from_redis()
        assert result.migrated == 0
        assert result.skipped == 1

    def test_migrate_idempotent(self, migrator, cache_handler, document_handler):
        """Running migration twice doesn't create duplicates."""
        _seed_cache(
            cache_handler,
            {
                "idem_loc": {
                    "location_name": "idem_loc",
                    "location_id": new_ulid_str(),
                },
            },
        )

        result1 = migrator.migrate_from_redis()
        assert result1.migrated == 1

        result2 = migrator.migrate_from_redis()
        assert result2.migrated == 0
        assert result2.skipped == 1

        collection = document_handler.get_collection("locations")
        assert len(collection.find().to_list()) == 1

    def test_migrate_returns_summary(self, migrator, cache_handler):
        """Verify counts in result."""
        _seed_cache(
            cache_handler,
            {
                "A": {
                    "location_name": "A",
                    "location_id": new_ulid_str(),
                },
                "B": {
                    "location_name": "B",
                    "location_id": new_ulid_str(),
                },
            },
        )

        result = migrator.migrate_from_redis()
        assert result.migrated == 2
        assert result.skipped == 0
        assert result.errors == []


class TestMigrateFromSettings:
    def test_migrate_from_settings_format(self, migrator, document_handler):
        """Test migrating inline LocationDefinition list."""
        settings_locations = [
            {
                "location_name": "settings_loc_a",
                "location_id": new_ulid_str(),
                "description": "From settings",
            },
            {
                "location_name": "settings_loc_b",
                "location_id": new_ulid_str(),
            },
        ]

        result = migrator.migrate_from_settings(settings_locations)
        assert result.migrated == 2
        assert result.skipped == 0

        collection = document_handler.get_collection("locations")
        docs = collection.find().to_list()
        assert len(docs) == 2


class TestNormalizeReservationFields:
    def test_no_reservation(self):
        """No reservation field → no change."""
        data = {"location_name": "test"}
        result = LocationMigrator._normalize_reservation_fields(data)
        assert "reservation" not in result or result.get("reservation") is None

    def test_already_normalized(self):
        """Already has created/expires → no change."""
        data = {
            "reservation": {
                "owned_by": {"user_id": "u1"},
                "created": "2024-01-01T00:00:00",
                "expires": "2024-01-01T01:00:00",
            }
        }
        result = LocationMigrator._normalize_reservation_fields(data)
        assert result["reservation"]["created"] == "2024-01-01T00:00:00"
        assert result["reservation"]["expires"] == "2024-01-01T01:00:00"

    def test_start_end_mapped(self):
        """start/end → created/expires."""
        data = {
            "reservation": {
                "owned_by": {"user_id": "u1"},
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-01T01:00:00",
            }
        }
        result = LocationMigrator._normalize_reservation_fields(data)
        assert result["reservation"]["created"] == "2024-01-01T00:00:00"
        assert result["reservation"]["expires"] == "2024-01-01T01:00:00"
        assert "start" not in result["reservation"]
        assert "end" not in result["reservation"]
