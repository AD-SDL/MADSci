"""Tests for location template server endpoints (representation templates, location templates, create-from-template)."""

import pytest
from fastapi.testclient import TestClient
from madsci.common.db_handlers.cache_handler import InMemoryCacheHandler
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.types.location_types import (
    Location,
    LocationManagerSettings,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_server import LocationManager


@pytest.fixture
def document_handler():
    """Create an InMemoryDocumentStorageHandler for testing."""
    handler = InMemoryDocumentStorageHandler(database_name="test_locations")
    yield handler
    handler.close()


@pytest.fixture
def cache_handler():
    """Create an InMemoryCacheHandler for testing."""
    handler = InMemoryCacheHandler()
    yield handler
    handler.close()


@pytest.fixture
def app(cache_handler, document_handler):
    """Create a test app with test settings and in-memory handlers."""
    settings = LocationManagerSettings(enable_registry_resolution=False)
    manager = LocationManager(
        settings=settings,
        cache_handler=cache_handler,
        document_handler=document_handler,
    )
    return manager.create_server(version="0.1.0")


@pytest.fixture
def client(app):
    """Create a test client."""
    client = TestClient(app)
    yield client
    client.close()


# --- Representation Template Tests ---


class TestRepresentationTemplateCRUD:
    """Tests for representation template CRUD endpoints."""

    def test_list_empty(self, client):
        """GET /representation_templates returns empty list initially."""
        response = client.get("/representation_templates")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_and_get(self, client):
        """POST then GET a representation template."""
        template = LocationRepresentationTemplate(
            template_name="robotarm_deck",
            default_values={"gripper_config": "standard", "max_payload": 2.0},
            required_overrides=["position"],
            tags=["robot"],
        )
        response = client.post(
            "/representation_template",
            json=template.model_dump(mode="json"),
        )
        assert response.status_code == 200
        created = LocationRepresentationTemplate.model_validate(response.json())
        assert created.template_name == "robotarm_deck"

        # Get by name
        response = client.get("/representation_template/robotarm_deck")
        assert response.status_code == 200
        fetched = LocationRepresentationTemplate.model_validate(response.json())
        assert fetched.template_id == created.template_id

    def test_create_duplicate_returns_409(self, client):
        """Creating duplicate template returns 409."""
        template = LocationRepresentationTemplate(template_name="dup_test")
        client.post(
            "/representation_template",
            json=template.model_dump(mode="json"),
        )
        response = client.post(
            "/representation_template",
            json=LocationRepresentationTemplate(template_name="dup_test").model_dump(
                mode="json"
            ),
        )
        assert response.status_code == 409

    def test_get_nonexistent_returns_404(self, client):
        """Getting nonexistent template returns 404."""
        response = client.get("/representation_template/nonexistent")
        assert response.status_code == 404

    def test_delete(self, client):
        """DELETE a representation template."""
        template = LocationRepresentationTemplate(template_name="to_delete")
        client.post(
            "/representation_template",
            json=template.model_dump(mode="json"),
        )
        response = client.delete("/representation_template/to_delete")
        assert response.status_code == 200

        response = client.get("/representation_template/to_delete")
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        """Deleting nonexistent template returns 404."""
        response = client.delete("/representation_template/nonexistent")
        assert response.status_code == 404

    def test_list_multiple(self, client):
        """GET /representation_templates returns all created templates."""
        for name in ["repr_a", "repr_b", "repr_c"]:
            client.post(
                "/representation_template",
                json=LocationRepresentationTemplate(template_name=name).model_dump(
                    mode="json"
                ),
            )
        response = client.get("/representation_templates")
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 3
        names = {t["template_name"] for t in templates}
        assert names == {"repr_a", "repr_b", "repr_c"}


class TestRepresentationTemplateInit:
    """Tests for the idempotent init endpoint."""

    def test_init_creates_new(self, client):
        """Init creates template if it doesn't exist."""
        template = LocationRepresentationTemplate(
            template_name="new_repr",
            default_values={"key": "value"},
            version="1.0.0",
        )
        response = client.post(
            "/representation_template/init",
            json=template.model_dump(mode="json"),
        )
        assert response.status_code == 200
        result = LocationRepresentationTemplate.model_validate(response.json())
        assert result.template_name == "new_repr"
        assert result.version == "1.0.0"

    def test_init_returns_existing_same_version(self, client):
        """Init returns existing template if same version."""
        template = LocationRepresentationTemplate(
            template_name="existing_repr",
            default_values={"key": "original"},
            version="1.0.0",
        )
        resp1 = client.post(
            "/representation_template/init",
            json=template.model_dump(mode="json"),
        )
        original_id = resp1.json()["template_id"]

        # Init again with same version but different defaults
        template2 = LocationRepresentationTemplate(
            template_name="existing_repr",
            default_values={"key": "changed"},
            version="1.0.0",
        )
        resp2 = client.post(
            "/representation_template/init",
            json=template2.model_dump(mode="json"),
        )
        assert resp2.status_code == 200
        result = resp2.json()
        # Should return original, not updated
        assert result["template_id"] == original_id
        assert result["default_values"]["key"] == "original"

    def test_init_updates_on_version_change(self, client):
        """Init updates template if version differs."""
        template_v1 = LocationRepresentationTemplate(
            template_name="versioned_repr",
            default_values={"key": "v1"},
            version="1.0.0",
        )
        resp1 = client.post(
            "/representation_template/init",
            json=template_v1.model_dump(mode="json"),
        )
        original_id = resp1.json()["template_id"]

        # Init with new version
        template_v2 = LocationRepresentationTemplate(
            template_name="versioned_repr",
            default_values={"key": "v2"},
            version="2.0.0",
        )
        resp2 = client.post(
            "/representation_template/init",
            json=template_v2.model_dump(mode="json"),
        )
        assert resp2.status_code == 200
        result = resp2.json()
        # Should update but keep original ID
        assert result["template_id"] == original_id
        assert result["default_values"]["key"] == "v2"
        assert result["version"] == "2.0.0"


# --- Location Template Tests ---


class TestLocationTemplateCRUD:
    """Tests for location template CRUD endpoints."""

    def test_list_empty(self, client):
        """GET /location_templates returns empty list initially."""
        response = client.get("/location_templates")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_and_get(self, client):
        """POST then GET a location template."""
        template = LocationTemplate(
            template_name="ot2_deck_slot",
            resource_template_name="location_container",
            representation_templates={
                "deck_controller": "lh_deck_repr",
                "transfer_arm": "robotarm_deck",
            },
        )
        response = client.post(
            "/location_template",
            json=template.model_dump(mode="json"),
        )
        assert response.status_code == 200
        created = LocationTemplate.model_validate(response.json())
        assert created.template_name == "ot2_deck_slot"

        response = client.get("/location_template/ot2_deck_slot")
        assert response.status_code == 200
        fetched = LocationTemplate.model_validate(response.json())
        assert fetched.template_id == created.template_id

    def test_create_duplicate_returns_409(self, client):
        """Creating duplicate template returns 409."""
        template = LocationTemplate(template_name="dup_loc_tmpl")
        client.post(
            "/location_template",
            json=template.model_dump(mode="json"),
        )
        response = client.post(
            "/location_template",
            json=LocationTemplate(template_name="dup_loc_tmpl").model_dump(mode="json"),
        )
        assert response.status_code == 409

    def test_get_nonexistent_returns_404(self, client):
        """Getting nonexistent template returns 404."""
        response = client.get("/location_template/nonexistent")
        assert response.status_code == 404

    def test_delete(self, client):
        """DELETE a location template."""
        template = LocationTemplate(template_name="to_delete")
        client.post(
            "/location_template",
            json=template.model_dump(mode="json"),
        )
        response = client.delete("/location_template/to_delete")
        assert response.status_code == 200

        response = client.get("/location_template/to_delete")
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        """Deleting nonexistent template returns 404."""
        response = client.delete("/location_template/nonexistent")
        assert response.status_code == 404


class TestLocationTemplateInit:
    """Tests for the idempotent location template init endpoint."""

    def test_init_creates_new(self, client):
        """Init creates template if it doesn't exist."""
        template = LocationTemplate(
            template_name="new_loc_tmpl",
            version="1.0.0",
        )
        response = client.post(
            "/location_template/init",
            json=template.model_dump(mode="json"),
        )
        assert response.status_code == 200
        result = LocationTemplate.model_validate(response.json())
        assert result.template_name == "new_loc_tmpl"

    def test_init_returns_existing_same_version(self, client):
        """Init returns existing template if same version."""
        template = LocationTemplate(
            template_name="existing_loc_tmpl",
            description="original",
            version="1.0.0",
        )
        resp1 = client.post(
            "/location_template/init",
            json=template.model_dump(mode="json"),
        )
        original_id = resp1.json()["template_id"]

        template2 = LocationTemplate(
            template_name="existing_loc_tmpl",
            description="changed",
            version="1.0.0",
        )
        resp2 = client.post(
            "/location_template/init",
            json=template2.model_dump(mode="json"),
        )
        assert resp2.json()["template_id"] == original_id
        assert resp2.json()["description"] == "original"

    def test_init_updates_on_version_change(self, client):
        """Init updates template if version differs."""
        template_v1 = LocationTemplate(
            template_name="versioned_loc_tmpl",
            description="v1",
            version="1.0.0",
        )
        resp1 = client.post(
            "/location_template/init",
            json=template_v1.model_dump(mode="json"),
        )
        original_id = resp1.json()["template_id"]

        template_v2 = LocationTemplate(
            template_name="versioned_loc_tmpl",
            description="v2",
            version="2.0.0",
        )
        resp2 = client.post(
            "/location_template/init",
            json=template_v2.model_dump(mode="json"),
        )
        result = resp2.json()
        assert result["template_id"] == original_id
        assert result["description"] == "v2"
        assert result["version"] == "2.0.0"


# --- Create Location from Template Tests ---


class TestCreateLocationFromTemplate:
    """Tests for POST /location/from_template."""

    def _setup_templates(self, client):
        """Helper to create repr templates and a location template."""
        # Create representation templates
        repr1 = LocationRepresentationTemplate(
            template_name="lh_deck_repr",
            default_values={"deck_type": "standard", "max_plates": 1},
            required_overrides=["deck_position"],
        )
        repr2 = LocationRepresentationTemplate(
            template_name="robotarm_deck",
            default_values={"gripper_config": "standard", "max_payload": 2.0},
            required_overrides=["position"],
        )
        client.post(
            "/representation_template",
            json=repr1.model_dump(mode="json"),
        )
        client.post(
            "/representation_template",
            json=repr2.model_dump(mode="json"),
        )

        # Create location template
        loc_tmpl = LocationTemplate(
            template_name="lh_deck_slot",
            resource_template_name="location_container",
            representation_templates={
                "deck_controller": "lh_deck_repr",
                "transfer_arm": "robotarm_deck",
            },
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

    def test_happy_path(self, client):
        """Create location from template with all overrides provided."""
        self._setup_templates(client)

        response = client.post(
            "/location/from_template",
            json={
                "location_name": "lh1.deck_1",
                "template_name": "lh_deck_slot",
                "node_bindings": {
                    "deck_controller": "liquidhandler_1",
                    "transfer_arm": "robotarm_1",
                },
                "representation_overrides": {
                    "deck_controller": {"deck_position": 1},
                    "transfer_arm": {"position": [10, 15, 5]},
                },
            },
        )
        assert response.status_code == 200
        location = Location.model_validate(response.json())
        assert location.location_name == "lh1.deck_1"
        assert location.location_template_name == "lh_deck_slot"
        assert location.node_bindings == {
            "deck_controller": "liquidhandler_1",
            "transfer_arm": "robotarm_1",
        }

        # Check representations were merged correctly
        lh_repr = location.representations["liquidhandler_1"]
        assert lh_repr["deck_type"] == "standard"  # from default
        assert lh_repr["max_plates"] == 1  # from default
        assert lh_repr["deck_position"] == 1  # from override

        arm_repr = location.representations["robotarm_1"]
        assert arm_repr["gripper_config"] == "standard"  # from default
        assert arm_repr["max_payload"] == 2.0  # from default
        assert arm_repr["position"] == [10, 15, 5]  # from override

    def test_missing_location_template_returns_404(self, client):
        """Create from nonexistent template returns 404."""
        response = client.post(
            "/location/from_template",
            json={
                "location_name": "test",
                "template_name": "nonexistent",
                "node_bindings": {},
                "representation_overrides": {},
            },
        )
        assert response.status_code == 404

    def test_missing_required_overrides_returns_422(self, client):
        """Missing required overrides returns 422."""
        self._setup_templates(client)

        response = client.post(
            "/location/from_template",
            json={
                "location_name": "missing_overrides",
                "template_name": "lh_deck_slot",
                "node_bindings": {
                    "deck_controller": "lh1",
                    "transfer_arm": "arm1",
                },
                "representation_overrides": {
                    "deck_controller": {"deck_position": 1},
                    # Missing required "position" for transfer_arm
                },
            },
        )
        assert response.status_code == 422
        assert "position" in response.json()["detail"]

    def test_missing_node_binding_returns_422(self, client):
        """Missing node binding for a role returns 422."""
        # Create a simple location template with one role, no required overrides on repr template
        repr_tmpl = LocationRepresentationTemplate(
            template_name="simple_repr",
            default_values={"key": "val"},
            required_overrides=[],
        )
        client.post(
            "/representation_template",
            json=repr_tmpl.model_dump(mode="json"),
        )
        loc_tmpl = LocationTemplate(
            template_name="binding_test_tmpl",
            representation_templates={"required_role": "simple_repr"},
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        response = client.post(
            "/location/from_template",
            json={
                "location_name": "missing_binding",
                "template_name": "binding_test_tmpl",
                "node_bindings": {},  # Missing "required_role" binding
                "representation_overrides": {},
            },
        )
        assert response.status_code == 422
        assert "required_role" in response.json()["detail"]

    def test_missing_repr_template_creates_with_overrides(self, client):
        """If repr template doesn't exist, location is created with override data only."""
        # Create location template referencing a non-existent repr template
        loc_tmpl = LocationTemplate(
            template_name="lazy_tmpl",
            representation_templates={"role1": "nonexistent_repr"},
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        response = client.post(
            "/location/from_template",
            json={
                "location_name": "lazy_loc",
                "template_name": "lazy_tmpl",
                "node_bindings": {"role1": "some_node"},
                "representation_overrides": {
                    "role1": {"custom_key": "custom_value"},
                },
            },
        )
        assert response.status_code == 200
        location = Location.model_validate(response.json())
        assert location.representations["some_node"] == {"custom_key": "custom_value"}

    def test_allow_transfers_override(self, client):
        """Allow_transfers can be overridden from request."""
        loc_tmpl = LocationTemplate(
            template_name="transfers_tmpl",
            default_allow_transfers=True,
        )
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        response = client.post(
            "/location/from_template",
            json={
                "location_name": "no_transfers",
                "template_name": "transfers_tmpl",
                "node_bindings": {},
                "representation_overrides": {},
                "allow_transfers": False,
            },
        )
        assert response.status_code == 200
        location = Location.model_validate(response.json())
        assert location.allow_transfers is False

    def test_duplicate_location_name_returns_409(self, client):
        """Creating from template with existing location name returns 409."""
        loc_tmpl = LocationTemplate(template_name="dup_tmpl")
        client.post(
            "/location_template",
            json=loc_tmpl.model_dump(mode="json"),
        )

        # Create first
        client.post(
            "/location/from_template",
            json={
                "location_name": "dup_loc",
                "template_name": "dup_tmpl",
                "node_bindings": {},
                "representation_overrides": {},
            },
        )

        # Try to create duplicate
        response = client.post(
            "/location/from_template",
            json={
                "location_name": "dup_loc",
                "template_name": "dup_tmpl",
                "node_bindings": {},
                "representation_overrides": {},
            },
        )
        assert response.status_code == 409

    def test_old_post_location_still_works(self, client):
        """Backwards compat: old POST /location still works."""
        location = Location(
            location_name="old_style",
            location_id=new_ulid_str(),
            representations={"node1": {"key": "val"}},
        )
        response = client.post(
            "/location",
            json=location.model_dump(mode="json"),
        )
        assert response.status_code == 200
        result = Location.model_validate(response.json())
        assert result.location_name == "old_style"


# --- Health Endpoint with Template Counts ---


def test_health_includes_template_counts(client):
    """Health endpoint reports template counts."""
    # Create some templates
    client.post(
        "/representation_template",
        json=LocationRepresentationTemplate(template_name="repr1").model_dump(
            mode="json"
        ),
    )
    client.post(
        "/location_template",
        json=LocationTemplate(template_name="tmpl1").model_dump(mode="json"),
    )

    response = client.get("/health")
    assert response.status_code == 200
    health = response.json()
    assert health["num_representation_templates"] == 1
    assert health["num_location_templates"] == 1
