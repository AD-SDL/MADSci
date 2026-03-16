"""Tests for location_types.py — Phase 1 of MongoDB migration."""

from madsci.common.types.location_types import (
    Location,
    LocationImportResult,
    LocationManagerHealth,
    LocationManagerSettings,
)


class TestLocationManagerSettings:
    """Tests for the updated LocationManagerSettings."""

    def test_settings_has_document_db_fields(self):
        """Verify document_db_url and database_name exist with defaults."""
        settings = LocationManagerSettings(enable_registry_resolution=False)
        assert str(settings.document_db_url) == "mongodb://localhost:27017/"
        assert settings.database_name == "madsci_locations"

    def test_settings_has_seed_locations_file(self):
        """Verify seed_locations_file exists with default 'locations.yaml'."""
        settings = LocationManagerSettings(enable_registry_resolution=False)
        assert settings.seed_locations_file == "locations.yaml"

    def test_settings_seed_locations_file_backward_compat(self):
        """Verify locations_file_path alias works for backward compatibility."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            locations_file_path="custom.yaml",
        )
        assert settings.seed_locations_file == "custom.yaml"

    def test_settings_document_db_url_mongo_alias(self):
        """Verify mongo_db_url alias works for backward compatibility."""
        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            mongo_db_url="mongodb://custom:27017/",
        )
        assert str(settings.document_db_url) == "mongodb://custom:27017/"


class TestLocationManagerHealth:
    """Tests for the updated LocationManagerHealth."""

    def test_health_has_document_db_connected(self):
        """Verify document_db_connected field exists."""
        health = LocationManagerHealth()
        assert health.document_db_connected is None

    def test_health_has_redis_connected(self):
        """Verify redis_connected field still exists."""
        health = LocationManagerHealth()
        assert health.redis_connected is None

    def test_health_document_db_connected_set(self):
        """Verify document_db_connected can be set."""
        health = LocationManagerHealth(document_db_connected=True)
        assert health.document_db_connected is True


class TestLocationImportResult:
    """Tests for the new LocationImportResult model."""

    def test_import_result_model(self):
        """Verify LocationImportResult structure and defaults."""
        result = LocationImportResult()
        assert result.imported == 0
        assert result.skipped == 0
        assert result.errors == []
        assert result.locations == []

    def test_import_result_with_data(self):
        """Verify LocationImportResult with populated data."""
        loc = Location(location_name="test_loc")
        result = LocationImportResult(
            imported=1,
            skipped=2,
            errors=["error1"],
            locations=[loc],
        )
        assert result.imported == 1
        assert result.skipped == 2
        assert result.errors == ["error1"]
        assert len(result.locations) == 1
        assert result.locations[0].location_name == "test_loc"
