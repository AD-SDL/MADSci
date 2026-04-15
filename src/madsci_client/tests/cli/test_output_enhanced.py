"""Tests for enhanced output.py features (OutputFormat, ColumnDef, determine_output_format)."""

from __future__ import annotations

from io import StringIO
from typing import Any

import click
from madsci.client.cli.utils.output import (
    ColumnDef,
    OutputFormat,
    determine_output_format,
    output_result,
)
from pydantic import BaseModel
from rich.console import Console

# ---------------------------------------------------------------------------
# OutputFormat enum
# ---------------------------------------------------------------------------


class TestOutputFormat:
    """Tests for the OutputFormat enum."""

    def test_values(self) -> None:
        assert OutputFormat.TABLE == "table"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.YAML == "yaml"
        assert OutputFormat.QUIET == "quiet"

    def test_is_string(self) -> None:
        assert isinstance(OutputFormat.TABLE, str)


# ---------------------------------------------------------------------------
# ColumnDef
# ---------------------------------------------------------------------------


class TestColumnDef:
    """Tests for the ColumnDef named tuple."""

    def test_basic_construction(self) -> None:
        col = ColumnDef(header="Name", key="name")
        assert col.header == "Name"
        assert col.key == "name"
        assert col.style is None
        assert col.max_width is None

    def test_with_style(self) -> None:
        col = ColumnDef(header="Status", key="status", style="green", max_width=20)
        assert col.style == "green"
        assert col.max_width == 20


# ---------------------------------------------------------------------------
# determine_output_format
# ---------------------------------------------------------------------------


class TestDetermineOutputFormat:
    """Tests for determine_output_format()."""

    def _make_ctx(self, **flags: Any) -> click.Context:
        ctx = click.Context(click.Command("test"))
        ctx.ensure_object(dict)
        ctx.obj.update(flags)
        return ctx

    def test_default_is_table(self) -> None:
        ctx = self._make_ctx()
        assert determine_output_format(ctx) == OutputFormat.TABLE

    def test_json_flag(self) -> None:
        ctx = self._make_ctx(json=True)
        assert determine_output_format(ctx) == OutputFormat.JSON

    def test_yaml_flag(self) -> None:
        ctx = self._make_ctx(yaml=True)
        assert determine_output_format(ctx) == OutputFormat.YAML

    def test_quiet_flag(self) -> None:
        ctx = self._make_ctx(quiet=True)
        assert determine_output_format(ctx) == OutputFormat.QUIET

    def test_json_takes_precedence(self) -> None:
        ctx = self._make_ctx(json=True, yaml=True, quiet=True)
        assert determine_output_format(ctx) == OutputFormat.JSON

    def test_yaml_over_quiet(self) -> None:
        ctx = self._make_ctx(yaml=True, quiet=True)
        assert determine_output_format(ctx) == OutputFormat.YAML

    def test_no_obj(self) -> None:
        ctx = click.Context(click.Command("test"))
        ctx.obj = None
        assert determine_output_format(ctx) == OutputFormat.TABLE


# ---------------------------------------------------------------------------
# Enhanced output_result
# ---------------------------------------------------------------------------


def _capture_console() -> Console:
    """Create a Console that writes to an in-memory buffer."""
    return Console(file=StringIO(), force_terminal=True, width=120)


def _get_output(console: Console) -> str:
    """Extract the string captured by the in-memory console."""
    console.file.seek(0)
    return console.file.read()


class SampleModel(BaseModel):
    """A minimal Pydantic model for testing."""

    name: str = "test"
    value: int = 42


class TestOutputResultEnhanced:
    """Tests for the enhanced output_result function."""

    def test_json_mode_with_pydantic_model(self) -> None:
        console = _capture_console()
        output_result(console, SampleModel(), format="json")
        text = _get_output(console)
        assert "test" in text
        assert "42" in text

    def test_yaml_mode_with_pydantic_model(self) -> None:
        console = _capture_console()
        output_result(console, SampleModel(), format="yaml")
        text = _get_output(console)
        assert "name:" in text or "name :" in text

    def test_quiet_mode_with_key(self) -> None:
        console = _capture_console()
        output_result(
            console,
            {"id": "abc123", "name": "test"},
            format="quiet",
            quiet_key="id",
        )
        text = _get_output(console)
        assert "abc123" in text

    def test_quiet_mode_with_list(self) -> None:
        console = _capture_console()
        data = [{"id": "a"}, {"id": "b"}]
        output_result(console, data, format="quiet", quiet_key="id")
        text = _get_output(console)
        assert "a" in text
        assert "b" in text

    def test_table_mode_with_columns(self) -> None:
        console = _capture_console()
        columns = [
            ColumnDef(header="Name", key="name"),
            ColumnDef(header="Value", key="value", style="cyan"),
        ]
        data = [{"name": "alpha", "value": "1"}, {"name": "beta", "value": "2"}]
        output_result(console, data, format="text", columns=columns)
        text = _get_output(console)
        assert "Name" in text
        assert "alpha" in text
        assert "beta" in text

    def test_pydantic_model_table_mode(self) -> None:
        console = _capture_console()
        output_result(console, SampleModel(), format="text")
        text = _get_output(console)
        assert "name" in text
        assert "test" in text

    def test_list_of_pydantic_models_with_columns(self) -> None:
        console = _capture_console()
        columns = [
            ColumnDef(header="Name", key="name"),
            ColumnDef(header="Value", key="value"),
        ]
        data = [SampleModel(name="x", value=1), SampleModel(name="y", value=2)]
        output_result(console, data, format="text", columns=columns)
        text = _get_output(console)
        assert "x" in text
        assert "y" in text

    def test_dict_as_key_value_table(self) -> None:
        console = _capture_console()
        output_result(console, {"foo": "bar"}, format="text")
        text = _get_output(console)
        assert "foo" in text
        assert "bar" in text

    def test_plain_list_bullet_points(self) -> None:
        console = _capture_console()
        output_result(console, ["item1", "item2"], format="text")
        text = _get_output(console)
        assert "item1" in text

    def test_scalar_fallback(self) -> None:
        console = _capture_console()
        output_result(console, "just a string", format="text")
        text = _get_output(console)
        assert "just a string" in text

    def test_json_mode_with_list_of_models(self) -> None:
        console = _capture_console()
        data = [SampleModel(name="a", value=1), SampleModel(name="b", value=2)]
        output_result(console, data, format="json")
        text = _get_output(console)
        assert '"a"' in text
        assert '"b"' in text

    def test_quiet_mode_with_model(self) -> None:
        console = _capture_console()
        output_result(console, SampleModel(), format="quiet", quiet_key="name")
        text = _get_output(console)
        assert "test" in text

    def test_quiet_mode_no_key(self) -> None:
        console = _capture_console()
        output_result(console, {"a": 1}, format="quiet")
        text = _get_output(console)
        # Should print the whole dict as string
        assert "a" in text
