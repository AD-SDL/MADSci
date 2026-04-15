"""Tests for location manager schema.json and schema migrations."""

import json
from pathlib import Path

from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.location_manager.location_migration import SchemaUpgrader

SCHEMA_PATH = (
    Path(__file__).parent.parent / "madsci" / "location_manager" / "schema.json"
)


def test_schema_json_exists():
    """Schema file exists at expected path."""
    assert SCHEMA_PATH.exists()


def test_schema_json_valid():
    """Parses as valid JSON with required structure."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert "database" in schema
    assert "schema_version" in schema
    assert "collections" in schema
    assert isinstance(schema["collections"], dict)


def test_schema_version_is_3():
    """Schema version is 3.0.0."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert schema["schema_version"] == "3.0.0"


def test_schema_has_locations_collection():
    """Locations collection is defined with required indexes."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert "locations" in schema["collections"]
    locations = schema["collections"]["locations"]
    assert "indexes" in locations
    assert len(locations["indexes"]) >= 3

    # Check for location_name unique index
    index_keys = [tuple(tuple(k) for k in idx["keys"]) for idx in locations["indexes"]]
    assert (("location_name", 1),) in index_keys
    assert (("location_id", 1),) in index_keys
    assert (("managed_by", 1),) in index_keys

    # Verify uniqueness constraints on the unique indexes
    unique_indexes = {
        idx["name"] for idx in locations["indexes"] if idx.get("unique") is True
    }
    assert "location_name_unique" in unique_indexes
    assert "location_id_unique" in unique_indexes

    # Verify managed_by index exists (non-unique)
    index_names = {idx["name"] for idx in locations["indexes"]}
    assert "managed_by_idx" in index_names


def test_schema_has_schema_versions_collection():
    """Schema versions collection exists with expected indexes."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert "schema_versions" in schema["collections"]
    sv = schema["collections"]["schema_versions"]
    assert "indexes" in sv
    assert len(sv["indexes"]) >= 2


def test_schema_has_representation_templates_collection():
    """Representation templates collection is defined with unique indexes."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert "representation_templates" in schema["collections"]
    coll = schema["collections"]["representation_templates"]
    assert "indexes" in coll
    assert len(coll["indexes"]) >= 2

    index_names = {idx["name"] for idx in coll["indexes"]}
    assert "repr_template_name_unique" in index_names
    assert "repr_template_id_unique" in index_names

    for idx in coll["indexes"]:
        assert idx.get("unique") is True


def test_schema_has_location_templates_collection():
    """Location templates collection is defined with unique indexes."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert "location_templates" in schema["collections"]
    coll = schema["collections"]["location_templates"]
    assert "indexes" in coll
    assert len(coll["indexes"]) >= 2

    index_names = {idx["name"] for idx in coll["indexes"]}
    assert "loc_template_name_unique" in index_names
    assert "loc_template_id_unique" in index_names

    for idx in coll["indexes"]:
        assert idx.get("unique") is True


class TestSchemaUpgrader1to2:
    """Tests for the 1.0.0 → 2.0.0 schema migration."""

    def test_upgrade_creates_version_record(self):
        """Upgrade records version 2.0.0 in schema_versions."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        upgrader = SchemaUpgrader(document_handler=handler)

        result = upgrader.upgrade_1_to_2()
        assert result.migrated == 1
        assert result.errors == []

        versions = handler.get_collection("schema_versions")
        record = versions.find_one({"version": "2.0.0"})
        assert record is not None
        handler.close()

    def test_upgrade_is_idempotent(self):
        """Running upgrade twice doesn't fail or duplicate."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        upgrader = SchemaUpgrader(document_handler=handler)

        result1 = upgrader.upgrade_1_to_2()
        assert result1.migrated == 1

        result2 = upgrader.upgrade_1_to_2()
        assert result2.skipped == 1
        assert result2.migrated == 0
        assert result2.errors == []
        handler.close()

    def test_upgrade_preserves_existing_locations(self):
        """Upgrade doesn't modify existing locations data."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        locations = handler.get_collection("locations")
        locations.insert_one(
            {"location_name": "test_loc", "location_id": "12345678901234567890123456"}
        )

        upgrader = SchemaUpgrader(document_handler=handler)
        result = upgrader.upgrade_1_to_2()
        assert result.errors == []

        # Verify location is unchanged
        loc = locations.find_one({"location_name": "test_loc"})
        assert loc is not None
        assert loc["location_id"] == "12345678901234567890123456"
        handler.close()

    def test_new_collections_are_accessible_after_upgrade(self):
        """New collections can be read/written after upgrade."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        upgrader = SchemaUpgrader(document_handler=handler)
        upgrader.upgrade_1_to_2()

        repr_coll = handler.get_collection("representation_templates")
        loc_coll = handler.get_collection("location_templates")

        # Can insert and read
        repr_coll.insert_one({"template_name": "test", "template_id": "abc"})
        assert repr_coll.find_one({"template_name": "test"}) is not None

        loc_coll.insert_one({"template_name": "test2", "template_id": "def"})
        assert loc_coll.find_one({"template_name": "test2"}) is not None
        handler.close()


class TestSchemaUpgrader2to3:
    """Tests for the 2.0.0 → 3.0.0 schema migration."""

    def test_upgrade_adds_managed_by_and_owner_to_existing_docs(self):
        """Upgrade adds managed_by='lab' and owner=None to documents missing managed_by."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        locations = handler.get_collection("locations")
        locations.insert_one(
            {"location_name": "old_loc", "location_id": "AAAAAAAAAAAAAAAAAAAAAAAAAA"}
        )
        locations.insert_one(
            {"location_name": "old_loc_2", "location_id": "BBBBBBBBBBBBBBBBBBBBBBBBBB"}
        )

        upgrader = SchemaUpgrader(document_handler=handler)
        result = upgrader.upgrade_2_to_3()
        assert result.errors == []
        assert result.migrated == 2

        # Verify both documents now have managed_by and owner
        loc1 = locations.find_one({"location_name": "old_loc"})
        assert loc1["managed_by"] == "lab"
        assert loc1["owner"] is None

        loc2 = locations.find_one({"location_name": "old_loc_2"})
        assert loc2["managed_by"] == "lab"
        assert loc2["owner"] is None

        # Verify version record
        versions = handler.get_collection("schema_versions")
        record = versions.find_one({"version": "3.0.0"})
        assert record is not None
        handler.close()

    def test_upgrade_is_idempotent(self):
        """Running upgrade_2_to_3 twice doesn't fail or duplicate."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        locations = handler.get_collection("locations")
        locations.insert_one(
            {
                "location_name": "idempotent_loc",
                "location_id": "CCCCCCCCCCCCCCCCCCCCCCCCCC",
            }
        )

        upgrader = SchemaUpgrader(document_handler=handler)
        result1 = upgrader.upgrade_2_to_3()
        assert result1.migrated == 1
        assert result1.errors == []

        result2 = upgrader.upgrade_2_to_3()
        # Second run: no docs missing managed_by, so migrated=0
        assert result2.migrated == 0
        assert result2.errors == []

        # Version record should still exist (not duplicated)
        versions = handler.get_collection("schema_versions")
        all_versions = versions.find({"version": "3.0.0"}).to_list()
        assert len(all_versions) == 1
        handler.close()

    def test_upgrade_does_not_modify_docs_with_managed_by(self):
        """Documents that already have managed_by are not modified."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        locations = handler.get_collection("locations")
        locations.insert_one(
            {
                "location_name": "node_loc",
                "location_id": "DDDDDDDDDDDDDDDDDDDDDDDDDD",
                "managed_by": "node",
                "owner": {"node_name": "arm_1"},
            }
        )
        locations.insert_one(
            {
                "location_name": "legacy_loc",
                "location_id": "EEEEEEEEEEEEEEEEEEEEEEEEEE",
            }
        )

        upgrader = SchemaUpgrader(document_handler=handler)
        result = upgrader.upgrade_2_to_3()
        assert result.errors == []
        # Only the legacy doc should be migrated
        assert result.migrated == 1

        # Node-managed location unchanged
        node_loc = locations.find_one({"location_name": "node_loc"})
        assert node_loc["managed_by"] == "node"
        assert node_loc["owner"] == {"node_name": "arm_1"}

        # Legacy location updated
        legacy_loc = locations.find_one({"location_name": "legacy_loc"})
        assert legacy_loc["managed_by"] == "lab"
        assert legacy_loc["owner"] is None
        handler.close()

    def test_upgrade_creates_version_record(self):
        """Upgrade records version 3.0.0 in schema_versions."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        upgrader = SchemaUpgrader(document_handler=handler)

        result = upgrader.upgrade_2_to_3()
        assert result.errors == []

        versions = handler.get_collection("schema_versions")
        record = versions.find_one({"version": "3.0.0"})
        assert record is not None
        assert "applied_at" in record
        assert record["description"] == "Added managed_by and owner fields to locations"
        handler.close()

    def test_upgrade_on_empty_database(self):
        """Upgrade on empty database doesn't error (0 docs to migrate)."""
        handler = InMemoryDocumentStorageHandler(database_name="test")
        upgrader = SchemaUpgrader(document_handler=handler)

        result = upgrader.upgrade_2_to_3()
        assert result.errors == []
        assert result.migrated == 0

        # Version record should still be created
        versions = handler.get_collection("schema_versions")
        record = versions.find_one({"version": "3.0.0"})
        assert record is not None
        handler.close()
