"""Pytest unit tests for the MongoDBVersionChecker with semantic versioning."""

import json
from unittest.mock import Mock, patch

import pytest
from madsci.common.mongodb_version_checker import MongoDBVersionChecker


@pytest.fixture
def temp_schema_file(tmp_path):
    """Create a temporary schema file for testing."""
    schema_file = tmp_path / "schema.json"
    schema_content = {
        "database": "test_db",
        "version": "1.0.0",
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


class TestSemanticVersionComparison:
    """Test semantic version comparison logic in is_migration_needed."""

    def test_no_migration_needed_for_patch_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that patch version differences don't trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, MADSci has 1.0.1
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(checker, "get_current_madsci_version", return_value="1.0.1"):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        assert needs_migration is False
        assert madsci_version == "1.0.1"
        assert db_version == "1.0.0"

    def test_no_migration_needed_for_prerelease_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that pre-release version differences don't trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, MADSci has 1.0.0-rc1
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(
            checker, "get_current_madsci_version", return_value="1.0.0-rc1"
        ):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        assert needs_migration is False
        assert madsci_version == "1.0.0-rc1"
        assert db_version == "1.0.0"

    def test_migration_needed_for_minor_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that minor version differences trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, MADSci has 1.1.0
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(checker, "get_current_madsci_version", return_value="1.1.0"):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        assert needs_migration is True
        assert madsci_version == "1.1.0"
        assert db_version == "1.0.0"

    def test_migration_needed_for_major_version_difference(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that major version differences trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0, MADSci has 2.0.0
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(checker, "get_current_madsci_version", return_value="2.0.0"):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        assert needs_migration is True
        assert madsci_version == "2.0.0"
        assert db_version == "1.0.0"

    def test_no_migration_for_exact_version_match(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test that exact version matches don't trigger migration."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database and MADSci both have 1.0.0
        mock_collection.find_one.return_value = {"version": "1.0.0"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(checker, "get_current_madsci_version", return_value="1.0.0"):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        assert needs_migration is False
        assert madsci_version == "1.0.0"
        assert db_version == "1.0.0"

    def test_backward_compatibility_with_patch_versions(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test backward compatibility: newer DB patch version with older MADSci."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.2, MADSci has 1.0.1
        mock_collection.find_one.return_value = {"version": "1.0.2"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(checker, "get_current_madsci_version", return_value="1.0.1"):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        assert needs_migration is False
        assert madsci_version == "1.0.1"
        assert db_version == "1.0.2"

    def test_fallback_to_string_comparison_for_invalid_versions(
        self, mock_mongo_client, temp_schema_file
    ):
        """Test fallback to string comparison when semantic versioning fails."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has invalid semantic version
        mock_collection.find_one.return_value = {"version": "invalid-version"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(checker, "get_current_madsci_version", return_value="1.0.0"):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        # Should fall back to string comparison and trigger migration
        assert needs_migration is True
        assert madsci_version == "1.0.0"
        assert db_version == "invalid-version"

    def test_complex_prerelease_versions(self, mock_mongo_client, temp_schema_file):
        """Test complex pre-release version handling."""
        _mock_client, _mock_db, mock_collection = mock_mongo_client

        # Database has 1.0.0-alpha.1, MADSci has 1.0.0-beta.2
        mock_collection.find_one.return_value = {"version": "1.0.0-alpha.1"}

        checker = MongoDBVersionChecker(
            "mongodb://localhost:27017", "test_db", temp_schema_file
        )

        with patch.object(
            checker, "get_current_madsci_version", return_value="1.0.0-beta.2"
        ):
            needs_migration, madsci_version, db_version = checker.is_migration_needed()

        # Pre-release differences should not trigger migration
        assert needs_migration is False
        assert madsci_version == "1.0.0-beta.2"
        assert db_version == "1.0.0-alpha.1"


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

            needs_migration, _madsci_version, db_version = checker.is_migration_needed()

            assert needs_migration is True
            assert db_version == "NO_VERSION_TRACKING"

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

            needs_migration, _madsci_version, db_version = checker.is_migration_needed()

            assert needs_migration is True
            assert db_version is None
