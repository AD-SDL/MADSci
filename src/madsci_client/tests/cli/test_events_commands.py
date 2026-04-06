"""Tests for the madsci events command group."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.event_types import Event, EventLogLevel, EventType
from madsci.common.utils import new_ulid_str

_EVENT_ID = new_ulid_str()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    event_id: str | None = None,
    log_level: EventLogLevel = EventLogLevel.INFO,
    event_type: EventType = EventType.UNKNOWN,
    event_data: object | None = None,
) -> Event:
    """Build a minimal Event for testing."""
    return Event(
        event_id=event_id or _EVENT_ID,
        log_level=log_level,
        event_type=event_type,
        event_data=event_data or {"message": "test event"},
        event_timestamp=datetime(2026, 1, 1, 12, 0, 0),
    )


def _patch_event_client(method_name: str, return_value):
    """Shortcut to patch an EventClient method."""
    return patch(
        f"madsci.client.event_client.EventClient.{method_name}",
        return_value=return_value,
    )


def _patch_event_client_init():
    """Patch EventClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.event_client.EventClient.__init__",
        return_value=None,
    )


# ---------------------------------------------------------------------------
# events group help
# ---------------------------------------------------------------------------


class TestEventsGroup:
    """Tests for the events command group itself."""

    def test_events_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["events", "--help"])
        assert result.exit_code == 0
        assert "Manage events" in result.output

    def test_events_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["ev", "--help"])
        assert result.exit_code == 0
        assert "Manage events" in result.output


# ---------------------------------------------------------------------------
# events query
# ---------------------------------------------------------------------------


class TestEventsQuery:
    """Tests for 'events query'."""

    def test_query_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["events", "query", "--help"])
        assert result.exit_code == 0
        assert "--selector" in result.output
        assert "--count" in result.output
        assert "--level" in result.output

    def test_query_default(self) -> None:
        events = OrderedDict({_EVENT_ID: _make_event()})
        with (
            _patch_event_client_init(),
            _patch_event_client("get_events", events),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "events",
                    "query",
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0

    def test_query_json(self) -> None:
        events = OrderedDict({_EVENT_ID: _make_event()})
        with (
            _patch_event_client_init(),
            _patch_event_client("get_events", events),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "events",
                    "query",
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0

    def test_query_empty(self) -> None:
        with (
            _patch_event_client_init(),
            _patch_event_client("get_events", OrderedDict()),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "events",
                    "query",
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0
            assert "No events found" in result.output

    def test_query_with_selector(self) -> None:
        events = OrderedDict({_EVENT_ID: _make_event()})
        with (
            _patch_event_client_init(),
            _patch_event_client("query_events", events),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "events",
                    "query",
                    "--selector",
                    '{"event_type": "UNKNOWN"}',
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0

    def test_query_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "query",
                "--selector",
                "not-valid-json",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_query_quiet(self) -> None:
        events = OrderedDict({_EVENT_ID: _make_event()})
        with (
            _patch_event_client_init(),
            _patch_event_client("get_events", events),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "events",
                    "query",
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# events get
# ---------------------------------------------------------------------------


class TestEventsGet:
    """Tests for 'events get'."""

    def test_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["events", "get", "--help"])
        assert result.exit_code == 0

    def test_get_basic(self) -> None:
        event = _make_event()
        with (
            _patch_event_client_init(),
            _patch_event_client("get_event", event),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "events",
                    "get",
                    _EVENT_ID,
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0

    def test_get_not_found(self) -> None:
        with (
            _patch_event_client_init(),
            _patch_event_client("get_event", None),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "events",
                    "get",
                    "NOTFOUND",
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_get_json(self) -> None:
        event = _make_event()
        with (
            _patch_event_client_init(),
            _patch_event_client("get_event", event),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "events",
                    "get",
                    _EVENT_ID,
                    "--event-url",
                    "http://localhost:8001/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# events archive
# ---------------------------------------------------------------------------


class TestEventsArchive:
    """Tests for 'events archive'."""

    def test_archive_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["events", "archive", "--help"])
        assert result.exit_code == 0
        assert "--before-date" in result.output
        assert "--ids" in result.output

    def test_archive_no_args(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "archive",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code != 0
        assert "Provide --before-date or --ids" in result.output

    @patch("httpx.post")
    def test_archive_by_date(self, mock_post) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"archived_count": 5}
        mock_post.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "archive",
                "--before-date",
                "2026-01-01",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code == 0
        assert "5" in result.output

    @patch("httpx.post")
    def test_archive_by_ids(self, mock_post) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"archived_count": 2}
        mock_post.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "archive",
                "--ids",
                "id1,id2",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code == 0
        assert "2" in result.output


# ---------------------------------------------------------------------------
# events purge
# ---------------------------------------------------------------------------


class TestEventsPurge:
    """Tests for 'events purge'."""

    def test_purge_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["events", "purge", "--help"])
        assert result.exit_code == 0
        assert "--older-than-days" in result.output
        assert "--yes" in result.output

    @patch("httpx.delete")
    def test_purge_with_yes(self, mock_delete) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"purged_count": 10}
        mock_delete.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "purge",
                "--yes",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code == 0
        assert "10" in result.output

    def test_purge_abort(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "purge",
                "--event-url",
                "http://localhost:8001/",
            ],
            input="n\n",
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# events backup
# ---------------------------------------------------------------------------


class TestEventsBackup:
    """Tests for 'events backup'."""

    def test_backup_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["events", "backup", "--help"])
        assert result.exit_code == 0
        assert "--create" in result.output
        assert "--status" in result.output

    def test_backup_no_args(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "backup",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code != 0
        assert "Provide --create or --status" in result.output

    @patch("httpx.post")
    def test_backup_create(self, mock_post) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"backup_id": "bk-123", "status": "created"}
        mock_post.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "backup",
                "--create",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    @patch("httpx.get")
    def test_backup_status(self, mock_get) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"last_backup": "2026-01-01", "count": 5}
        mock_get.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "events",
                "backup",
                "--status",
                "--event-url",
                "http://localhost:8001/",
            ],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------


class TestEventsRegistered:
    """Test that the events command is properly registered."""

    def test_events_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "events" in _LAZY_COMMANDS

    def test_ev_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "ev" in AliasedGroup._aliases
        assert AliasedGroup._aliases["ev"] == "events"
