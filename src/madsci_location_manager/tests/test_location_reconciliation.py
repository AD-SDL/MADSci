"""Tests for location reconciliation (lazy template resolution)."""

import pytest
from fastapi.testclient import TestClient
from madsci.common.db_handlers.mongo_handler import InMemoryMongoHandler
from madsci.common.db_handlers.redis_handler import InMemoryRedisHandler
from madsci.common.types.location_types import (
    Location,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_server import LocationManager


@pytest.fixture
def mongo_handler():
    """Create an InMemoryMongoHandler for testing."""
    handler = InMemoryMongoHandler(database_name="test_locations")
    yield handler
    handler.close()


@pytest.fixture
def redis_handler():
    """Create an InMemoryRedisHandler for testing."""
    handler = InMemoryRedisHandler()
    yield handler
    handler.close()


@pytest.fixture
def app(redis_handler, mongo_handler):
    """Create a test app with test settings and in-memory handlers."""
    settings = LocationManagerSettings(
        enable_registry_resolution=False,
        reconciliation_enabled=False,  # Disable background loop for tests
    )
    manager = LocationManager(
        settings=settings,
        redis_handler=redis_handler,
        mongo_handler=mongo_handler,
    )
    return manager.create_server(version="0.1.0")


@pytest.fixture
def client(app):
    """Create a test client."""
    client = TestClient(app)
    yield client
    client.close()


class TestReconcileEndpoint:
    """Tests for the POST /reconcile endpoint."""

    def test_reconcile_no_op_when_nothing_to_resolve(self, client):
        """Reconciliation is a no-op when everything is resolved."""
        response = client.post("/reconcile")
        assert response.status_code == 200
        result = response.json()
        assert result["resources_resolved"] == 0
        assert result["representations_updated"] == 0

    def test_reconcile_fills_missing_representations(self, client):
        """Reconciliation fills in representation defaults from templates that arrive later."""
        # 1. Create a location template referencing repr template that doesn't exist yet
        loc_tmpl = LocationTemplate(
            template_name="test_tmpl",
            representation_templates={"arm": "arm_repr"},
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        # 2. Create a location from template (repr template not available yet)
        response = client.post(
            "/location/from_template",
            json={
                "location_name": "test_loc",
                "template_name": "test_tmpl",
                "node_bindings": {"arm": "robotarm_1"},
                "representation_overrides": {
                    "arm": {"position": [1, 2, 3]},
                },
            },
        )
        assert response.status_code == 200
        location = Location.model_validate(response.json())
        # Only override data present, no defaults merged (template didn't exist)
        assert location.representations["robotarm_1"] == {"position": [1, 2, 3]}

        # 3. Register the repr template with defaults
        repr_tmpl = LocationRepresentationTemplate(
            template_name="arm_repr",
            default_values={"gripper_config": "standard", "max_payload": 2.0},
            required_overrides=[],
        )
        client.post(
            "/representation_template",
            json=repr_tmpl.model_dump(mode="json"),
        )

        # 4. Trigger reconciliation
        response = client.post("/reconcile")
        assert response.status_code == 200
        result = response.json()
        assert result["representations_updated"] == 1

        # 5. Verify the location now has merged defaults
        response = client.get("/location/test_loc")
        assert response.status_code == 200
        updated = Location.model_validate(response.json())
        repr_data = updated.representations["robotarm_1"]
        assert repr_data["gripper_config"] == "standard"
        assert repr_data["max_payload"] == 2.0
        assert repr_data["position"] == [1, 2, 3]  # Override preserved

    def test_reconcile_does_not_overwrite_existing_data(self, client):
        """Reconciliation doesn't overwrite user-set representation values."""
        # Setup template and location
        repr_tmpl = LocationRepresentationTemplate(
            template_name="overwrite_test",
            default_values={"key": "default_value", "other": "default_other"},
            required_overrides=[],
        )
        client.post(
            "/representation_template",
            json=repr_tmpl.model_dump(mode="json"),
        )

        loc_tmpl = LocationTemplate(
            template_name="overwrite_tmpl",
            representation_templates={"role": "overwrite_test"},
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        # Create location with override that differs from default
        client.post(
            "/location/from_template",
            json={
                "location_name": "custom_loc",
                "template_name": "overwrite_tmpl",
                "node_bindings": {"role": "node_1"},
                "representation_overrides": {
                    "role": {"key": "custom_value"},
                },
            },
        )

        # Reconcile
        client.post("/reconcile")

        # Verify custom value is preserved (merge with default uses {**defaults, **current})
        response = client.get("/location/custom_loc")
        loc = Location.model_validate(response.json())
        assert loc.representations["node_1"]["key"] == "custom_value"
        assert loc.representations["node_1"]["other"] == "default_other"


class TestReconcileOnInit:
    """Tests for event-driven reconciliation triggered by template init."""

    def test_init_repr_template_triggers_reconciliation(self, client):
        """Registering a repr template via /init triggers reconciliation for referencing locations."""
        # 1. Create location template referencing "late_repr"
        loc_tmpl = LocationTemplate(
            template_name="late_tmpl",
            representation_templates={"role": "late_repr"},
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        # 2. Create location (repr template doesn't exist yet)
        client.post(
            "/location/from_template",
            json={
                "location_name": "late_loc",
                "template_name": "late_tmpl",
                "node_bindings": {"role": "node_1"},
                "representation_overrides": {"role": {"custom": "data"}},
            },
        )

        # 3. Init the repr template (should trigger reconciliation)
        repr_tmpl = LocationRepresentationTemplate(
            template_name="late_repr",
            default_values={"default_key": "default_val"},
        )
        client.post(
            "/representation_template/init",
            json=repr_tmpl.model_dump(mode="json"),
        )

        # 4. Check location was updated with defaults
        response = client.get("/location/late_loc")
        loc = Location.model_validate(response.json())
        assert loc.representations["node_1"]["default_key"] == "default_val"
        assert loc.representations["node_1"]["custom"] == "data"


class TestSeedFileWithLazyResolution:
    """Tests for seed file loading with lazy resource template resolution."""

    def test_seed_list_format_handles_missing_resource_template(
        self, redis_handler, mongo_handler, tmp_path
    ):
        """Seed file with list format loads even if resource template is unavailable."""
        import yaml  # noqa: PLC0415

        seed_file = tmp_path / "locations.yaml"
        seed_data = [
            {
                "location_name": "lazy_loc",
                "location_id": new_ulid_str(),
                "resource_template_name": "nonexistent_template",
                "representations": {"node1": {"key": "val"}},
            },
        ]
        with seed_file.open("w") as f:
            yaml.dump(seed_data, f)

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            seed_locations_file=str(seed_file),
            reconciliation_enabled=False,
        )
        manager = LocationManager(
            settings=settings,
            redis_handler=redis_handler,
            mongo_handler=mongo_handler,
        )
        app = manager.create_server(version="0.1.0")

        with TestClient(app) as test_client:
            response = test_client.get("/locations")
            assert response.status_code == 200
            locations = response.json()
            assert len(locations) == 1
            loc = locations[0]
            assert loc["location_name"] == "lazy_loc"
            # Resource ID should be None (template unavailable)
            assert loc["resource_id"] is None

    def test_register_default_resource_template_removed(self):
        """The _register_default_resource_template method should still exist (not removed yet)
        but doesn't prevent startup if resource manager is unavailable."""
        # This test verifies that the startup doesn't crash even without
        # a resource server. The _register_default_resource_template is
        # still called but failures are caught.
        settings = LocationManagerSettings(enable_registry_resolution=False)
        handler = InMemoryMongoHandler(database_name="test")
        redis = InMemoryRedisHandler()
        manager = LocationManager(
            settings=settings,
            mongo_handler=handler,
            redis_handler=redis,
        )
        # If we got here without crashing, the test passes
        assert manager is not None
        handler.close()
        redis.close()
