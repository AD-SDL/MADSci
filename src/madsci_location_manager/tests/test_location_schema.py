"""Tests for location manager schema.json."""

import json
from pathlib import Path

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
