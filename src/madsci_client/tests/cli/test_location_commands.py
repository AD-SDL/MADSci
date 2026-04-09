"""Tests for the madsci location command group."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.location_types import (
    Location,
    LocationImportResult,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.utils import new_ulid_str

# Pre-generate stable ULID strings for tests
_LOC_ID_1 = new_ulid_str()
_LOC_ID_2 = new_ulid_str()
_RES_ID_1 = new_ulid_str()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_location(
    *,
    location_id: str | None = None,
    location_name: str = "test_location",
    resource_id: str | None = None,
    allow_transfers: bool = True,
    location_template_name: str | None = None,
    description: str | None = None,
) -> Location:
    """Build a minimal Location for testing."""
    if location_id is None:
        location_id = _LOC_ID_1
    return Location(
        location_id=location_id,
        location_name=location_name,
        resource_id=resource_id,
        allow_transfers=allow_transfers,
        location_template_name=location_template_name,
        description=description,
    )


def _make_location_template(
    *,
    template_name: str = "test_template",
    description: str | None = "A test template",
    version: str = "1.0.0",
) -> LocationTemplate:
    """Build a minimal LocationTemplate for testing."""
    return LocationTemplate(
        template_name=template_name,
        description=description,
        version=version,
    )


def _make_repr_template(
    *,
    template_name: str = "test_repr_template",
    description: str | None = "A test repr template",
    version: str = "1.0.0",
    created_by: str | None = "test_node",
) -> LocationRepresentationTemplate:
    """Build a minimal LocationRepresentationTemplate for testing."""
    return LocationRepresentationTemplate(
        template_name=template_name,
        description=description,
        version=version,
        created_by=created_by,
    )


def _patch_client(method_name: str, return_value):
    """Shortcut to patch a LocationClient method."""
    return patch(
        f"madsci.client.location_client.LocationClient.{method_name}",
        return_value=return_value,
    )


def _patch_client_init():
    """Patch LocationClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.location_client.LocationClient.__init__",
        return_value=None,
    )


_URL_ARGS = ["--location-url", "http://localhost:8006/"]


# ---------------------------------------------------------------------------
# location group help
# ---------------------------------------------------------------------------


class TestLocationGroup:
    """Tests for the location command group itself."""

    def test_location_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "--help"])
        assert result.exit_code == 0
        assert "Manage locations" in result.output

    def test_location_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["loc", "--help"])
        assert result.exit_code == 0
        assert "Manage locations" in result.output


# ---------------------------------------------------------------------------
# location list
# ---------------------------------------------------------------------------


class TestLocationList:
    """Tests for 'location list'."""

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "list", "--help"])
        assert result.exit_code == 0

    def test_list_default(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_locations", [loc]):
            runner = CliRunner(env={"COLUMNS": "200"})
            result = runner.invoke(madsci, ["location", "list", *_URL_ARGS])
            assert result.exit_code == 0
            assert "test_loca" in result.output

    def test_list_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_locations", [loc]):
            runner = CliRunner()
            result = runner.invoke(madsci, ["--json", "location", "list", *_URL_ARGS])
            assert result.exit_code == 0

    def test_list_quiet(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_locations", [loc]):
            runner = CliRunner()
            result = runner.invoke(madsci, ["--quiet", "location", "list", *_URL_ARGS])
            assert result.exit_code == 0

    def test_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_locations", []):
            runner = CliRunner()
            result = runner.invoke(madsci, ["location", "list", *_URL_ARGS])
            assert result.exit_code == 0
            assert "No locations found" in result.output


# ---------------------------------------------------------------------------
# location get
# ---------------------------------------------------------------------------


class TestLocationGet:
    """Tests for 'location get'."""

    def test_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "get", "--help"])
        assert result.exit_code == 0

    def test_get_basic(self) -> None:
        loc = _make_location(description="My slot")
        with _patch_client_init(), _patch_client("get_location_by_name", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "get", "test_location", *_URL_ARGS]
            )
            assert result.exit_code == 0
            assert "test_location" in result.output

    def test_get_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_location_by_name", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--json", "location", "get", "test_location", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_get_quiet(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_location_by_name", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--quiet", "location", "get", "test_location", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_get_not_found(self) -> None:
        with _patch_client_init(), _patch_client("get_location_by_name", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "get", "nonexistent", *_URL_ARGS]
            )
            assert result.exit_code != 0
            assert "not found" in result.output


# ---------------------------------------------------------------------------
# location create
# ---------------------------------------------------------------------------


class TestLocationCreate:
    """Tests for 'location create'."""

    def test_create_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "create", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output

    def test_create_basic(self) -> None:
        loc = _make_location(location_name="new_slot")
        with _patch_client_init(), _patch_client("add_location", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "create", "--name", "new_slot", *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "created" in result.output.lower()

    def test_create_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("add_location", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "location", "create", "--name", "new_slot", *_URL_ARGS],
            )
            assert result.exit_code == 0

    def test_create_quiet(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("add_location", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--quiet", "location", "create", "--name", "new_slot", *_URL_ARGS],
            )
            assert result.exit_code == 0

    def test_create_missing_name(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "create", *_URL_ARGS])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# location create-from-template
# ---------------------------------------------------------------------------


class TestLocationCreateFromTemplate:
    """Tests for 'location create-from-template'."""

    def test_create_from_template_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "create-from-template", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--bindings" in result.output

    def test_create_from_template_basic(self) -> None:
        loc = _make_location(location_name="slot_1", location_template_name="ot2_deck")
        with (
            _patch_client_init(),
            _patch_client("create_location_from_template", loc),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "location",
                    "create-from-template",
                    "ot2_deck",
                    "--name",
                    "slot_1",
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0
            assert "created" in result.output.lower()

    def test_create_from_template_with_bindings(self) -> None:
        loc = _make_location(location_name="slot_1")
        with (
            _patch_client_init(),
            _patch_client("create_location_from_template", loc),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "location",
                    "create-from-template",
                    "ot2_deck",
                    "--name",
                    "slot_1",
                    "--bindings",
                    '{"controller": "ot2_node"}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0

    def test_create_from_template_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "location",
                "create-from-template",
                "ot2_deck",
                "--name",
                "slot_1",
                "--bindings",
                "not-json",
                *_URL_ARGS,
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_create_from_template_json(self) -> None:
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("create_location_from_template", loc),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "create-from-template",
                    "ot2_deck",
                    "--name",
                    "slot_1",
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location delete
# ---------------------------------------------------------------------------


class TestLocationDelete:
    """Tests for 'location delete'."""

    def test_delete_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "delete", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_delete_with_yes(self) -> None:
        with (
            _patch_client_init(),
            _patch_client("delete_location", {"status": "deleted"}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "delete", "test_location", "--yes", *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "deleted" in result.output.lower()

    def test_delete_abort(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["location", "delete", "test_location", *_URL_ARGS],
            input="n\n",
        )
        assert result.exit_code != 0

    def test_delete_confirm(self) -> None:
        with (
            _patch_client_init(),
            _patch_client("delete_location", {"status": "deleted"}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "delete", "test_location", *_URL_ARGS],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "deleted" in result.output.lower()

    def test_delete_json(self) -> None:
        with (
            _patch_client_init(),
            _patch_client("delete_location", {"status": "deleted"}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "location", "delete", "test_location", "--yes", *_URL_ARGS],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location resources
# ---------------------------------------------------------------------------


class TestLocationResources:
    """Tests for 'location resources'."""

    def test_resources_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "resources", "--help"])
        assert result.exit_code == 0

    def test_resources_basic(self) -> None:
        hierarchy = ResourceHierarchy(
            resource_id=_RES_ID_1,
            ancestor_ids=[],
            descendant_ids={_RES_ID_1: [new_ulid_str()]},
        )
        with _patch_client_init(), _patch_client("get_location_resources", hierarchy):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "resources", "test_location", *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "Resources" in result.output

    def test_resources_empty(self) -> None:
        hierarchy = ResourceHierarchy(
            resource_id="",
            ancestor_ids=[],
            descendant_ids={},
        )
        with _patch_client_init(), _patch_client("get_location_resources", hierarchy):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "resources", "test_location", *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "No resources" in result.output

    def test_resources_json(self) -> None:
        hierarchy = ResourceHierarchy(
            resource_id=_RES_ID_1,
            ancestor_ids=[],
            descendant_ids={},
        )
        with _patch_client_init(), _patch_client("get_location_resources", hierarchy):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "location", "resources", "test_location", *_URL_ARGS],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location attach
# ---------------------------------------------------------------------------


class TestLocationAttach:
    """Tests for 'location attach'."""

    def test_attach_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "attach", "--help"])
        assert result.exit_code == 0

    def test_attach_basic(self) -> None:
        loc = _make_location(resource_id=_RES_ID_1)
        with _patch_client_init(), _patch_client("attach_resource", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "attach", "test_location", _RES_ID_1, *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "attached" in result.output.lower()

    def test_attach_json(self) -> None:
        loc = _make_location(resource_id=_RES_ID_1)
        with _patch_client_init(), _patch_client("attach_resource", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "attach",
                    "test_location",
                    _RES_ID_1,
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location detach
# ---------------------------------------------------------------------------


class TestLocationDetach:
    """Tests for 'location detach'."""

    def test_detach_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "detach", "--help"])
        assert result.exit_code == 0

    def test_detach_basic(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("detach_resource", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "detach", "test_location", *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "detached" in result.output.lower()

    def test_detach_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("detach_resource", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "location", "detach", "test_location", *_URL_ARGS],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location set-repr
# ---------------------------------------------------------------------------


class TestLocationSetRepr:
    """Tests for 'location set-repr'."""

    def test_set_repr_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "set-repr", "--help"])
        assert result.exit_code == 0
        assert "--data" in result.output

    def test_set_repr_basic(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("set_representation", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "location",
                    "set-repr",
                    "test_location",
                    "robot_arm",
                    "--data",
                    '{"x": 1, "y": 2}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0
            assert "set" in result.output.lower()

    def test_set_repr_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "location",
                "set-repr",
                "test_location",
                "robot_arm",
                "--data",
                "not-json",
                *_URL_ARGS,
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_set_repr_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("set_representation", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "set-repr",
                    "test_location",
                    "robot_arm",
                    "--data",
                    '{"x": 1}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location remove-repr
# ---------------------------------------------------------------------------


class TestLocationRemoveRepr:
    """Tests for 'location remove-repr'."""

    def test_remove_repr_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "remove-repr", "--help"])
        assert result.exit_code == 0

    def test_remove_repr_basic(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("remove_representation", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "remove-repr", "test_location", "robot_arm", *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "removed" in result.output.lower()

    def test_remove_repr_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("remove_representation", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "remove-repr",
                    "test_location",
                    "robot_arm",
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location transfer-graph
# ---------------------------------------------------------------------------


class TestLocationTransferGraph:
    """Tests for 'location transfer-graph'."""

    def test_transfer_graph_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "transfer-graph", "--help"])
        assert result.exit_code == 0

    def test_transfer_graph_basic(self) -> None:
        graph = {_LOC_ID_1: [_LOC_ID_2]}
        with _patch_client_init(), _patch_client("get_transfer_graph", graph):
            runner = CliRunner()
            result = runner.invoke(madsci, ["location", "transfer-graph", *_URL_ARGS])
            assert result.exit_code == 0
            assert "Transfer Graph" in result.output

    def test_transfer_graph_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_transfer_graph", {}):
            runner = CliRunner()
            result = runner.invoke(madsci, ["location", "transfer-graph", *_URL_ARGS])
            assert result.exit_code == 0
            assert "empty" in result.output.lower()

    def test_transfer_graph_json(self) -> None:
        graph = {_LOC_ID_1: [_LOC_ID_2]}
        with _patch_client_init(), _patch_client("get_transfer_graph", graph):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--json", "location", "transfer-graph", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_transfer_graph_quiet(self) -> None:
        graph = {_LOC_ID_1: [_LOC_ID_2]}
        with _patch_client_init(), _patch_client("get_transfer_graph", graph):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--quiet", "location", "transfer-graph", *_URL_ARGS]
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location plan-transfer
# ---------------------------------------------------------------------------


class TestLocationPlanTransfer:
    """Tests for 'location plan-transfer'."""

    def test_plan_transfer_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "plan-transfer", "--help"])
        assert result.exit_code == 0
        assert "--resource-id" in result.output

    def test_plan_transfer_basic(self) -> None:
        from madsci.common.types.workflow_types import WorkflowDefinition

        wf = WorkflowDefinition(name="transfer_plan")
        with _patch_client_init(), _patch_client("plan_transfer", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "plan-transfer", _LOC_ID_1, _LOC_ID_2, *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "Transfer Plan" in result.output

    def test_plan_transfer_json(self) -> None:
        from madsci.common.types.workflow_types import WorkflowDefinition

        wf = WorkflowDefinition(name="transfer_plan")
        with _patch_client_init(), _patch_client("plan_transfer", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "plan-transfer",
                    _LOC_ID_1,
                    _LOC_ID_2,
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0

    def test_plan_transfer_quiet(self) -> None:
        from madsci.common.types.workflow_types import WorkflowDefinition

        wf = WorkflowDefinition(name="transfer_plan")
        with _patch_client_init(), _patch_client("plan_transfer", wf):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "location",
                    "plan-transfer",
                    _LOC_ID_1,
                    _LOC_ID_2,
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location export
# ---------------------------------------------------------------------------


class TestLocationExport:
    """Tests for 'location export'."""

    def test_export_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "export", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output

    def test_export_stdout(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("export_locations", [loc]):
            runner = CliRunner()
            result = runner.invoke(madsci, ["location", "export", *_URL_ARGS])
            assert result.exit_code == 0

    def test_export_json(self) -> None:
        loc = _make_location()
        with _patch_client_init(), _patch_client("export_locations", [loc]):
            runner = CliRunner()
            result = runner.invoke(madsci, ["--json", "location", "export", *_URL_ARGS])
            assert result.exit_code == 0

    def test_export_to_file(self, tmp_path: Path) -> None:
        loc = _make_location()
        out_file = tmp_path / "locations.yaml"
        with _patch_client_init(), _patch_client("export_locations", [loc]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "export", "--output", str(out_file), *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert out_file.exists()
            assert "Exported" in result.output


# ---------------------------------------------------------------------------
# location import
# ---------------------------------------------------------------------------


class TestLocationImport:
    """Tests for 'location import'."""

    def test_import_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "import", "--help"])
        assert result.exit_code == 0
        assert "--overwrite" in result.output

    def test_import_basic(self, tmp_path: Path) -> None:
        import yaml

        loc_data = [{"location_name": "imported_loc", "location_id": new_ulid_str()}]
        in_file = tmp_path / "locations.yaml"
        in_file.write_text(yaml.dump(loc_data))

        import_result = LocationImportResult(imported=1, skipped=0, errors=[])
        with _patch_client_init(), _patch_client("import_locations", import_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "import", str(in_file), *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "1 imported" in result.output

    def test_import_json(self, tmp_path: Path) -> None:
        import yaml

        loc_data = [{"location_name": "imported_loc", "location_id": new_ulid_str()}]
        in_file = tmp_path / "locations.yaml"
        in_file.write_text(yaml.dump(loc_data))

        import_result = LocationImportResult(imported=1, skipped=0, errors=[])
        with _patch_client_init(), _patch_client("import_locations", import_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "location", "import", str(in_file), *_URL_ARGS],
            )
            assert result.exit_code == 0

    def test_import_with_errors(self, tmp_path: Path) -> None:
        import yaml

        loc_data = [{"location_name": "bad_loc", "location_id": new_ulid_str()}]
        in_file = tmp_path / "locations.yaml"
        in_file.write_text(yaml.dump(loc_data))

        import_result = LocationImportResult(
            imported=0, skipped=0, errors=["duplicate name"]
        )
        with _patch_client_init(), _patch_client("import_locations", import_result):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "import", str(in_file), *_URL_ARGS],
            )
            assert result.exit_code == 0
            assert "1 errors" in result.output

    def test_import_file_not_found(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            ["location", "import", "/nonexistent/file.yaml", *_URL_ARGS],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# location template list
# ---------------------------------------------------------------------------


class TestLocationTemplateList:
    """Tests for 'location template list'."""

    def test_template_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "template", "list", "--help"])
        assert result.exit_code == 0

    def test_template_list_basic(self) -> None:
        t = _make_location_template()
        with _patch_client_init(), _patch_client("get_location_templates", [t]):
            runner = CliRunner()
            result = runner.invoke(madsci, ["location", "template", "list", *_URL_ARGS])
            assert result.exit_code == 0

    def test_template_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_location_templates", []):
            runner = CliRunner()
            result = runner.invoke(madsci, ["location", "template", "list", *_URL_ARGS])
            assert result.exit_code == 0
            assert "No location templates found" in result.output

    def test_template_list_json(self) -> None:
        t = _make_location_template()
        with _patch_client_init(), _patch_client("get_location_templates", [t]):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--json", "location", "template", "list", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_template_list_quiet(self) -> None:
        t = _make_location_template()
        with _patch_client_init(), _patch_client("get_location_templates", [t]):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--quiet", "location", "template", "list", *_URL_ARGS]
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location template get
# ---------------------------------------------------------------------------


class TestLocationTemplateGet:
    """Tests for 'location template get'."""

    def test_template_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "template", "get", "--help"])
        assert result.exit_code == 0

    def test_template_get_basic(self) -> None:
        t = _make_location_template()
        with _patch_client_init(), _patch_client("get_location_template", t):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "template", "get", "test_template", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_template_get_not_found(self) -> None:
        with _patch_client_init(), _patch_client("get_location_template", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "template", "get", "nonexistent", *_URL_ARGS]
            )
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_template_get_json(self) -> None:
        t = _make_location_template()
        with _patch_client_init(), _patch_client("get_location_template", t):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["--json", "location", "template", "get", "test_template", *_URL_ARGS],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location rep-template list
# ---------------------------------------------------------------------------


class TestLocationRepTemplateList:
    """Tests for 'location rep-template list'."""

    def test_rep_template_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "rep-template", "list", "--help"])
        assert result.exit_code == 0

    def test_rep_template_list_basic(self) -> None:
        t = _make_repr_template()
        with _patch_client_init(), _patch_client("get_representation_templates", [t]):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "rep-template", "list", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_rep_template_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("get_representation_templates", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "rep-template", "list", *_URL_ARGS]
            )
            assert result.exit_code == 0
            assert "No representation templates found" in result.output

    def test_rep_template_list_json(self) -> None:
        t = _make_repr_template()
        with _patch_client_init(), _patch_client("get_representation_templates", [t]):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--json", "location", "rep-template", "list", *_URL_ARGS]
            )
            assert result.exit_code == 0

    def test_rep_template_list_quiet(self) -> None:
        t = _make_repr_template()
        with _patch_client_init(), _patch_client("get_representation_templates", [t]):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["--quiet", "location", "rep-template", "list", *_URL_ARGS]
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# location rep-template get
# ---------------------------------------------------------------------------


class TestLocationRepTemplateGet:
    """Tests for 'location rep-template get'."""

    def test_rep_template_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "rep-template", "get", "--help"])
        assert result.exit_code == 0

    def test_rep_template_get_basic(self) -> None:
        t = _make_repr_template()
        with _patch_client_init(), _patch_client("get_representation_template", t):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "rep-template", "get", "test_repr_template", *_URL_ARGS],
            )
            assert result.exit_code == 0

    def test_rep_template_get_not_found(self) -> None:
        with _patch_client_init(), _patch_client("get_representation_template", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["location", "rep-template", "get", "nonexistent", *_URL_ARGS],
            )
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_rep_template_get_json(self) -> None:
        t = _make_repr_template()
        with _patch_client_init(), _patch_client("get_representation_template", t):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "rep-template",
                    "get",
                    "test_repr_template",
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------


class TestLocationRegistered:
    """Test that the location command is properly registered."""

    def test_location_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "location" in _LAZY_COMMANDS

    def test_loc_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "loc" in AliasedGroup._aliases
        assert AliasedGroup._aliases["loc"] == "location"


# ---------------------------------------------------------------------------
# location list: managed_by column and filter
# ---------------------------------------------------------------------------


class TestLocationListManagedBy:
    """Tests for managed_by column and --managed-by filter in 'location list'."""

    def test_list_shows_managed_by_column(self) -> None:
        """The table output should include a 'Managed By' column with LAB value."""
        loc = _make_location()
        # Default managed_by is LAB
        with _patch_client_init(), _patch_client("get_locations", [loc]):
            runner = CliRunner(env={"COLUMNS": "200"})
            result = runner.invoke(madsci, ["location", "list", *_URL_ARGS])
            assert result.exit_code == 0
            assert "Managed By" in result.output
            assert "LAB" in result.output

    def test_list_shows_node_managed(self) -> None:
        """A node-managed location should show NODE in the Managed By column."""
        from madsci.common.types.location_types import LocationManagement

        loc = _make_location()
        loc.managed_by = LocationManagement.NODE
        with _patch_client_init(), _patch_client("get_locations", [loc]):
            runner = CliRunner(env={"COLUMNS": "200"})
            result = runner.invoke(madsci, ["location", "list", *_URL_ARGS])
            assert result.exit_code == 0
            assert "NODE" in result.output

    def test_list_managed_by_filter_option(self) -> None:
        """The --managed-by option should be accepted and passed to the client."""
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("get_locations", [loc]) as mock_get,
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "list", "--managed-by", "node", *_URL_ARGS]
            )
            assert result.exit_code == 0
            # Verify managed_by parameter was passed to get_locations
            mock_get.assert_called_once_with(managed_by="node")

    def test_list_managed_by_short_option(self) -> None:
        """The -m short option should work as alias for --managed-by."""
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("get_locations", [loc]) as mock_get,
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "list", "-m", "lab", *_URL_ARGS]
            )
            assert result.exit_code == 0
            mock_get.assert_called_once_with(managed_by="lab")


# ---------------------------------------------------------------------------
# location get: managed_by and owner fields
# ---------------------------------------------------------------------------


class TestLocationGetManagedBy:
    """Tests for managed_by and owner display in 'location get'."""

    def test_get_shows_managed_by(self) -> None:
        """Detail output should include Managed By field."""
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_location_by_name", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "get", "test_location", *_URL_ARGS]
            )
            assert result.exit_code == 0
            assert "Managed By" in result.output
            assert "LAB" in result.output

    def test_get_shows_owner_with_node_id(self) -> None:
        """Detail output should show the owner's node_id when present."""
        from madsci.common.types.auth_types import OwnershipInfo
        from madsci.common.types.location_types import LocationManagement

        owner = OwnershipInfo(node_id=new_ulid_str())
        loc = _make_location()
        loc.managed_by = LocationManagement.NODE
        loc.owner = owner
        with _patch_client_init(), _patch_client("get_location_by_name", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "get", "test_location", *_URL_ARGS]
            )
            assert result.exit_code == 0
            assert "Owner" in result.output
            assert str(owner.node_id) in result.output

    def test_get_shows_owner_na_when_none(self) -> None:
        """Detail output should show N/A for owner when it is None."""
        loc = _make_location()
        with _patch_client_init(), _patch_client("get_location_by_name", loc):
            runner = CliRunner()
            result = runner.invoke(
                madsci, ["location", "get", "test_location", *_URL_ARGS]
            )
            assert result.exit_code == 0
            assert "Owner" in result.output
            assert "N/A" in result.output


# ---------------------------------------------------------------------------
# location train
# ---------------------------------------------------------------------------


class TestLocationTrain:
    """Tests for 'location train' subcommand."""

    def test_train_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["location", "train", "--help"])
        assert result.exit_code == 0
        assert "LOCATION_NAME" in result.output
        assert "NODE_NAME" in result.output

    def test_train_basic_with_overrides(self) -> None:
        """Train with explicit overrides (no template) should call set_representation."""
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("set_representation", loc) as mock_set,
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "location",
                    "train",
                    "deck_slot_1",
                    "robot_arm",
                    "--overrides",
                    '{"x": 1, "y": 2}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0
            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert call_args[0][0] == "deck_slot_1"
            assert call_args[0][1] == "robot_arm"
            assert call_args[0][2] == {"x": 1, "y": 2}

    def test_train_with_template(self) -> None:
        """Train with --template should fetch the template and merge defaults with overrides."""
        from madsci.common.types.location_types import LocationRepresentationTemplate

        template = LocationRepresentationTemplate(
            template_name="arm_template",
            default_values={"gripper": "standard", "max_payload": 2.0},
        )
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("get_representation_template", template),
            _patch_client("set_representation", loc) as mock_set,
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "location",
                    "train",
                    "deck_slot_1",
                    "robot_arm",
                    "--template",
                    "arm_template",
                    "--overrides",
                    '{"gripper": "wide"}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0
            mock_set.assert_called_once()
            # Should be defaults merged with overrides
            call_data = mock_set.call_args[0][2]
            assert call_data["gripper"] == "wide"  # override
            assert call_data["max_payload"] == 2.0  # from template default

    def test_train_with_template_no_overrides(self) -> None:
        """Train with --template but no overrides should use template defaults as-is."""
        from madsci.common.types.location_types import LocationRepresentationTemplate

        template = LocationRepresentationTemplate(
            template_name="arm_template",
            default_values={"gripper": "standard"},
        )
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("get_representation_template", template),
            _patch_client("set_representation", loc) as mock_set,
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "location",
                    "train",
                    "deck_slot_1",
                    "robot_arm",
                    "--template",
                    "arm_template",
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0
            call_data = mock_set.call_args[0][2]
            assert call_data == {"gripper": "standard"}

    def test_train_invalid_overrides_json(self) -> None:
        """Invalid JSON in --overrides should produce an error."""
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "location",
                "train",
                "deck_slot_1",
                "robot_arm",
                "--overrides",
                "not-json",
                *_URL_ARGS,
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_train_no_template_no_overrides(self) -> None:
        """Train with neither --template nor --overrides should error."""
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "location",
                "train",
                "deck_slot_1",
                "robot_arm",
                *_URL_ARGS,
            ],
        )
        assert result.exit_code != 0

    def test_train_json_output(self) -> None:
        """Train with --json output should produce JSON."""
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("set_representation", loc),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "location",
                    "train",
                    "deck_slot_1",
                    "robot_arm",
                    "--overrides",
                    '{"x": 1}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0

    def test_train_quiet_output(self) -> None:
        """Train with --quiet output should produce minimal output."""
        loc = _make_location()
        with (
            _patch_client_init(),
            _patch_client("set_representation", loc),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "location",
                    "train",
                    "deck_slot_1",
                    "robot_arm",
                    "--overrides",
                    '{"x": 1}',
                    *_URL_ARGS,
                ],
            )
            assert result.exit_code == 0
