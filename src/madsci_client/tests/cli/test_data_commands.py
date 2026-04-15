"""Tests for the madsci data command group."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.utils import new_ulid_str

_DP_ID = new_ulid_str()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_datapoint(
    *,
    datapoint_id: str | None = None,
    data_type: str = "value",
    label: str | None = "test-label",
    value: object = {"key": "val"},
) -> MagicMock:
    """Build a mock DataPoint for testing."""
    dp = MagicMock()
    dp.datapoint_id = datapoint_id or _DP_ID
    dp.data_type = data_type
    dp.label = label
    dp.data_timestamp = "2026-01-01T12:00:00"
    dp.size_bytes = 42
    dp.value = value
    return dp


def _patch_client(method_name: str, return_value):
    """Shortcut to patch a DataClient method."""
    return patch(
        f"madsci.client.data_client.DataClient.{method_name}",
        return_value=return_value,
    )


def _patch_client_init():
    """Patch DataClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.data_client.DataClient.__init__",
        return_value=None,
    )


# ---------------------------------------------------------------------------
# data group help
# ---------------------------------------------------------------------------


class TestDataGroup:
    """Tests for the data command group itself."""

    def test_data_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["data", "--help"])
        assert result.exit_code == 0
        assert "Manage datapoints" in result.output

    def test_data_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["dt", "--help"])
        assert result.exit_code == 0
        assert "Manage datapoints" in result.output


# ---------------------------------------------------------------------------
# data list
# ---------------------------------------------------------------------------


class TestDataList:
    """Tests for 'data list'."""

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["data", "list", "--help"])
        assert result.exit_code == 0
        assert "--count" in result.output

    def test_list_default(self) -> None:
        dps = [_make_datapoint()]
        with _patch_client_init(), _patch_client("get_datapoints", dps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["data", "list", "--data-url", "http://localhost:8004/"],
            )
            assert result.exit_code == 0
            assert "test-label" in result.output

    def test_list_json(self) -> None:
        dps = [_make_datapoint()]
        with _patch_client_init(), _patch_client("get_datapoints", dps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "data",
                    "list",
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0

    def test_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_datapoints", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["data", "list", "--data-url", "http://localhost:8004/"],
            )
            assert result.exit_code == 0
            assert "No datapoints found" in result.output

    def test_list_quiet(self) -> None:
        dps = [_make_datapoint()]
        with _patch_client_init(), _patch_client("get_datapoints", dps):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "data",
                    "list",
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# data get
# ---------------------------------------------------------------------------


class TestDataGet:
    """Tests for 'data get'."""

    def test_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["data", "get", "--help"])
        assert result.exit_code == 0
        assert "--save-to" in result.output

    def test_get_value(self) -> None:
        with (
            _patch_client_init(),
            _patch_client("get_datapoint_value", {"temperature": 25.3}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "get",
                    _DP_ID,
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0

    def test_get_save_to(self, tmp_path) -> None:
        output_file = tmp_path / "output.json"
        with (
            _patch_client_init(),
            _patch_client("save_datapoint_value", None),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "get",
                    _DP_ID,
                    "--save-to",
                    str(output_file),
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0
            assert "saved" in result.output.lower()


# ---------------------------------------------------------------------------
# data metadata
# ---------------------------------------------------------------------------


class TestDataMetadata:
    """Tests for 'data metadata'."""

    def test_metadata_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["data", "metadata", "--help"])
        assert result.exit_code == 0

    def test_metadata_basic(self) -> None:
        mock_meta = {
            "datapoint_id": _DP_ID,
            "label": "test",
            "data_type": "value",
            "data_timestamp": "2026-01-01T12:00:00",
        }
        with (
            _patch_client_init(),
            _patch_client("get_datapoint_metadata", mock_meta),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "metadata",
                    _DP_ID,
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0

    def test_metadata_json(self) -> None:
        mock_meta = {
            "datapoint_id": _DP_ID,
            "label": "test",
            "data_type": "value",
        }
        with (
            _patch_client_init(),
            _patch_client("get_datapoint_metadata", mock_meta),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "data",
                    "metadata",
                    _DP_ID,
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# data submit
# ---------------------------------------------------------------------------


class TestDataSubmit:
    """Tests for 'data submit'."""

    def test_submit_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["data", "submit", "--help"])
        assert result.exit_code == 0
        assert "--file" in result.output
        assert "--value" in result.output

    def test_submit_value(self) -> None:
        dp = _make_datapoint()
        with _patch_client_init(), _patch_client("submit_datapoint", dp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "submit",
                    "--value",
                    '{"temperature": 25.3}',
                    "--label",
                    "sensor",
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0
            assert "submitted" in result.output.lower()

    def test_submit_file(self, tmp_path) -> None:
        test_file = tmp_path / "data.csv"
        test_file.write_text("col1,col2\n1,2\n")

        dp = _make_datapoint(data_type="file")
        with _patch_client_init(), _patch_client("submit_datapoint", dp):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "submit",
                    "--file",
                    str(test_file),
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0
            assert "submitted" in result.output.lower()

    def test_submit_mutually_exclusive(self, tmp_path) -> None:
        test_file = tmp_path / "data.csv"
        test_file.write_text("col1\n1\n")

        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "data",
                "submit",
                "--file",
                str(test_file),
                "--value",
                '{"a": 1}',
                "--data-url",
                "http://localhost:8004/",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_submit_no_args(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["data", "submit", "--data-url", "http://localhost:8004/"],
        )
        assert result.exit_code != 0

    def test_submit_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "data",
                "submit",
                "--value",
                "not-valid-json",
                "--data-url",
                "http://localhost:8004/",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output


# ---------------------------------------------------------------------------
# data query
# ---------------------------------------------------------------------------


class TestDataQuery:
    """Tests for 'data query'."""

    def test_query_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["data", "query", "--help"])
        assert result.exit_code == 0
        assert "--selector" in result.output

    def test_query_basic(self) -> None:
        dp = _make_datapoint()
        with (
            _patch_client_init(),
            _patch_client("query_datapoints", {"dp1": dp}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "query",
                    "--selector",
                    '{"label": "test"}',
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0

    def test_query_empty(self) -> None:
        with _patch_client_init(), _patch_client("query_datapoints", {}):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "data",
                    "query",
                    "--selector",
                    '{"label": "nonexistent"}',
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0
            assert "No datapoints matched" in result.output

    def test_query_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "data",
                "query",
                "--selector",
                "not-valid-json",
                "--data-url",
                "http://localhost:8004/",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_query_json_output(self) -> None:
        dp = _make_datapoint()
        with (
            _patch_client_init(),
            _patch_client("query_datapoints", {"dp1": dp}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "data",
                    "query",
                    "--selector",
                    '{"label": "test"}',
                    "--data-url",
                    "http://localhost:8004/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------


class TestDataRegistered:
    """Test that the data command is properly registered."""

    def test_data_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "data" in _LAZY_COMMANDS

    def test_dt_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "dt" in AliasedGroup._aliases
        assert AliasedGroup._aliases["dt"] == "data"
