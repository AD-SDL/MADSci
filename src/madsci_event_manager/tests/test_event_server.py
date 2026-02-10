"""
Test the Event Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.event_types import (
    EmailAlertsConfig,
    Event,
    EventManagerDefinition,
    EventManagerSettings,
    EventType,
)
from madsci.event_manager.event_server import EventManager
from pymongo.synchronous.database import Database
from pytest_mock_resources import MongoConfig, create_mongo_fixture

event_manager_def = EventManagerDefinition(
    name="test_event_manager",
)
event_manager_settings = EventManagerSettings(
    email_alerts=EmailAlertsConfig(email_addresses=["test@example.com"]),
)


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Configure the MongoDB fixture."""
    return MongoConfig(image="mongo:8.0")


db_connection = create_mongo_fixture()


@pytest.fixture
def test_client(db_connection: Database, tmp_path: Path) -> TestClient:
    """Event Server Test Client Fixture"""
    settings = EventManagerSettings(
        email_alerts=EmailAlertsConfig(email_addresses=["test@example.com"]),
        manager_definition=tmp_path / "event.manager.yaml",
    )
    manager = EventManager(
        settings=settings,
        definition=event_manager_def,
        db_connection=db_connection,
    )
    app = manager.create_server()
    client = TestClient(app)
    yield client
    client.close()


def test_root(test_client: TestClient) -> None:
    """
    Test the root endpoint for the Event_Manager's server.
    Should return an EventManagerDefinition.
    """
    result = test_client.get("/").json()
    EventManagerDefinition.model_validate(result)


def test_roundtrip_event(test_client: TestClient) -> None:
    """
    Test that we can send and then retrieve an event by ID.
    """
    test_event = Event(
        event_type=EventType.TEST,
        event_data={"test": "data"},
    )
    result = test_client.post("/event", json=test_event.model_dump(mode="json")).json()
    assert Event.model_validate(result) == test_event
    result = test_client.get(f"/event/{test_event.event_id}").json()
    assert Event.model_validate(result) == test_event


def test_get_events(test_client: TestClient) -> None:
    """
    Test that we can retrieve all events and they are returned as a dictionary in reverse-chronological order, with the correct number of events.
    """
    for i in range(10):
        test_event = Event(
            event_type=EventType.TEST,
            event_data={"test": i},
        )
        test_client.post("/event", json=test_event.model_dump(mode="json"))
    query_number = 5
    result = test_client.get("/events", params={"number": query_number}).json()
    # * Check that the number of events returned is correct
    assert len(result) == query_number
    previous_timestamp = float("inf")
    for _, value in result.items():
        event = Event.model_validate(value)
        # * Check that the events are in reverse-chronological order
        assert event.event_data["test"] in range(5, 10)
        assert previous_timestamp >= event.event_timestamp.timestamp()
        previous_timestamp = event.event_timestamp.timestamp()


def test_query_events(test_client: TestClient) -> None:
    """
    Test querying events based on a selector.
    """
    for i in range(10, 20):
        test_event = Event(
            event_type=EventType.TEST,
            event_data={"test": i},
        )
        test_client.post("/event", json=test_event.model_dump(mode="json"))
    test_val = 10
    selector = {"event_data.test": {"$gte": test_val}}
    result = test_client.post("/events/query", json=selector).json()
    assert len(result) == test_val
    for _, value in result.items():
        event = Event.model_validate(value)
        assert event.event_data["test"] >= test_val


def test_event_alert(test_client: TestClient) -> None:
    """
    Test that an alert is triggered when an event meets the alert criteria.
    """
    # Create an event that should trigger an alert
    alert_event = Event(
        event_type=EventType.TEST,
        log_level=event_manager_settings.alert_level,
        alert=True,
        event_data={"alert": "This is a test alert"},
    )

    # Post the event to the server
    with patch(
        "madsci.event_manager.notifications.EmailAlerts.send_email"
    ) as mock_send_email:
        test_client.post("/event", json=alert_event.model_dump(mode="json"))

        # Assert that the email alert was sent
        mock_send_email.assert_called()
        assert mock_send_email.call_count == len(
            event_manager_settings.email_alerts.email_addresses
        )


def test_health_endpoint(test_client: TestClient) -> None:
    """Test the health endpoint of the Event Manager."""
    response = test_client.get("/health")
    assert response.status_code == 200

    health_data = response.json()
    assert "healthy" in health_data
    assert "description" in health_data
    assert "db_connected" in health_data
    assert "total_events" in health_data

    # Health should be True when database is working
    assert health_data["healthy"] is True
    assert health_data["db_connected"] is True
    assert isinstance(health_data["total_events"], int)
    assert health_data["total_events"] >= 0


# =============================================================================
# Event Retention Tests
# =============================================================================


class TestEventRetention:
    """Test EventManager retention functionality."""

    def test_archive_events_by_ids(self, test_client: TestClient) -> None:
        """Test that specific events can be archived by their IDs."""
        # Create test events
        events = []
        for i in range(3):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"archive_test_{i}"},
            )
            test_client.post("/event", json=event.model_dump(mode="json"))
            events.append(event)

        # Archive specific events
        event_ids = [events[0].event_id, events[1].event_id]
        response = test_client.post("/events/archive", json={"event_ids": event_ids})
        assert response.status_code == 200
        result = response.json()
        assert result["archived_count"] == 2

        # Verify archived events
        response = test_client.get(f"/event/{events[0].event_id}")
        event_data = response.json()
        assert event_data["archived"] is True
        assert event_data["archived_at"] is not None

        # Verify non-archived event
        response = test_client.get(f"/event/{events[2].event_id}")
        event_data = response.json()
        assert event_data["archived"] is False

    def test_archive_events_by_date(self, test_client: TestClient) -> None:
        """Test that events before a certain date can be archived."""
        # Create an old event (simulate by setting timestamp in past)
        old_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "old_event"},
            event_timestamp=datetime.now() - timedelta(days=100),
        )
        test_client.post("/event", json=old_event.model_dump(mode="json"))

        # Create a recent event
        recent_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "recent_event"},
        )
        test_client.post("/event", json=recent_event.model_dump(mode="json"))

        # Archive events older than 50 days
        before_date = (datetime.now() - timedelta(days=50)).isoformat()
        response = test_client.post(
            "/events/archive", json={"before_date": before_date}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["archived_count"] >= 1

    def test_archived_events_excluded_from_queries_by_default(
        self, test_client: TestClient
    ) -> None:
        """Test that archived events are excluded from default queries."""
        # Create and archive an event
        event = Event(
            event_type=EventType.TEST,
            event_data={"test": "excluded_test"},
        )
        test_client.post("/event", json=event.model_dump(mode="json"))
        test_client.post("/events/archive", json={"event_ids": [event.event_id]})

        # Query events - archived should be excluded by default
        response = test_client.get("/events", params={"number": 100})
        result = response.json()

        # The archived event should not appear in results
        assert event.event_id not in result

    def test_include_archived_events_option(self, test_client: TestClient) -> None:
        """Test that archived events can be included via query option."""
        # Create and archive an event
        event = Event(
            event_type=EventType.TEST,
            event_data={"test": "include_archived_test"},
        )
        test_client.post("/event", json=event.model_dump(mode="json"))
        test_client.post("/events/archive", json={"event_ids": [event.event_id]})

        # Query with include_archived=True
        response = test_client.get(
            "/events", params={"number": 100, "include_archived": True}
        )
        result = response.json()

        # The archived event should appear in results
        assert event.event_id in result

    def test_get_archived_events_endpoint(self, test_client: TestClient) -> None:
        """Test retrieving only archived events."""
        # Create and archive some events
        archived_events = []
        for i in range(3):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"archived_only_{i}"},
            )
            test_client.post("/event", json=event.model_dump(mode="json"))
            archived_events.append(event)

        # Archive them
        event_ids = [e.event_id for e in archived_events]
        test_client.post("/events/archive", json={"event_ids": event_ids})

        # Get only archived events
        response = test_client.get("/events/archived", params={"number": 100})
        assert response.status_code == 200
        result = response.json()

        # All returned events should be archived
        for _event_id, event_data in result.items():
            assert event_data["archived"] is True

    def test_purge_archived_events(self, test_client: TestClient) -> None:
        """Test permanently deleting archived events."""

        # Create an event and archive it
        event = Event(
            event_type=EventType.TEST,
            event_data={"test": "purge_test"},
        )
        test_client.post("/event", json=event.model_dump(mode="json"))

        # Archive the event (this will set archived_at to current time)
        test_client.post("/events/archive", json={"event_ids": [event.event_id]})

        # Manually update the archived_at to simulate an old archive
        # (This is done via the purge endpoint with older_than_days=0 for testing)
        response = test_client.delete("/events/archived", params={"older_than_days": 0})
        assert response.status_code == 200
        result = response.json()
        assert result["deleted_count"] >= 1

        # Verify event was deleted
        response = test_client.get(f"/event/{event.event_id}")
        assert response.status_code == 404


class TestEventRetentionBatching:
    """Test batch processing for retention operations."""

    def test_archive_respects_batch_size(self, test_client: TestClient) -> None:
        """Test that archiving processes events in batches."""
        # Create multiple old events
        for i in range(5):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"batch_test_{i}"},
                event_timestamp=datetime.now() - timedelta(days=100),
            )
            test_client.post("/event", json=event.model_dump(mode="json"))

        # Archive with small batch size
        before_date = (datetime.now() - timedelta(days=50)).isoformat()
        response = test_client.post(
            "/events/archive",
            json={"before_date": before_date, "batch_size": 2},
        )
        assert response.status_code == 200
        # Should still archive all, just in batches
        result = response.json()
        assert result["archived_count"] >= 5


# =============================================================================
# Event Backup Tests
# =============================================================================


class TestEventBackup:
    """Test EventManager backup functionality."""

    def test_create_backup(self, test_client: TestClient) -> None:
        """Test creating a one-time backup.

        Note: This test mocks MongoDBBackupTool since the actual backup requires
        mongodump to be installed and connected to the correct MongoDB instance,
        which is handled differently in the test environment.
        """
        # Create some events first
        for i in range(3):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"backup_test_{i}"},
            )
            test_client.post("/event", json=event.model_dump(mode="json"))

        # Mock the MongoDBBackupTool to avoid requiring mongodump and actual DB connection
        with patch(
            "madsci.event_manager.event_server.MongoDBBackupTool"
        ) as mock_backup_tool_class:
            mock_backup_tool = MagicMock()
            mock_backup_tool.create_backup.return_value = Path(
                "/mock/backup/path/test_backup"
            )
            mock_backup_tool_class.return_value = mock_backup_tool

            # Create backup
            response = test_client.post("/backup", json={"description": "test_backup"})
            assert response.status_code == 200
            result = response.json()
            assert "backup_path" in result
            assert result["status"] == "completed"

            # Verify the backup tool was called correctly
            mock_backup_tool.create_backup.assert_called_once_with(
                name_suffix="test_backup"
            )

    def test_get_backup_status(self, test_client: TestClient) -> None:
        """Test getting backup status."""
        response = test_client.get("/backup/status")
        assert response.status_code == 200
        result = response.json()
        assert "backup_enabled" in result
        assert "available_backups" in result


# =============================================================================
# Event Query Improvements Tests
# =============================================================================


class TestEventQueryImprovements:
    """Test improved event query options."""

    def test_query_with_pagination_offset(self, test_client: TestClient) -> None:
        """Test paginated event queries with offset."""
        # Create 10 events
        created_events = []
        for i in range(10):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"pagination_test_{i}"},
            )
            test_client.post("/event", json=event.model_dump(mode="json"))
            created_events.append(event)

        # Get first page
        response = test_client.get("/events", params={"number": 5, "offset": 0})
        page1 = response.json()
        assert len(page1) == 5

        # Get second page
        response = test_client.get("/events", params={"number": 5, "offset": 5})
        page2 = response.json()
        assert len(page2) == 5

        # Verify no overlap
        page1_ids = set(page1.keys())
        page2_ids = set(page2.keys())
        assert page1_ids.isdisjoint(page2_ids)

    def test_query_with_date_range_start(self, test_client: TestClient) -> None:
        """Test date range filtering with start_time."""
        # Create old and new events
        old_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "old_date_range"},
            event_timestamp=datetime.now() - timedelta(days=10),
        )
        test_client.post("/event", json=old_event.model_dump(mode="json"))

        new_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "new_date_range"},
        )
        test_client.post("/event", json=new_event.model_dump(mode="json"))

        # Query with start_time
        start_time = (datetime.now() - timedelta(days=5)).isoformat()
        response = test_client.get("/events", params={"start_time": start_time})
        result = response.json()

        # Should only include recent event
        assert new_event.event_id in result
        assert old_event.event_id not in result

    def test_query_with_date_range_end(self, test_client: TestClient) -> None:
        """Test date range filtering with end_time."""
        # Create events
        old_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "old_end_range"},
            event_timestamp=datetime.now() - timedelta(days=10),
        )
        test_client.post("/event", json=old_event.model_dump(mode="json"))

        new_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "new_end_range"},
        )
        test_client.post("/event", json=new_event.model_dump(mode="json"))

        # Query with end_time
        end_time = (datetime.now() - timedelta(days=5)).isoformat()
        response = test_client.get("/events", params={"end_time": end_time})
        result = response.json()

        # Should only include old event
        assert old_event.event_id in result
        assert new_event.event_id not in result

    def test_query_with_date_range_both(self, test_client: TestClient) -> None:
        """Test date range filtering with both start_time and end_time."""
        # Create events at different times
        very_old_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "very_old"},
            event_timestamp=datetime.now() - timedelta(days=20),
        )
        test_client.post("/event", json=very_old_event.model_dump(mode="json"))

        middle_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "middle"},
            event_timestamp=datetime.now() - timedelta(days=10),
        )
        test_client.post("/event", json=middle_event.model_dump(mode="json"))

        new_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "new"},
        )
        test_client.post("/event", json=new_event.model_dump(mode="json"))

        # Query with date range
        start_time = (datetime.now() - timedelta(days=15)).isoformat()
        end_time = (datetime.now() - timedelta(days=5)).isoformat()
        response = test_client.get(
            "/events", params={"start_time": start_time, "end_time": end_time}
        )
        result = response.json()

        # Should only include middle event
        assert middle_event.event_id in result
        assert very_old_event.event_id not in result
        assert new_event.event_id not in result


class TestTTLIndex:
    """Test MongoDB TTL index configuration."""

    def test_archived_events_have_archived_at_field(
        self, test_client: TestClient
    ) -> None:
        """Test that archived events have archived_at field set."""
        # Create and archive an event
        event = Event(
            event_type=EventType.TEST,
            event_data={"test": "ttl_test"},
        )
        test_client.post("/event", json=event.model_dump(mode="json"))
        test_client.post("/events/archive", json={"event_ids": [event.event_id]})

        # Verify archived_at is set
        response = test_client.get(f"/event/{event.event_id}")
        event_data = response.json()
        assert event_data["archived"] is True
        assert event_data["archived_at"] is not None

        # Verify archived_at is a valid datetime
        archived_at = datetime.fromisoformat(
            event_data["archived_at"].replace("Z", "+00:00")
        )
        assert archived_at is not None


# =============================================================================
# Background Retention Task Tests
# =============================================================================


class TestBackgroundRetentionTask:
    """Test the background retention task functionality."""

    def test_archive_old_events_method(
        self, db_connection: Database, tmp_path: Path
    ) -> None:
        """Test that _archive_old_events correctly archives old events."""
        # Create manager with retention enabled and short soft_delete period for testing
        settings = EventManagerSettings(
            retention_enabled=True,
            soft_delete_after_days=1,  # Archive events older than 1 day
            archive_batch_size=10,
            manager_definition=tmp_path / "event.manager.yaml",
        )
        manager = EventManager(
            settings=settings,
            definition=event_manager_def,
            db_connection=db_connection,
        )

        # Create old events (2 days ago)
        old_events = []
        for i in range(3):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"old_auto_archive_{i}"},
                event_timestamp=datetime.now() - timedelta(days=2),
            )
            manager.events.insert_one(event.to_mongo())
            old_events.append(event)

        # Create recent event (should not be archived)
        recent_event = Event(
            event_type=EventType.TEST,
            event_data={"test": "recent_auto_archive"},
        )
        manager.events.insert_one(recent_event.to_mongo())

        # Run the archive method
        archived_count = asyncio.run(manager._archive_old_events())

        # Should have archived the 3 old events
        assert archived_count == 3

        # Verify old events are archived
        for event in old_events:
            doc = manager.events.find_one({"_id": event.event_id})
            assert doc["archived"] is True
            assert doc["archived_at"] is not None

        # Verify recent event is not archived
        doc = manager.events.find_one({"_id": recent_event.event_id})
        assert doc["archived"] is False

    def test_archive_old_events_respects_batch_limit(
        self, db_connection: Database, tmp_path: Path
    ) -> None:
        """Test that _archive_old_events respects max_batches_per_run limit."""
        # Create manager with small batch limits
        settings = EventManagerSettings(
            retention_enabled=True,
            soft_delete_after_days=1,
            archive_batch_size=2,  # 2 events per batch
            max_batches_per_run=2,  # Max 2 batches = 4 events max
            manager_definition=tmp_path / "event.manager.yaml",
        )
        manager = EventManager(
            settings=settings,
            definition=event_manager_def,
            db_connection=db_connection,
        )

        # Create 10 old events
        for i in range(10):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"batch_limit_test_{i}"},
                event_timestamp=datetime.now() - timedelta(days=2),
            )
            manager.events.insert_one(event.to_mongo())

        # Run archive - should only process 4 events (2 batches * 2 per batch)
        archived_count = asyncio.run(manager._archive_old_events())
        assert archived_count == 4

        # Verify only 4 events are archived
        archived_docs = list(manager.events.find({"archived": True}))
        assert len(archived_docs) == 4

        # Run again - should archive 4 more
        archived_count = asyncio.run(manager._archive_old_events())
        assert archived_count == 4

        # Verify 8 total archived
        archived_docs = list(manager.events.find({"archived": True}))
        assert len(archived_docs) == 8

    def test_archive_old_events_no_events_to_archive(
        self, db_connection: Database, tmp_path: Path
    ) -> None:
        """Test that _archive_old_events handles case with no events to archive."""
        settings = EventManagerSettings(
            retention_enabled=True,
            soft_delete_after_days=30,
            manager_definition=tmp_path / "event.manager.yaml",
        )
        manager = EventManager(
            settings=settings,
            definition=event_manager_def,
            db_connection=db_connection,
        )

        # Create only recent events
        for i in range(3):
            event = Event(
                event_type=EventType.TEST,
                event_data={"test": f"recent_only_{i}"},
            )
            manager.events.insert_one(event.to_mongo())

        # Run archive - should archive nothing
        archived_count = asyncio.run(manager._archive_old_events())
        assert archived_count == 0


class TestRetentionErrorHandling:
    """Test retention error handling behavior."""

    def test_default_fail_on_retention_error_is_false(self) -> None:
        """Test that fail_on_retention_error defaults to False."""
        settings = EventManagerSettings()
        assert settings.fail_on_retention_error is False

    def test_retention_settings_configuration(self) -> None:
        """Test that retention settings can be configured."""
        settings = EventManagerSettings(
            retention_enabled=True,
            soft_delete_after_days=60,
            hard_delete_after_days=180,
            retention_check_interval_hours=12,
            archive_batch_size=500,
            max_batches_per_run=50,
            fail_on_retention_error=True,
        )
        assert settings.retention_enabled is True
        assert settings.soft_delete_after_days == 60
        assert settings.hard_delete_after_days == 180
        assert settings.retention_check_interval_hours == 12
        assert settings.archive_batch_size == 500
        assert settings.max_batches_per_run == 50
        assert settings.fail_on_retention_error is True
