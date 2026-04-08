"""Tests for madsci.client.cli.utils.formatting."""

from __future__ import annotations

from datetime import datetime, timezone

from madsci.client.cli.utils.formatting import (
    STATUS_STYLES,
    build_ownership_section,
    format_duration,
    format_status_colored,
    format_status_icon,
    format_timestamp,
    get_status_style,
    truncate,
)

# ---------------------------------------------------------------------------
# get_status_style
# ---------------------------------------------------------------------------


class TestGetStatusStyle:
    """Tests for get_status_style()."""

    def test_known_statuses(self) -> None:
        for status in STATUS_STYLES:
            icon, colour = get_status_style(status)
            assert isinstance(icon, str)
            assert isinstance(colour, str)

    def test_case_insensitive(self) -> None:
        assert get_status_style("Healthy") == get_status_style("healthy")
        assert get_status_style("RUNNING") == get_status_style("running")

    def test_strips_whitespace(self) -> None:
        assert get_status_style("  healthy  ") == get_status_style("healthy")

    def test_unknown_status_returns_default(self) -> None:
        icon, colour = get_status_style("totally_made_up")
        assert icon == "\u25cb"
        assert colour == "dim"


# ---------------------------------------------------------------------------
# format_status_icon
# ---------------------------------------------------------------------------


class TestFormatStatusIcon:
    """Tests for format_status_icon()."""

    def test_healthy(self) -> None:
        result = format_status_icon("healthy")
        assert "[green]" in result
        assert "\u25cf" in result

    def test_offline(self) -> None:
        result = format_status_icon("offline")
        assert "[red]" in result

    def test_unknown(self) -> None:
        result = format_status_icon("xyzzy")
        assert "[dim]" in result


# ---------------------------------------------------------------------------
# format_status_colored
# ---------------------------------------------------------------------------


class TestFormatStatusColored:
    """Tests for format_status_colored()."""

    def test_default_text(self) -> None:
        result = format_status_colored("healthy")
        assert "healthy" in result
        assert "[green]" in result

    def test_custom_text(self) -> None:
        result = format_status_colored("failed", text="FAIL")
        assert "FAIL" in result
        assert "failed" not in result
        assert "[red]" in result


# ---------------------------------------------------------------------------
# format_timestamp
# ---------------------------------------------------------------------------


class TestFormatTimestamp:
    """Tests for format_timestamp()."""

    def test_none_returns_dash(self) -> None:
        assert format_timestamp(None) == "-"

    def test_datetime_long(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_timestamp(dt)
        assert "2024-03-15" in result
        assert "14:30:45" in result

    def test_datetime_short(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45, 123000, tzinfo=timezone.utc)
        result = format_timestamp(dt, short=True)
        assert result == "14:30:45.123"

    def test_iso_string(self) -> None:
        result = format_timestamp("2024-03-15T14:30:45Z")
        assert "2024-03-15" in result

    def test_iso_string_short(self) -> None:
        result = format_timestamp("2024-03-15T14:30:45.123000Z", short=True)
        assert result == "14:30:45.123"

    def test_bad_string_long(self) -> None:
        result = format_timestamp("not-a-date")
        assert result == "not-a-date"

    def test_bad_string_short(self) -> None:
        result = format_timestamp("not-a-date-at-all", short=True)
        assert result == "not-a-date-a"  # truncated to 12 chars

    def test_arbitrary_object(self) -> None:
        result = format_timestamp(12345)
        assert result == "12345"


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------


class TestFormatDuration:
    """Tests for format_duration()."""

    def test_none_returns_dash(self) -> None:
        assert format_duration(None) == "-"

    def test_negative_returns_dash(self) -> None:
        assert format_duration(-5.0) == "-"

    def test_zero(self) -> None:
        assert format_duration(0) == "00m 00s"

    def test_seconds_only(self) -> None:
        assert format_duration(42) == "00m 42s"

    def test_minutes_and_seconds(self) -> None:
        assert format_duration(125) == "02m 05s"

    def test_hours(self) -> None:
        result = format_duration(3723)
        assert result == "1h 02m 03s"

    def test_fractional_seconds(self) -> None:
        # Should truncate to integer seconds
        assert format_duration(61.9) == "01m 01s"


# ---------------------------------------------------------------------------
# truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    """Tests for truncate()."""

    def test_short_text_unchanged(self) -> None:
        assert truncate("hello", max_len=50) == "hello"

    def test_exact_length_unchanged(self) -> None:
        text = "a" * 50
        assert truncate(text, max_len=50) == text

    def test_long_text_truncated(self) -> None:
        text = "a" * 60
        result = truncate(text, max_len=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_max_len_3_no_ellipsis(self) -> None:
        result = truncate("abcdef", max_len=3)
        assert result == "abc"

    def test_max_len_2(self) -> None:
        result = truncate("abcdef", max_len=2)
        assert result == "ab"

    def test_empty_string(self) -> None:
        assert truncate("", max_len=10) == ""


# ---------------------------------------------------------------------------
# build_ownership_section
# ---------------------------------------------------------------------------


class TestBuildOwnershipSection:
    """Tests for build_ownership_section()."""

    def test_empty_data_returns_empty_list(self) -> None:
        """Returns [] when ownership_info is absent."""
        assert build_ownership_section({}) == []

    def test_none_ownership_info_returns_empty_list(self) -> None:
        """Returns [] when ownership_info is None."""
        assert build_ownership_section({"ownership_info": None}) == []

    def test_empty_ownership_info_returns_empty_list(self) -> None:
        """Returns [] when ownership_info dict is empty."""
        assert build_ownership_section({"ownership_info": {}}) == []

    def test_returns_user_id_label_tuple(self) -> None:
        """Returns (label, value) tuple for user_id."""
        items = build_ownership_section({"ownership_info": {"user_id": "u-123"}})
        assert len(items) == 1
        label, value = items[0]
        assert label == "User Id"
        assert value == "u-123"

    def test_returns_all_known_ownership_keys(self) -> None:
        """Returns tuples for all populated ownership keys in canonical order."""
        ownership_info = {
            "user_id": "u-1",
            "experiment_id": "e-1",
            "campaign_id": "c-1",
            "workflow_id": "w-1",
            "workflow_run_id": "wr-1",
            "step_id": "s-1",
            "node_id": "n-1",
        }
        items = build_ownership_section({"ownership_info": ownership_info})
        assert len(items) == 7
        labels = [item[0] for item in items]
        assert "User Id" in labels
        assert "Experiment Id" in labels
        assert "Campaign Id" in labels
        assert "Workflow Id" in labels
        assert "Workflow Run Id" in labels
        assert "Step Id" in labels
        assert "Node Id" in labels

    def test_skips_empty_values(self) -> None:
        """Empty string values are not included."""
        items = build_ownership_section(
            {"ownership_info": {"user_id": "u-1", "experiment_id": ""}}
        )
        assert len(items) == 1
        assert items[0][0] == "User Id"

    def test_skips_none_values(self) -> None:
        """None values are not included."""
        items = build_ownership_section(
            {"ownership_info": {"user_id": "u-1", "experiment_id": None}}
        )
        assert len(items) == 1

    def test_values_converted_to_str(self) -> None:
        """Non-string values are coerced to str."""
        items = build_ownership_section({"ownership_info": {"user_id": 42}})
        assert items[0][1] == "42"

    def test_returns_list_of_tuples(self) -> None:
        """Return type is list[tuple[str, str]]."""
        result = build_ownership_section({"ownership_info": {"user_id": "u"}})
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)
        assert len(result[0]) == 2

    def test_dict_conversion_preserves_order(self) -> None:
        """Converting the result to dict preserves entries."""
        items = build_ownership_section(
            {"ownership_info": {"user_id": "u-1", "experiment_id": "e-1"}}
        )
        d = dict(items)
        assert d["User Id"] == "u-1"
        assert d["Experiment Id"] == "e-1"
