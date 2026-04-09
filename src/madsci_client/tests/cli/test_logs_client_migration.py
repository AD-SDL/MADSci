"""Tests for the logs client migration from raw httpx to EventClient.

Verifies that both the CLI logs command and TUI logs screen use EventClient
instead of raw httpx for fetching events.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from madsci.common.types.event_types import Event, EventLogLevel, EventType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_id: str = "evt-001",
    log_level: EventLogLevel = EventLogLevel.INFO,
    message: str = "test message",
    event_type: EventType = EventType.LOG,
) -> Event:
    """Create a minimal Event model for testing."""
    return Event(
        event_id=event_id,
        log_level=log_level,
        event_type=event_type,
        event_data={"message": message},
        event_timestamp=datetime(2026, 1, 15, 12, 0, 0),
    )


def _make_events_dict(*events: Event) -> dict[str, Event]:
    """Build the dict[str, Event] return type that EventClient.get_events returns."""
    return OrderedDict((e.event_id, e) for e in events)


# ===========================================================================
# CLI logs command tests
# ===========================================================================


class TestFetchLogsUsesEventClient:
    """Verify fetch_logs_from_event_manager uses EventClient instead of httpx."""

    def test_no_httpx_import_in_fetch_function(self) -> None:
        """The fetch_logs_from_event_manager function should not import httpx."""
        import inspect

        from madsci.client.cli.commands.logs import fetch_logs_from_event_manager

        source = inspect.getsource(fetch_logs_from_event_manager)
        assert "httpx" not in source, (
            "fetch_logs_from_event_manager still references httpx"
        )

    def test_fetch_creates_event_client(self) -> None:
        """fetch_logs_from_event_manager should create an EventClient."""
        events = _make_events_dict(
            _make_event("e1", message="hello"),
            _make_event("e2", message="world"),
        )

        mock_client_instance = MagicMock()
        mock_client_instance.get_events.return_value = events

        with patch(
            "madsci.client.cli.commands.logs.EventClient",
            return_value=mock_client_instance,
        ) as mock_cls:
            from madsci.client.cli.commands.logs import fetch_logs_from_event_manager

            result = fetch_logs_from_event_manager(
                base_url="http://localhost:8001/",
                limit=10,
            )

        mock_cls.assert_called_once()
        mock_client_instance.get_events.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_fetch_returns_list_of_dicts(self) -> None:
        """The function should convert Event models to dicts for display logic."""
        events = _make_events_dict(
            _make_event("e1", message="one"),
        )

        mock_client_instance = MagicMock()
        mock_client_instance.get_events.return_value = events

        with patch(
            "madsci.client.cli.commands.logs.EventClient",
            return_value=mock_client_instance,
        ):
            from madsci.client.cli.commands.logs import fetch_logs_from_event_manager

            result = fetch_logs_from_event_manager(
                base_url="http://localhost:8001/",
                limit=5,
            )

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        # Should have event_id key from model_dump
        assert result[0]["event_id"] == "e1"

    def test_fetch_passes_number_to_get_events(self) -> None:
        """The limit parameter should be passed as number= to get_events."""
        mock_client_instance = MagicMock()
        mock_client_instance.get_events.return_value = {}

        with patch(
            "madsci.client.cli.commands.logs.EventClient",
            return_value=mock_client_instance,
        ):
            from madsci.client.cli.commands.logs import fetch_logs_from_event_manager

            fetch_logs_from_event_manager(
                base_url="http://localhost:8001/",
                limit=25,
            )

        call_kwargs = mock_client_instance.get_events.call_args
        assert call_kwargs.kwargs.get("number") == 25 or (
            call_kwargs.args and call_kwargs.args[0] == 25
        )

    def test_fetch_handles_connection_error(self) -> None:
        """Should return empty list on connection error, not raise."""
        mock_client_instance = MagicMock()
        mock_client_instance.get_events.side_effect = Exception("Connection refused")

        with patch(
            "madsci.client.cli.commands.logs.EventClient",
            return_value=mock_client_instance,
        ):
            from madsci.client.cli.commands.logs import fetch_logs_from_event_manager

            result = fetch_logs_from_event_manager(
                base_url="http://localhost:8001/",
            )

        assert result == []


class TestCliLogsNoHttpxModule:
    """Verify the logs module itself does not import httpx at module level."""

    def test_no_httpx_at_module_level(self) -> None:
        """The logs.py CLI module should not import httpx at all."""
        import inspect

        import madsci.client.cli.commands.logs as logs_module

        source = inspect.getsource(logs_module)
        # Check there is no `import httpx` statement anywhere in the source
        assert not re.search(r"^\s*import\s+httpx", source, re.MULTILINE), (
            "logs.py CLI module still has 'import httpx'"
        )
        assert not re.search(r"from\s+httpx\s+import", source, re.MULTILINE), (
            "logs.py CLI module still has 'from httpx import'"
        )


# ===========================================================================
# TUI logs screen tests
# ===========================================================================


class TestTuiLogsUsesEventClient:
    """Verify the TUI LogsScreen._fetch_logs uses EventClient instead of httpx."""

    def test_no_httpx_import_in_tui_logs(self) -> None:
        """The TUI logs module should not import httpx."""
        import inspect

        import madsci.client.cli.tui.screens.logs as tui_logs_module

        source = inspect.getsource(tui_logs_module)
        assert not re.search(r"^\s*import\s+httpx", source, re.MULTILINE), (
            "TUI logs module still has 'import httpx'"
        )
        assert not re.search(r"from\s+httpx\s+import", source, re.MULTILINE), (
            "TUI logs module still has 'from httpx import'"
        )

    def test_logs_screen_has_event_client_attribute(self) -> None:
        """LogsScreen should have a lazy _event_client attribute."""
        from madsci.client.cli.tui.screens.logs import LogsScreen

        screen = LogsScreen()
        assert hasattr(screen, "_event_client")
        assert screen._event_client is None

    def test_logs_screen_has_get_event_client_method(self) -> None:
        """LogsScreen should have a _get_event_client method."""
        from madsci.client.cli.tui.screens.logs import LogsScreen

        screen = LogsScreen()
        assert hasattr(screen, "_get_event_client")
        assert callable(screen._get_event_client)


class TestTuiLogsLevelMapping:
    """Test the level string-to-int mapping used in the TUI logs screen."""

    def test_level_string_to_int_mapping_exists(self) -> None:
        """The TUI logs module should have a LEVEL_NAME_TO_INT mapping or equivalent."""
        from madsci.client.cli.tui.screens.logs import _level_name_to_int

        assert _level_name_to_int("debug") == 10
        assert _level_name_to_int("info") == 20
        assert _level_name_to_int("warning") == 30
        assert _level_name_to_int("error") == 40
        assert _level_name_to_int("critical") == 50
        # "all" or None should return -1 (no filter)
        assert _level_name_to_int(None) == -1
        assert _level_name_to_int("all") == -1

    def test_level_mapping_case_insensitive(self) -> None:
        """Level mapping should be case-insensitive."""
        from madsci.client.cli.tui.screens.logs import _level_name_to_int

        assert _level_name_to_int("DEBUG") == 10
        assert _level_name_to_int("Info") == 20
        assert _level_name_to_int("WARNING") == 30


class TestTuiLogsFetchIntegration:
    """Test the _fetch_logs method uses EventClient correctly."""

    @pytest.mark.asyncio
    async def test_fetch_logs_calls_async_get_events(self) -> None:
        """_fetch_logs should call async_get_events on EventClient."""
        from madsci.client.cli.tui.screens.logs import LogsScreen

        events = _make_events_dict(
            _make_event("e1", message="hello"),
        )

        mock_client = MagicMock()
        mock_client.async_get_events = AsyncMock(return_value=events)

        screen = LogsScreen()
        screen._event_client = mock_client
        # Mock get_service_url so it doesn't fail
        screen.get_service_url = MagicMock(return_value="http://localhost:8001/")

        await screen._fetch_logs(limit=10, level="info")

        mock_client.async_get_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_logs_returns_list_of_dicts(self) -> None:
        """_fetch_logs should return list[dict] for LogViewer.append_entries."""
        from madsci.client.cli.tui.screens.logs import LogsScreen

        events = _make_events_dict(
            _make_event("e1", message="hello"),
            _make_event("e2", message="world"),
        )

        mock_client = MagicMock()
        mock_client.async_get_events = AsyncMock(return_value=events)

        screen = LogsScreen()
        screen._event_client = mock_client
        screen.get_service_url = MagicMock(return_value="http://localhost:8001/")

        result = await screen._fetch_logs(limit=10)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    @pytest.mark.asyncio
    async def test_fetch_logs_applies_search_filter_client_side(self) -> None:
        """_fetch_logs should filter by search string on the client side."""
        from madsci.client.cli.tui.screens.logs import LogsScreen

        events = _make_events_dict(
            _make_event("e1", message="workflow started"),
            _make_event("e2", message="error occurred"),
            _make_event("e3", message="workflow completed"),
        )

        mock_client = MagicMock()
        mock_client.async_get_events = AsyncMock(return_value=events)

        screen = LogsScreen()
        screen._event_client = mock_client
        screen.get_service_url = MagicMock(return_value="http://localhost:8001/")

        result = await screen._fetch_logs(limit=10, search="workflow")

        # Should only return events whose message contains "workflow"
        assert len(result) == 2
        messages = [entry.get("event_data", {}).get("message", "") for entry in result]
        assert all("workflow" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_fetch_logs_returns_empty_on_error(self) -> None:
        """_fetch_logs should return empty list on error, not raise."""
        from madsci.client.cli.tui.screens.logs import LogsScreen

        mock_client = MagicMock()
        mock_client.async_get_events = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        screen = LogsScreen()
        screen._event_client = mock_client
        screen.get_service_url = MagicMock(return_value="http://localhost:8001/")

        result = await screen._fetch_logs(limit=10)

        assert result == []
