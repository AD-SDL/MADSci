"""Pytest unit tests for the MongoDBVersionChecker with schema versioning."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from pydantic_extra_types.semantic_version import SemanticVersion


@pytest.fixture
def temp_schema_file(tmp_path):
    """Create a temporary schema file for testing."""
    schema_file = tmp_path / "schema.json"
    schema_content = {
        "database": "test_db",
        "schema_version": "1.0.0",
        "description": "Test schema",
        "collections": {
            "test_collection": {"description": "Test collection", "indexes": []},
            "schema_versions": {
                "description": "Version tracking",
                "indexes": [
                    {
                        "keys": [["version", 1]],
                        "name": "version_unique",
                        "unique": True,
                    }
                ],
            },
        },
    }
    schema_file.write_text(json.dumps(schema_content))
    return str(schema_file)


@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client for testing."""
    with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
        mock_db = Mock()
        mock_collection = Mock()

        mock_client_instance = Mock()
        mock_client_instance.__getitem__ = Mock(return_value=mock_db)
        mock_client.return_value = mock_client_instance

        mock_db.list_collection_names.return_value = [
            "test_collection",
            "schema_versions",
        ]
        mock_db.__getitem__ = Mock(return_value=mock_collection)

        yield mock_client, mock_db, mock_collection


class TestSchemaVersionComparison:
    """Test schema version comparison logic in is_migration_needed."""

    def test_migration_needed_for_patch_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that patch version differences DO trigger migration (schema versions must match exactly)."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, Schema expects 1.0.1
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        # Update temp schema file to have version 1.0.1
        schema_path = Path(temp_schema_file)
        schema_content = json.loads(schema_path.read_text())
        schema_content["schema_version"] = "1.0.1"
        schema_path.write_text(json.dumps(schema_content))

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("1.0.1")
        assert db_version == SemanticVersion.parse("1.0.0")

    def test_migration_needed_for_prerelease_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that pre-release version differences DO trigger migration (schema versions must match exactly)."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, Schema expects 1.0.0-rc1
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        # Update temp schema file to have version 1.0.0-rc1
        schema_path = Path(temp_schema_file)
        schema_content = json.loads(schema_path.read_text())
        schema_content["schema_version"] = "1.0.0-rc1"
        schema_path.write_text(json.dumps(schema_content))

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("1.0.0-rc1")
        assert db_version == SemanticVersion.parse("1.0.0")

    def test_migration_needed_for_minor_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that minor version differences trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, Schema expects 1.1.0
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        # Update temp schema file to have version 1.1.0
        schema_path = Path(temp_schema_file)
        schema_content = json.loads(schema_path.read_text())
        schema_content["schema_version"] = "1.1.0"
        schema_path.write_text(json.dumps(schema_content))

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("1.1.0")
        assert db_version == SemanticVersion.parse("1.0.0")

    def test_migration_needed_for_major_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that major version differences trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, Schema expects 2.0.0
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        # Update temp schema file to have version 2.0.0
        schema_path = Path(temp_schema_file)
        schema_content = json.loads(schema_path.read_text())
        schema_content["schema_version"] = "2.0.0"
        schema_path.write_text(json.dumps(schema_content))

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("2.0.0")
        assert db_version == SemanticVersion.parse("1.0.0")

    def test_no_migration_for_exact_version_match(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that exact version matches don't trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database and Schema both have 1.0.0
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        assert needs_migration is False
        assert expected_schema_version == SemanticVersion.parse("1.0.0")
        assert db_version == SemanticVersion.parse("1.0.0")

    def test_migration_needed_when_db_version_newer(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that migration is needed when DB version is newer than expected schema version."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.2, Schema expects 1.0.1
        mock_collection.find_one.return_value = {"version": "1.0.2"}

        # Update temp schema file to have version 1.0.1
        schema_path = Path(temp_schema_file)
        schema_content = json.loads(schema_path.read_text())
        schema_content["schema_version"] = "1.0.1"
        schema_path.write_text(json.dumps(schema_content))

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("1.0.1")
        assert db_version == SemanticVersion.parse("1.0.2")

    def test_fallback_for_invalid_db_versions(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test behavior when database has invalid semantic version."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has invalid semantic version
        mock_collection.find_one.return_value = {"version": "invalid-version"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        # Should trigger migration due to version comparison failure (returns None on error)
        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("1.0.0")
        assert db_version is None

    def test_complex_prerelease_versions(self, mock_mongo_client, temp_schema_file):
        """Test complex pre-release version handling."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0-alpha.1, Schema expects 1.0.0-beta.2
        mock_collection.find_one.return_value = {"version": "1.0.0-alpha.1"}

        # Update temp schema file to have version 1.0.0-beta.2
        schema_path = Path(temp_schema_file)
        schema_content = json.loads(schema_path.read_text())
        schema_content["schema_version"] = "1.0.0-beta.2"
        schema_path.write_text(json.dumps(schema_content))

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        needs_migration, expected_schema_version, db_version = (
            checker.is_migration_needed()
        )

        # Pre-release differences should trigger migration (exact match required)
        assert needs_migration is True
        assert expected_schema_version == SemanticVersion.parse("1.0.0-beta.2")
        assert db_version == SemanticVersion.parse("1.0.0-alpha.1")


class TestExistingFunctionality:
    """Test that existing functionality still works."""

    def test_migration_needed_for_no_version_tracking(self, temp_schema_file):
        """Test that databases without version tracking trigger migration."""
        with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
            mock_db = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Database exists but no schema_versions collection
            mock_db.list_collection_names.return_value = ["test_collection"]

            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "test_db", temp_schema_file
            )

            needs_migration, expected_schema_version, db_version = (
                checker.is_migration_needed()
            )

            assert needs_migration is True
            assert expected_schema_version == SemanticVersion.parse("1.0.0")
            assert db_version == SemanticVersion(0, 0, 0)

    def test_migration_needed_for_nonexistent_database(self, temp_schema_file):
        """Test that non-existent databases trigger migration."""
        with patch("madsci.common.mongodb_version_checker.MongoClient") as mock_client:
            mock_db = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Database doesn't exist (no collections)
            mock_db.list_collection_names.return_value = []

            checker = MongoDBVersionChecker(
                "mongodb://localhost:27017", "test_db", temp_schema_file
            )

            needs_migration, expected_schema_version, db_version = (
                checker.is_migration_needed()
            )

            assert needs_migration is True
            assert expected_schema_version == SemanticVersion.parse("1.0.0")
            assert db_version is None
