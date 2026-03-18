"""Tests for the dual-handler LocationStateHandler (document database + cache)."""

import pytest
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
from madsci.location_manager.location_state_handler import LocationStateHandler


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
def settings():
    """Create test settings."""
    return LocationManagerSettings(enable_registry_resolution=False)


@pytest.fixture
def state_handler(settings, document_handler, cache_handler):
    """Create a LocationStateHandler with both handlers."""
    handler = LocationStateHandler(
        settings=settings,
        manager_id="test_manager",
        document_handler=document_handler,
        cache_handler=cache_handler,
    )
    yield handler
    handler.close()


@pytest.fixture
def sample_location():
    """Create a sample location."""
    return Location(
        location_name="test_location",
        location_id=new_ulid_str(),
        description="A test location",
    )


class TestInit:
    """Tests for state handler initialization."""

    def test_init_with_both_handlers(self, settings, document_handler, cache_handler):
        """Construct with InMemoryDocumentStorageHandler + InMemoryCacheHandler."""
        handler = LocationStateHandler(
            settings=settings,
            manager_id="test",
            document_handler=document_handler,
            cache_handler=cache_handler,
        )
        assert handler._document_handler is document_handler
        assert handler._cache_handler is cache_handler
        handler.close()


class TestAddLocation:
    """Tests for adding locations."""

    def test_add_location_stores_in_mongo(self, state_handler, sample_location):
        """Add location, verify it's stored in document database collection."""
        result = state_handler.add_location(sample_location)
        assert result is not None
        assert result.location_name == sample_location.location_name

        # Verify it's in the document database collection
        retrieved = state_handler.get_location(sample_location.location_name)
        assert retrieved is not None
        assert retrieved.location_id == sample_location.location_id

    def test_add_location_duplicate_returns_none(self, state_handler, sample_location):
        """Add same name twice - second should return None."""
        state_handler.add_location(sample_location)
        result = state_handler.add_location(sample_location)
        assert result is None

    def test_add_location_from_dict(self, state_handler):
        """Add location from a dict."""
        loc_data = {
            "location_name": "dict_location",
            "location_id": new_ulid_str(),
        }
        result = state_handler.add_location(loc_data)
        assert result is not None
        assert result.location_name == "dict_location"


class TestGetLocation:
    """Tests for getting locations."""

    def test_get_location_by_name(self, state_handler, sample_location):
        """Add then retrieve by name."""
        state_handler.add_location(sample_location)
        result = state_handler.get_location(sample_location.location_name)
        assert result is not None
        assert result.location_name == sample_location.location_name
        assert result.location_id == sample_location.location_id

    def test_get_location_nonexistent(self, state_handler):
        """Get non-existent location returns None."""
        result = state_handler.get_location("nonexistent")
        assert result is None

    def test_get_location_by_id(self, state_handler, sample_location):
        """Add then retrieve by ID (now O(1) via mongo query)."""
        state_handler.add_location(sample_location)
        result = state_handler.get_location_by_id(sample_location.location_id)
        assert result is not None
        assert result.location_id == sample_location.location_id
        assert result.location_name == sample_location.location_name

    def test_get_location_by_id_nonexistent(self, state_handler):
        """Get by non-existent ID returns None."""
        result = state_handler.get_location_by_id("nonexistent_id")
        assert result is None

    def test_get_locations_returns_all(self, state_handler):
        """Add multiple, get all."""
        loc1 = Location(location_name="loc_a", location_id=new_ulid_str())
        loc2 = Location(location_name="loc_b", location_id=new_ulid_str())
        loc3 = Location(location_name="loc_c", location_id=new_ulid_str())
        state_handler.add_location(loc1)
        state_handler.add_location(loc2)
        state_handler.add_location(loc3)
        locations = state_handler.get_locations()
        assert len(locations) == 3
        names = {loc.location_name for loc in locations}
        assert names == {"loc_a", "loc_b", "loc_c"}


class TestUpdateLocation:
    """Tests for updating locations."""

    def test_update_location(self, state_handler, sample_location):
        """Add, update, verify persisted."""
        state_handler.add_location(sample_location)
        sample_location.description = "Updated description"
        result = state_handler.update_location(sample_location)
        assert result.description == "Updated description"

        # Verify persisted
        retrieved = state_handler.get_location(sample_location.location_name)
        assert retrieved.description == "Updated description"

    def test_update_location_wrong_id_raises(self, state_handler, sample_location):
        """Mismatched ID raises ValueError."""
        state_handler.add_location(sample_location)
        wrong_id_location = Location(
            location_name=sample_location.location_name,
            location_id=new_ulid_str(),  # Different ID
        )
        with pytest.raises(ValueError):
            state_handler.update_location(wrong_id_location)

    def test_update_nonexistent_raises(self, state_handler):
        """Updating non-existent raises KeyError."""
        loc = Location(location_name="Nonexistent", location_id=new_ulid_str())
        with pytest.raises(KeyError):
            state_handler.update_location(loc)


class TestDeleteLocation:
    """Tests for deleting locations."""

    def test_delete_location(self, state_handler, sample_location):
        """Add, delete, verify removed."""
        state_handler.add_location(sample_location)
        result = state_handler.delete_location(sample_location.location_name)
        assert result is True

        # Verify removed
        retrieved = state_handler.get_location(sample_location.location_name)
        assert retrieved is None

    def test_delete_nonexistent_returns_false(self, state_handler):
        """Delete non-existent returns False."""
        result = state_handler.delete_location("nonexistent")
        assert result is False


class TestCacheTransientState:
    """Tests for cache-based transient state operations."""

    def test_state_change_counter_uses_cache(self, state_handler):
        """mark_state_changed() increments cache counter."""
        val1 = state_handler.mark_state_changed()
        val2 = state_handler.mark_state_changed()
        assert val2 > val1

    def test_has_state_changed_uses_cache(self, state_handler):
        """has_state_changed() reads from cache."""
        # Synchronize the marker by reading once (initial state may differ)
        state_handler.has_state_changed()
        # Now no further changes, should be False
        assert state_handler.has_state_changed() is False
        # After marking changed
        state_handler.mark_state_changed()
        assert state_handler.has_state_changed() is True
        # After checking, should be false until next change
        assert state_handler.has_state_changed() is False

    def test_lock_uses_cache(self, state_handler):
        """Lock is created via cache handler."""
        lock = state_handler.location_state_lock()
        assert lock is not None


class TestRepresentationTemplateCRUD:
    """Tests for representation template CRUD operations."""

    def test_add_and_get_repr_template(self, state_handler):
        """Add a representation template and retrieve it."""
        template = LocationRepresentationTemplate(
            template_name="robotarm_deck",
            default_values={"gripper_config": "standard", "max_payload": 2.0},
            required_overrides=["position"],
        )
        result = state_handler.add_representation_template(template)
        assert result is not None
        assert result.template_name == "robotarm_deck"

        retrieved = state_handler.get_representation_template("robotarm_deck")
        assert retrieved is not None
        assert retrieved.template_id == template.template_id
        assert retrieved.default_values == {
            "gripper_config": "standard",
            "max_payload": 2.0,
        }

    def test_add_duplicate_returns_none(self, state_handler):
        """Adding a template with duplicate name returns None."""
        template = LocationRepresentationTemplate(template_name="test_repr")
        state_handler.add_representation_template(template)
        result = state_handler.add_representation_template(
            LocationRepresentationTemplate(template_name="test_repr")
        )
        assert result is None

    def test_get_nonexistent_returns_none(self, state_handler):
        """Getting a nonexistent template returns None."""
        result = state_handler.get_representation_template("nonexistent")
        assert result is None

    def test_get_all_templates(self, state_handler):
        """Get all representation templates."""
        state_handler.add_representation_template(
            LocationRepresentationTemplate(template_name="repr_a")
        )
        state_handler.add_representation_template(
            LocationRepresentationTemplate(template_name="repr_b")
        )
        templates = state_handler.get_representation_templates()
        assert len(templates) == 2
        names = {t.template_name for t in templates}
        assert names == {"repr_a", "repr_b"}

    def test_update_repr_template(self, state_handler):
        """Update a representation template."""
        template = LocationRepresentationTemplate(
            template_name="test_repr",
            default_values={"key": "old"},
        )
        state_handler.add_representation_template(template)

        template.default_values = {"key": "new"}
        result = state_handler.update_representation_template(template)
        assert result.default_values == {"key": "new"}

        retrieved = state_handler.get_representation_template("test_repr")
        assert retrieved.default_values == {"key": "new"}

    def test_update_nonexistent_raises_key_error(self, state_handler):
        """Updating a nonexistent template raises KeyError."""
        template = LocationRepresentationTemplate(template_name="nonexistent")
        with pytest.raises(KeyError):
            state_handler.update_representation_template(template)

    def test_update_wrong_id_raises_value_error(self, state_handler):
        """Updating with wrong ID raises ValueError."""
        template = LocationRepresentationTemplate(template_name="test_repr")
        state_handler.add_representation_template(template)

        wrong_id = LocationRepresentationTemplate(
            template_name="test_repr",
            template_id=new_ulid_str(),
        )
        with pytest.raises(ValueError):
            state_handler.update_representation_template(wrong_id)

    def test_delete_repr_template(self, state_handler):
        """Delete a representation template."""
        template = LocationRepresentationTemplate(template_name="to_delete")
        state_handler.add_representation_template(template)

        result = state_handler.delete_representation_template("to_delete")
        assert result is True
        assert state_handler.get_representation_template("to_delete") is None

    def test_delete_nonexistent_returns_false(self, state_handler):
        """Deleting a nonexistent template returns False."""
        result = state_handler.delete_representation_template("nonexistent")
        assert result is False


class TestLocationTemplateCRUD:
    """Tests for location template CRUD operations."""

    def test_add_and_get_location_template(self, state_handler):
        """Add a location template and retrieve it."""
        template = LocationTemplate(
            template_name="ot2_deck_slot",
            resource_template_name="location_container",
            representation_templates={
                "deck_controller": "lh_deck_repr",
                "transfer_arm": "robotarm_deck",
            },
        )
        result = state_handler.add_location_template(template)
        assert result is not None
        assert result.template_name == "ot2_deck_slot"

        retrieved = state_handler.get_location_template("ot2_deck_slot")
        assert retrieved is not None
        assert retrieved.representation_templates == {
            "deck_controller": "lh_deck_repr",
            "transfer_arm": "robotarm_deck",
        }

    def test_add_duplicate_returns_none(self, state_handler):
        """Adding a template with duplicate name returns None."""
        template = LocationTemplate(template_name="test_loc_tmpl")
        state_handler.add_location_template(template)
        result = state_handler.add_location_template(
            LocationTemplate(template_name="test_loc_tmpl")
        )
        assert result is None

    def test_get_nonexistent_returns_none(self, state_handler):
        """Getting a nonexistent template returns None."""
        result = state_handler.get_location_template("nonexistent")
        assert result is None

    def test_get_all_templates(self, state_handler):
        """Get all location templates."""
        state_handler.add_location_template(LocationTemplate(template_name="tmpl_a"))
        state_handler.add_location_template(LocationTemplate(template_name="tmpl_b"))
        templates = state_handler.get_location_templates()
        assert len(templates) == 2
        names = {t.template_name for t in templates}
        assert names == {"tmpl_a", "tmpl_b"}

    def test_update_location_template(self, state_handler):
        """Update a location template."""
        template = LocationTemplate(
            template_name="test_tmpl",
            description="old description",
        )
        state_handler.add_location_template(template)

        template.description = "new description"
        result = state_handler.update_location_template(template)
        assert result.description == "new description"

        retrieved = state_handler.get_location_template("test_tmpl")
        assert retrieved.description == "new description"

    def test_update_nonexistent_raises_key_error(self, state_handler):
        """Updating a nonexistent template raises KeyError."""
        template = LocationTemplate(template_name="nonexistent")
        with pytest.raises(KeyError):
            state_handler.update_location_template(template)

    def test_update_wrong_id_raises_value_error(self, state_handler):
        """Updating with wrong ID raises ValueError."""
        template = LocationTemplate(template_name="test_tmpl")
        state_handler.add_location_template(template)

        wrong_id = LocationTemplate(
            template_name="test_tmpl",
            template_id=new_ulid_str(),
        )
        with pytest.raises(ValueError):
            state_handler.update_location_template(wrong_id)

    def test_delete_location_template(self, state_handler):
        """Delete a location template."""
        template = LocationTemplate(template_name="to_delete")
        state_handler.add_location_template(template)

        result = state_handler.delete_location_template("to_delete")
        assert result is True
        assert state_handler.get_location_template("to_delete") is None

    def test_delete_nonexistent_returns_false(self, state_handler):
        """Deleting a nonexistent template returns False."""
        result = state_handler.delete_location_template("nonexistent")
        assert result is False

    def test_collections_are_independent(self, state_handler):
        """Repr templates and location templates are stored independently."""
        state_handler.add_representation_template(
            LocationRepresentationTemplate(template_name="same_name")
        )
        state_handler.add_location_template(LocationTemplate(template_name="same_name"))

        repr_tmpl = state_handler.get_representation_template("same_name")
        loc_tmpl = state_handler.get_location_template("same_name")
        assert repr_tmpl is not None
        assert loc_tmpl is not None
        assert repr_tmpl.template_id != loc_tmpl.template_id


class TestClose:
    """Tests for closing the handler."""

    def test_close_closes_both_handlers(self, settings):
        """Close should close both document database and cache handlers."""
        mongo = InMemoryDocumentStorageHandler(database_name="test")
        cache = InMemoryCacheHandler()
        handler = LocationStateHandler(
            settings=settings,
            manager_id="test",
            document_handler=mongo,
            cache_handler=cache,
        )
        handler.close()
        # Both handlers should have been closed without errors
