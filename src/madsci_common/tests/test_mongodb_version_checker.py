"""Pytest unit tests for the DocumentDBVersionChecker with schema versioning."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.document_db_version_checker import (
    DocumentDBVersionChecker,
    ensure_schema_indexes,
)
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
            "test_collection": {
                "description": "Test collection",
                "indexes": [
                    {
                        "keys": [["name", 1]],
                        "name": "name_unique",
                        "unique": True,
                    },
                    {
                        "keys": [["created_at", -1]],
                        "name": "created_at_desc",
                    },
                ],
            },
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
    with patch("madsci.common.document_db_version_checker.MongoClient") as mock_client:
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
        mock_db.create_collection = Mock(return_value=mock_collection)
        mock_collection.list_indexes.return_value = []

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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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

        checker = DocumentDBVersionChecker(
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
        with patch(
            "madsci.common.document_db_version_checker.MongoClient"
        ) as mock_client:
            mock_db = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Database exists but no schema_versions collection
            mock_db.list_collection_names.return_value = ["test_collection"]

            checker = DocumentDBVersionChecker(
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
        with patch(
            "madsci.common.document_db_version_checker.MongoClient"
        ) as mock_client:
            mock_db = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Database doesn't exist (no collections)
            mock_db.list_collection_names.return_value = []

            checker = DocumentDBVersionChecker(
                "mongodb://localhost:27017", "test_db", temp_schema_file
            )

            needs_migration, expected_schema_version, db_version = (
                checker.is_migration_needed()
            )

            assert needs_migration is True
            assert expected_schema_version == SemanticVersion.parse("1.0.0")
            assert db_version is None


class TestEnsureSchemaIndexes:
    """Tests for the ensure_schema_indexes free function."""

    def test_creates_missing_indexes(self, temp_schema_file):
        """Test that ensure_schema_indexes creates indexes defined in schema."""
        handler = InMemoryDocumentStorageHandler()

        ensure_schema_indexes(handler, Path(temp_schema_file))

        # Check test_collection indexes
        test_coll = handler.get_collection("test_collection")
        idx_info = test_coll.index_information()
        assert "name_unique" in idx_info
        assert idx_info["name_unique"]["unique"] is True
        assert "created_at_desc" in idx_info

        # Check schema_versions indexes
        sv_coll = handler.get_collection("schema_versions")
        sv_info = sv_coll.index_information()
        assert "version_unique" in sv_info

    def test_skips_existing_indexes(self, temp_schema_file):
        """Test that existing indexes are not recreated."""
        handler = InMemoryDocumentStorageHandler()

        # Pre-create one of the indexes
        coll = handler.get_collection("test_collection")
        coll.create_index([("name", 1)], name="name_unique", unique=True)

        # Run ensure_schema_indexes — should not error
        ensure_schema_indexes(handler, Path(temp_schema_file))

        idx_info = coll.index_information()
        assert "name_unique" in idx_info
        assert "created_at_desc" in idx_info

    def test_creates_missing_collections(self, temp_schema_file):
        """Test that collections are auto-created."""
        handler = InMemoryDocumentStorageHandler()

        # No collections exist yet
        assert handler.list_collection_names() == []

        ensure_schema_indexes(handler, Path(temp_schema_file))

        # Collections should now exist
        names = handler.list_collection_names()
        assert "test_collection" in names
        assert "schema_versions" in names

    def test_handles_missing_schema_file(self, tmp_path):
        """Test that missing schema file is handled gracefully (no exception)."""
        handler = InMemoryDocumentStorageHandler()
        missing_path = tmp_path / "nonexistent_schema.json"

        # Should not raise
        ensure_schema_indexes(handler, missing_path)

    def test_handles_invalid_schema_file(self, tmp_path):
        """Test that invalid schema file is handled gracefully."""
        handler = InMemoryDocumentStorageHandler()
        bad_schema = tmp_path / "bad_schema.json"
        bad_schema.write_text('{"schema_version": "1.0.0"}')

        # Should not raise — missing database/collections keys
        ensure_schema_indexes(handler, bad_schema)

    def test_idempotent_multiple_calls(self, temp_schema_file):
        """Test that calling ensure_schema_indexes multiple times is safe."""
        handler = InMemoryDocumentStorageHandler()

        ensure_schema_indexes(handler, Path(temp_schema_file))
        ensure_schema_indexes(handler, Path(temp_schema_file))

        coll = handler.get_collection("test_collection")
        idx_info = coll.index_information()
        assert "name_unique" in idx_info
        assert "created_at_desc" in idx_info

    def test_validate_or_fail_fresh_db_creates_indexes(self, temp_schema_file):
        """Test that validate_or_fail on a fresh DB auto-creates schema indexes."""
        with patch(
            "madsci.common.document_db_version_checker.MongoClient"
        ) as mock_client:
            # Use an in-memory handler to verify indexes get created
            in_mem_handler = InMemoryDocumentStorageHandler()

            mock_db = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Fresh database: no collections initially, then some after creation
            call_count = [0]
            original_list = in_mem_handler.list_collection_names

            def list_collection_names_side_effect():
                call_count[0] += 1
                if call_count[0] <= 2:
                    # First two calls (is_migration_needed + validate_or_fail check)
                    return []
                # After schema_versions created
                return original_list()

            mock_db.list_collection_names.side_effect = (
                list_collection_names_side_effect
            )

            # schema_versions collection operations
            mock_schema_versions = Mock()
            mock_schema_versions.list_indexes.return_value = []

            def getitem_side_effect(_name):
                return mock_schema_versions

            mock_db.__getitem__ = Mock(side_effect=getitem_side_effect)
            mock_client_instance.list_database_names = Mock(return_value=[])

            checker = DocumentDBVersionChecker(
                "mongodb://localhost:27017",
                "test_db",
                temp_schema_file,
            )

            # Patch ensure_schema_indexes on the instance to verify it's called
            with patch(
                "madsci.common.document_db_version_checker.DocumentDBVersionChecker.ensure_schema_indexes"
            ) as mock_ensure:
                checker.validate_or_fail()
                mock_ensure.assert_called_once()

    def test_validate_or_fail_untracked_db_auto_initializes(self, temp_schema_file):
        """Test that validate_or_fail auto-initializes when collections exist but no schema_versions.

        This covers the case where a database has data collections (e.g. from a
        prior run or created by _setup_database) but no schema_versions collection,
        resulting in version 0.0.0.  The version checker should auto-initialize
        rather than raising RuntimeError.
        """
        with patch(
            "madsci.common.document_db_version_checker.MongoClient"
        ) as mock_client:
            mock_db = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Database has a data collection but no schema_versions
            mock_db.list_collection_names.return_value = ["events"]

            # schema_versions collection operations
            mock_schema_versions = Mock()
            mock_schema_versions.list_indexes.return_value = []
            # No existing version record — record_version will use insert_one path
            mock_schema_versions.find_one.return_value = None

            def getitem_side_effect(_name):
                return mock_schema_versions

            mock_db.__getitem__ = Mock(side_effect=getitem_side_effect)
            mock_client_instance.list_database_names = Mock(return_value=[])

            checker = DocumentDBVersionChecker(
                "mongodb://localhost:27017",
                "test_db",
                temp_schema_file,
            )

            # Should NOT raise — should auto-initialize
            with patch(
                "madsci.common.document_db_version_checker.DocumentDBVersionChecker.ensure_schema_indexes"
            ) as mock_ensure:
                checker.validate_or_fail()
                mock_ensure.assert_called_once()

            # Verify schema_versions was created and version was recorded
            mock_schema_versions.insert_one.assert_called_once()
            inserted_doc = mock_schema_versions.insert_one.call_args[0][0]
            assert inserted_doc["version"] == "1.0.0"

    def test_validate_or_fail_version_mismatch_raises(self, temp_schema_file):
        """Test that validate_or_fail raises when version tracking exists but mismatches."""
        with patch(
            "madsci.common.document_db_version_checker.MongoClient"
        ) as mock_client:
            mock_db = Mock()
            mock_collection = Mock()
            mock_client_instance = Mock()
            mock_client_instance.__getitem__ = Mock(return_value=mock_db)
            mock_client.return_value = mock_client_instance

            # Database has schema_versions with a different version
            mock_db.list_collection_names.return_value = [
                "events",
                "schema_versions",
            ]
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_collection.find_one.return_value = {"version": "0.9.0"}

            checker = DocumentDBVersionChecker(
                "mongodb://localhost:27017",
                "test_db",
                temp_schema_file,
            )

            # Should raise because version tracking exists with a real mismatch
            with pytest.raises(RuntimeError, match="schema version mismatch"):
                checker.validate_or_fail()
