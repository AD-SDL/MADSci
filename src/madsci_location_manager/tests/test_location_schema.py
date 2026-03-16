"""Tests for location manager schema.json and schema migrations."""

import json
from pathlib import Path

from madsci.common.db_handlers.mongo_handler import InMemoryMongoHandler
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


def test_schema_version_is_2():
    """Schema version is 2.0.0."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert schema["schema_version"] == "2.0.0"


def test_schema_has_locations_collection():
    """Locations collection is defined with unique indexes."""
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)

    assert "locations" in schema["collections"]
    locations = schema["collections"]["locations"]
    assert "indexes" in locations
    assert len(locations["indexes"]) >= 2

    # Check for location_name unique index
    index_keys = [tuple(tuple(k) for k in idx["keys"]) for idx in locations["indexes"]]
    assert (("location_name", 1),) in index_keys
    assert (("location_id", 1),) in index_keys

    # Verify uniqueness constraints
    for idx in locations["indexes"]:
        assert idx.get("unique") is True


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


class TestSchemaUpgrader:
    """Tests for the 1.0.0 → 2.0.0 schema migration."""

    def test_upgrade_creates_version_record(self):
        """Upgrade records version 2.0.0 in schema_versions."""
        handler = InMemoryMongoHandler(database_name="test")
        upgrader = SchemaUpgrader(mongo_handler=handler)

        result = upgrader.upgrade_1_to_2()
        assert result.migrated == 1
        assert result.errors == []

        versions = handler.get_collection("schema_versions")
        record = versions.find_one({"version": "2.0.0"})
        assert record is not None
        handler.close()

    def test_upgrade_is_idempotent(self):
        """Running upgrade twice doesn't fail or duplicate."""
        handler = InMemoryMongoHandler(database_name="test")
        upgrader = SchemaUpgrader(mongo_handler=handler)

        result1 = upgrader.upgrade_1_to_2()
        assert result1.migrated == 1

        result2 = upgrader.upgrade_1_to_2()
        assert result2.skipped == 1
        assert result2.migrated == 0
        assert result2.errors == []
        handler.close()

    def test_upgrade_preserves_existing_locations(self):
        """Upgrade doesn't modify existing locations data."""
        handler = InMemoryMongoHandler(database_name="test")
        locations = handler.get_collection("locations")
        locations.insert_one(
            {"location_name": "test_loc", "location_id": "12345678901234567890123456"}
        )

        upgrader = SchemaUpgrader(mongo_handler=handler)
        result = upgrader.upgrade_1_to_2()
        assert result.errors == []

        # Verify location is unchanged
        loc = locations.find_one({"location_name": "test_loc"})
        assert loc is not None
        assert loc["location_id"] == "12345678901234567890123456"
        handler.close()

    def test_new_collections_are_accessible_after_upgrade(self):
        """New collections can be read/written after upgrade."""
        handler = InMemoryMongoHandler(database_name="test")
        upgrader = SchemaUpgrader(mongo_handler=handler)
        upgrader.upgrade_1_to_2()

        repr_coll = handler.get_collection("representation_templates")
        loc_coll = handler.get_collection("location_templates")

        # Can insert and read
        repr_coll.insert_one({"template_name": "test", "template_id": "abc"})
        assert repr_coll.find_one({"template_name": "test"}) is not None

        loc_coll.insert_one({"template_name": "test2", "template_id": "def"})
        assert loc_coll.find_one({"template_name": "test2"}) is not None
        handler.close()
