"""Tests for seed file format loading (old list format and new dict format)."""

import pytest
import yaml
from fastapi.testclient import TestClient
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.db_handlers.redis_handler import InMemoryRedisHandler
from madsci.common.types.location_types import (
    LocationManagerSettings,
)
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_server import LocationManager


def _create_manager(settings, redis_handler, document_handler):
    """Create a LocationManager with test handlers."""
    return LocationManager(
        settings=settings,
        redis_handler=redis_handler,
        document_handler=document_handler,
    )


class TestOldFormatSeedFile:
    """Tests for old (list) seed file format."""

    def test_old_format_loads(self, tmp_path):
        """Old format (flat list of locations) loads correctly."""
        seed_file = tmp_path / "locations.yaml"
        seed_data = [
            {
                "location_name": "loc_a",
                "location_id": new_ulid_str(),
                "representations": {"node1": {"key": "val"}},
            },
            {
                "location_name": "loc_b",
                "location_id": new_ulid_str(),
                "representations": {},
            },
        ]
        with seed_file.open("w") as f:
            yaml.dump(seed_data, f)

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            seed_locations_file=str(seed_file),
            reconciliation_enabled=False,
        )
        mongo = InMemoryDocumentStorageHandler(database_name="test")
        redis = InMemoryRedisHandler()
        manager = _create_manager(settings, redis, mongo)
        app = manager.create_server(version="0.1.0")

        with TestClient(app) as client:
            response = client.get("/locations")
            assert response.status_code == 200
            locations = response.json()
            assert len(locations) == 2
            names = {loc["location_name"] for loc in locations}
            assert names == {"loc_a", "loc_b"}

        mongo.close()
        redis.close()


class TestNewFormatSeedFile:
    """Tests for new (dict) seed file format."""

    def test_new_format_loads_templates_and_locations(self, tmp_path):
        """New format loads repr templates, location templates, and template-based locations."""
        seed_file = tmp_path / "locations.yaml"
        seed_data = {
            "representation_templates": [
                {
                    "template_name": "arm_repr",
                    "default_values": {"gripper": "standard", "payload": 2.0},
                    "required_overrides": ["position"],
                },
            ],
            "location_templates": [
                {
                    "template_name": "arm_slot",
                    "representation_templates": {"arm": "arm_repr"},
                },
            ],
            "locations": [
                {
                    "location_name": "slot_1",
                    "template_name": "arm_slot",
                    "node_bindings": {"arm": "robotarm_1"},
                    "representation_overrides": {
                        "arm": {"position": [1, 2, 3]},
                    },
                },
            ],
        }
        with seed_file.open("w") as f:
            yaml.dump(seed_data, f)

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            seed_locations_file=str(seed_file),
            reconciliation_enabled=False,
        )
        mongo = InMemoryDocumentStorageHandler(database_name="test")
        redis = InMemoryRedisHandler()
        manager = _create_manager(settings, redis, mongo)
        app = manager.create_server(version="0.1.0")

        with TestClient(app) as client:
            # Check repr templates were loaded
            response = client.get("/representation_templates")
            assert response.status_code == 200
            templates = response.json()
            assert len(templates) == 1
            assert templates[0]["template_name"] == "arm_repr"

            # Check location templates were loaded
            response = client.get("/location_templates")
            assert response.status_code == 200
            templates = response.json()
            assert len(templates) == 1
            assert templates[0]["template_name"] == "arm_slot"

            # Check location was created with merged data
            response = client.get("/locations")
            assert response.status_code == 200
            locations = response.json()
            assert len(locations) == 1
            loc = locations[0]
            assert loc["location_name"] == "slot_1"
            assert loc["location_template_name"] == "arm_slot"
            repr_data = loc["representations"]["robotarm_1"]
            assert repr_data["gripper"] == "standard"
            assert repr_data["payload"] == 2.0
            assert repr_data["position"] == [1, 2, 3]

        mongo.close()
        redis.close()

    def test_new_format_with_inline_locations(self, tmp_path):
        """New format supports inline (old-style) locations alongside template-based ones."""
        seed_file = tmp_path / "locations.yaml"
        seed_data = {
            "locations": [
                {
                    "location_name": "inline_loc",
                    "representations": {"node1": {"key": "val"}},
                },
            ],
        }
        with seed_file.open("w") as f:
            yaml.dump(seed_data, f)

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            seed_locations_file=str(seed_file),
            reconciliation_enabled=False,
        )
        mongo = InMemoryDocumentStorageHandler(database_name="test")
        redis = InMemoryRedisHandler()
        manager = _create_manager(settings, redis, mongo)
        app = manager.create_server(version="0.1.0")

        with TestClient(app) as client:
            response = client.get("/locations")
            assert response.status_code == 200
            locations = response.json()
            assert len(locations) == 1
            assert locations[0]["location_name"] == "inline_loc"

        mongo.close()
        redis.close()


class TestExampleLocationsSeedFile:
    """Tests for the actual example_lab locations.yaml."""

    def test_example_locations_yaml_is_valid(self):
        """The example locations.yaml parses and has expected structure."""
        from pathlib import Path  # noqa: PLC0415

        seed_path = (
            Path(__file__).parent.parent.parent.parent
            / "examples"
            / "example_lab"
            / "locations.yaml"
        )
        if not seed_path.exists():
            pytest.skip("Example locations.yaml not found")

        with seed_path.open() as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict)
        assert "representation_templates" in data
        assert "location_templates" in data
        assert "locations" in data

        # Validate structure
        assert len(data["representation_templates"]) >= 3
        assert len(data["location_templates"]) >= 2
        assert len(data["locations"]) >= 10

        # Check that template-based locations have required fields
        for loc in data["locations"]:
            if "template_name" in loc:
                assert "node_bindings" in loc
                assert "location_name" in loc

    def test_example_locations_yaml_loads_successfully(self):
        """The example locations.yaml loads successfully into a test server."""
        from pathlib import Path  # noqa: PLC0415

        seed_path = (
            Path(__file__).parent.parent.parent.parent
            / "examples"
            / "example_lab"
            / "locations.yaml"
        )
        if not seed_path.exists():
            pytest.skip("Example locations.yaml not found")

        settings = LocationManagerSettings(
            enable_registry_resolution=False,
            seed_locations_file=str(seed_path),
            reconciliation_enabled=False,
        )
        mongo = InMemoryDocumentStorageHandler(database_name="test")
        redis = InMemoryRedisHandler()
        manager = _create_manager(settings, redis, mongo)
        app = manager.create_server(version="0.1.0")

        with TestClient(app) as client:
            # Templates should be loaded
            response = client.get("/representation_templates")
            assert response.status_code == 200
            assert len(response.json()) >= 3

            response = client.get("/location_templates")
            assert response.status_code == 200
            assert len(response.json()) >= 2

            # Locations should be loaded
            response = client.get("/locations")
            assert response.status_code == 200
            locations = response.json()
            assert len(locations) >= 10

            # Verify template-based locations have merged representations
            lh1_deck1 = next(
                (
                    loc
                    for loc in locations
                    if loc["location_name"] == "liquidhandler_1.deck_1"
                ),
                None,
            )
            assert lh1_deck1 is not None
            assert lh1_deck1["location_template_name"] == "lh_accessible_deck_slot"
            # Should have representations for both liquid handler and robot arm
            assert "liquidhandler_1" in lh1_deck1["representations"]
            assert "robotarm_1" in lh1_deck1["representations"]
            assert lh1_deck1["representations"]["liquidhandler_1"]["deck_position"] == 1
            assert lh1_deck1["representations"]["robotarm_1"]["position"] == [10, 15, 5]

            # Verify inline locations loaded correctly
            storage = next(
                (loc for loc in locations if loc["location_name"] == "storage_rack"),
                None,
            )
            assert storage is not None
            assert storage["location_template_name"] is None

        mongo.close()
        redis.close()
