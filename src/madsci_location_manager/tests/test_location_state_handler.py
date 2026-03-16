"""Tests for the dual-handler LocationStateHandler (MongoDB + Redis)."""

import pytest
from madsci.common.db_handlers.mongo_handler import InMemoryMongoHandler
from madsci.common.db_handlers.redis_handler import InMemoryRedisHandler
from madsci.common.types.location_types import Location, LocationManagerSettings
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_state_handler import LocationStateHandler


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
def settings():
    """Create test settings."""
    return LocationManagerSettings(enable_registry_resolution=False)


@pytest.fixture
def state_handler(settings, mongo_handler, redis_handler):
    """Create a LocationStateHandler with both handlers."""
    handler = LocationStateHandler(
        settings=settings,
        manager_id="test_manager",
        mongo_handler=mongo_handler,
        redis_handler=redis_handler,
    )
    yield handler
    handler.close()


@pytest.fixture
def sample_location():
    """Create a sample location."""
    return Location(
        location_name="Test Location",
        location_id=new_ulid_str(),
        description="A test location",
    )


class TestInit:
    """Tests for state handler initialization."""

    def test_init_with_both_handlers(self, settings, mongo_handler, redis_handler):
        """Construct with InMemoryMongoHandler + InMemoryRedisHandler."""
        handler = LocationStateHandler(
            settings=settings,
            manager_id="test",
            mongo_handler=mongo_handler,
            redis_handler=redis_handler,
        )
        assert handler._mongo_handler is mongo_handler
        assert handler._redis_handler is redis_handler
        handler.close()


class TestAddLocation:
    """Tests for adding locations."""

    def test_add_location_stores_in_mongo(self, state_handler, sample_location):
        """Add location, verify it's stored in mongo collection."""
        result = state_handler.add_location(sample_location)
        assert result is not None
        assert result.location_name == sample_location.location_name

        # Verify it's in the MongoDB collection
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
            "location_name": "Dict Location",
            "location_id": new_ulid_str(),
        }
        result = state_handler.add_location(loc_data)
        assert result is not None
        assert result.location_name == "Dict Location"


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
        loc1 = Location(location_name="Loc A", location_id=new_ulid_str())
        loc2 = Location(location_name="Loc B", location_id=new_ulid_str())
        loc3 = Location(location_name="Loc C", location_id=new_ulid_str())
        state_handler.add_location(loc1)
        state_handler.add_location(loc2)
        state_handler.add_location(loc3)
        locations = state_handler.get_locations()
        assert len(locations) == 3
        names = {loc.location_name for loc in locations}
        assert names == {"Loc A", "Loc B", "Loc C"}


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


class TestRedisTransientState:
    """Tests for Redis-based transient state operations."""

    def test_state_change_counter_uses_redis(self, state_handler):
        """mark_state_changed() increments Redis counter."""
        val1 = state_handler.mark_state_changed()
        val2 = state_handler.mark_state_changed()
        assert val2 > val1

    def test_has_state_changed_uses_redis(self, state_handler):
        """has_state_changed() reads from Redis."""
        # Synchronize the marker by reading once (initial state may differ)
        state_handler.has_state_changed()
        # Now no further changes, should be False
        assert state_handler.has_state_changed() is False
        # After marking changed
        state_handler.mark_state_changed()
        assert state_handler.has_state_changed() is True
        # After checking, should be false until next change
        assert state_handler.has_state_changed() is False

    def test_lock_uses_redis(self, state_handler):
        """Lock is created via Redis handler."""
        lock = state_handler.location_state_lock()
        assert lock is not None


class TestClose:
    """Tests for closing the handler."""

    def test_close_closes_both_handlers(self, settings):
        """Close should close both mongo and redis handlers."""
        mongo = InMemoryMongoHandler(database_name="test")
        redis = InMemoryRedisHandler()
        handler = LocationStateHandler(
            settings=settings,
            manager_id="test",
            mongo_handler=mongo,
            redis_handler=redis,
        )
        handler.close()
        # Both handlers should have been closed without errors
