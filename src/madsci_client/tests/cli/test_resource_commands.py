"""Tests for the madsci resource command group."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.types.resource_types import Asset, Resource
from madsci.common.utils import new_ulid_str

# Pre-generate stable ULID strings for tests
_RES_ID_1 = new_ulid_str()
_RES_ID_2 = new_ulid_str()
_RES_ID_PARENT = new_ulid_str()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_resource(
    *,
    resource_id: str | None = None,
    resource_name: str = "test-resource",
    parent_id: str | None = None,
) -> Resource:
    """Build a minimal Resource for testing."""
    if resource_id is None:
        resource_id = _RES_ID_1
    return Resource(
        resource_id=resource_id,
        resource_name=resource_name,
        parent_id=parent_id,
    )


def _patch_client(method_name: str, return_value):
    """Shortcut to patch a ResourceClient method."""
    return patch(
        f"madsci.client.resource_client.ResourceClient.{method_name}",
        return_value=return_value,
    )


def _patch_client_init():
    """Patch ResourceClient.__init__ to avoid network access."""
    return patch(
        "madsci.client.resource_client.ResourceClient.__init__",
        return_value=None,
    )


# ---------------------------------------------------------------------------
# resource group help
# ---------------------------------------------------------------------------


class TestResourceGroup:
    """Tests for the resource command group itself."""

    def test_resource_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "--help"])
        assert result.exit_code == 0
        assert "Manage resources" in result.output

    def test_resource_alias(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["res", "--help"])
        assert result.exit_code == 0
        assert "Manage resources" in result.output


# ---------------------------------------------------------------------------
# resource list
# ---------------------------------------------------------------------------


class TestResourceList:
    """Tests for 'resource list'."""

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "list", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--limit" in result.output

    def test_list_default(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("query_resource", [r]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["resource", "list", "--resource-url", "http://localhost:8003/"],
            )
            assert result.exit_code == 0
            assert "test-reso" in result.output

    def test_list_with_type(self) -> None:
        r = Asset(resource_id=_RES_ID_1, resource_name="test-asset")
        with _patch_client_init(), _patch_client("query_resource", [r]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "list",
                    "--type",
                    "asset",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_list_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("query_resource", [r]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "list",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_list_quiet(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("query_resource", [r]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "resource",
                    "list",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            # quiet Console suppresses output by design; just verify no crash
            assert result.exit_code == 0

    def test_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("query_resource", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["resource", "list", "--resource-url", "http://localhost:8003/"],
            )
            assert result.exit_code == 0
            assert "No resources found" in result.output

    def test_list_single_resource_wrapped_as_list(self) -> None:
        """query_resource may return a single item instead of a list."""
        r = _make_resource()
        with _patch_client_init(), _patch_client("query_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                ["resource", "list", "--resource-url", "http://localhost:8003/"],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource get
# ---------------------------------------------------------------------------


class TestResourceGet:
    """Tests for 'resource get'."""

    def test_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "get", "--help"])
        assert result.exit_code == 0

    def test_get_basic(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("get_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "get",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "test-resource" in result.output

    def test_get_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("get_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "get",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_get_not_found(self) -> None:
        with _patch_client_init(), _patch_client("get_resource", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "get",
                    "NOTFOUND12345",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_get_quiet(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("get_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "resource",
                    "get",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource create
# ---------------------------------------------------------------------------


class TestResourceCreate:
    """Tests for 'resource create'."""

    def test_create_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "create", "--help"])
        assert result.exit_code == 0
        assert "--template" in result.output
        assert "--name" in result.output
        assert "--params" in result.output

    def test_create_basic(self) -> None:
        r = _make_resource(resource_name="my-new-resource")
        with (
            _patch_client_init(),
            _patch_client("create_resource_from_template", r),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "create",
                    "--template",
                    "my_plate",
                    "--name",
                    "my-new-resource",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "created" in result.output.lower()

    def test_create_with_params(self) -> None:
        r = _make_resource()
        with (
            _patch_client_init(),
            _patch_client("create_resource_from_template", r),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "create",
                    "--template",
                    "my_plate",
                    "--params",
                    '{"quantity": 10}',
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_create_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "resource",
                "create",
                "--template",
                "my_plate",
                "--params",
                "not-valid-json",
                "--resource-url",
                "http://localhost:8003/",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_create_missing_template(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "resource",
                "create",
                "--resource-url",
                "http://localhost:8003/",
            ],
        )
        assert result.exit_code != 0

    def test_create_json(self) -> None:
        r = _make_resource()
        with (
            _patch_client_init(),
            _patch_client("create_resource_from_template", r),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "create",
                    "--template",
                    "my_plate",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_create_quiet(self) -> None:
        r = _make_resource()
        with (
            _patch_client_init(),
            _patch_client("create_resource_from_template", r),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "resource",
                    "create",
                    "--template",
                    "my_plate",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource delete
# ---------------------------------------------------------------------------


class TestResourceDelete:
    """Tests for 'resource delete'."""

    def test_delete_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "delete", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_delete_with_yes(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("remove_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "delete",
                    _RES_ID_1,
                    "--yes",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "deleted" in result.output.lower()

    def test_delete_abort(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            madsci,
            [
                "resource",
                "delete",
                _RES_ID_1,
                "--resource-url",
                "http://localhost:8003/",
            ],
            input="n\n",
        )
        assert result.exit_code != 0

    def test_delete_confirm(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("remove_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "delete",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "deleted" in result.output.lower()

    def test_delete_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("remove_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "delete",
                    _RES_ID_1,
                    "--yes",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource restore
# ---------------------------------------------------------------------------


class TestResourceRestore:
    """Tests for 'resource restore'."""

    def test_restore_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "restore", "--help"])
        assert result.exit_code == 0

    def test_restore_basic(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("restore_deleted_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "restore",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "restored" in result.output.lower()

    def test_restore_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("restore_deleted_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "restore",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_restore_quiet(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("restore_deleted_resource", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "resource",
                    "restore",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource tree
# ---------------------------------------------------------------------------


class TestResourceTree:
    """Tests for 'resource tree'."""

    def test_tree_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "tree", "--help"])
        assert result.exit_code == 0

    def test_tree_basic(self) -> None:
        from madsci.common.types.resource_types.server_types import ResourceHierarchy

        hierarchy = ResourceHierarchy(
            ancestor_ids=[_RES_ID_PARENT],
            resource_id=_RES_ID_1,
            descendant_ids={_RES_ID_1: [_RES_ID_2]},
        )
        with (
            _patch_client_init(),
            _patch_client("query_resource_hierarchy", hierarchy),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "tree",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "Hierarchy" in result.output

    def test_tree_json(self) -> None:
        from madsci.common.types.resource_types.server_types import ResourceHierarchy

        hierarchy = ResourceHierarchy(
            ancestor_ids=[],
            resource_id=_RES_ID_1,
            descendant_ids={},
        )
        with (
            _patch_client_init(),
            _patch_client("query_resource_hierarchy", hierarchy),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "tree",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_tree_no_ancestors(self) -> None:
        from madsci.common.types.resource_types.server_types import ResourceHierarchy

        hierarchy = ResourceHierarchy(
            ancestor_ids=[],
            resource_id=_RES_ID_1,
            descendant_ids={_RES_ID_1: [_RES_ID_2]},
        )
        with (
            _patch_client_init(),
            _patch_client("query_resource_hierarchy", hierarchy),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "tree",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource lock
# ---------------------------------------------------------------------------


class TestResourceLock:
    """Tests for 'resource lock'."""

    def test_lock_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "lock", "--help"])
        assert result.exit_code == 0
        assert "--owner" in result.output
        assert "--duration" in result.output

    def test_lock_basic(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("acquire_lock", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "lock",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "acquired" in result.output.lower()

    def test_lock_with_owner(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("acquire_lock", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "lock",
                    _RES_ID_1,
                    "--owner",
                    "my-client",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_lock_failed(self) -> None:
        with _patch_client_init(), _patch_client("acquire_lock", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "lock",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code != 0
            assert "Failed" in result.output

    def test_lock_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("acquire_lock", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "lock",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource unlock
# ---------------------------------------------------------------------------


class TestResourceUnlock:
    """Tests for 'resource unlock'."""

    def test_unlock_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "unlock", "--help"])
        assert result.exit_code == 0
        assert "--owner" in result.output

    def test_unlock_basic(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("release_lock", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "unlock",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "released" in result.output.lower()

    def test_unlock_failed(self) -> None:
        with _patch_client_init(), _patch_client("release_lock", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "unlock",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code != 0
            assert "Failed" in result.output

    def test_unlock_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("release_lock", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "unlock",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource quantity set
# ---------------------------------------------------------------------------


class TestResourceQuantitySet:
    """Tests for 'resource quantity set'."""

    def test_quantity_set_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "quantity", "set", "--help"])
        assert result.exit_code == 0

    def test_quantity_set_basic(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("set_quantity", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "quantity",
                    "set",
                    _RES_ID_1,
                    "100",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "100" in result.output

    def test_quantity_set_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("set_quantity", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "quantity",
                    "set",
                    _RES_ID_1,
                    "50",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource quantity adjust
# ---------------------------------------------------------------------------


class TestResourceQuantityAdjust:
    """Tests for 'resource quantity adjust'."""

    def test_quantity_adjust_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "quantity", "adjust", "--help"])
        assert result.exit_code == 0

    def test_quantity_adjust_positive(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("change_quantity_by", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "quantity",
                    "adjust",
                    _RES_ID_1,
                    "5",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "+5" in result.output

    def test_quantity_adjust_negative(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("change_quantity_by", r):
            runner = CliRunner()
            # Use -- to separate options from arguments so Click doesn't
            # interpret "-3" as an option flag.
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "quantity",
                    "adjust",
                    "--resource-url",
                    "http://localhost:8003/",
                    "--",
                    _RES_ID_1,
                    "-3",
                ],
            )
            assert result.exit_code == 0

    def test_quantity_adjust_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("change_quantity_by", r):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "quantity",
                    "adjust",
                    _RES_ID_1,
                    "10",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource template list
# ---------------------------------------------------------------------------


class TestResourceTemplateList:
    """Tests for 'resource template list'."""

    def test_template_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "template", "list", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output

    def test_template_list_basic(self) -> None:
        r = _make_resource(resource_name="plate_template")
        with _patch_client_init(), _patch_client("query_templates", [r]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "template",
                    "list",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_template_list_empty(self) -> None:
        with _patch_client_init(), _patch_client("query_templates", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "template",
                    "list",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "No templates found" in result.output

    def test_template_list_json(self) -> None:
        r = _make_resource()
        with _patch_client_init(), _patch_client("query_templates", [r]):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "template",
                    "list",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource template get
# ---------------------------------------------------------------------------


class TestResourceTemplateGet:
    """Tests for 'resource template get'."""

    def test_template_get_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "template", "get", "--help"])
        assert result.exit_code == 0

    def test_template_get_basic(self) -> None:
        template_info = {
            "template_name": "my_plate",
            "description": "A standard plate",
            "version": "1.0.0",
            "required_overrides": [],
            "tags": ["lab"],
            "created_by": "admin",
        }
        with _patch_client_init(), _patch_client("get_template_info", template_info):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "template",
                    "get",
                    "my_plate",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_template_get_not_found(self) -> None:
        with _patch_client_init(), _patch_client("get_template_info", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "template",
                    "get",
                    "nonexistent",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_template_get_json(self) -> None:
        template_info = {
            "template_name": "my_plate",
            "description": "A standard plate",
            "version": "1.0.0",
        }
        with _patch_client_init(), _patch_client("get_template_info", template_info):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "template",
                    "get",
                    "my_plate",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# resource template create
# ---------------------------------------------------------------------------


class TestResourceTemplateCreate:
    """Tests for 'resource template create'."""

    def test_template_create_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "template", "create", "--help"])
        assert result.exit_code == 0
        assert "--from" in result.output
        assert "--name" in result.output

    def test_template_create_basic(self) -> None:
        source = _make_resource()
        template_result = _make_resource(resource_name="my_template")
        with (
            _patch_client_init(),
            _patch_client("get_resource", source),
            _patch_client("create_template", template_result),
        ):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "template",
                    "create",
                    "--from",
                    _RES_ID_1,
                    "--name",
                    "my_template",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "created" in result.output.lower()

    def test_template_create_source_not_found(self) -> None:
        with _patch_client_init(), _patch_client("get_resource", None):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "template",
                    "create",
                    "--from",
                    "NOTFOUND",
                    "--name",
                    "my_template",
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code != 0
            assert "not found" in result.output


# ---------------------------------------------------------------------------
# resource history
# ---------------------------------------------------------------------------


class TestResourceHistory:
    """Tests for 'resource history'."""

    def test_history_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(madsci, ["resource", "history", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output

    def test_history_basic(self) -> None:
        history_entries = [
            {
                "history_id": "h1",
                "version": 1,
                "change_type": "create",
                "changed_at": "2026-01-01T00:00:00",
                "change_description": "Resource created",
            },
            {
                "history_id": "h2",
                "version": 2,
                "change_type": "update",
                "changed_at": "2026-01-02T00:00:00",
                "change_description": "Quantity updated",
            },
        ]
        with _patch_client_init(), _patch_client("query_history", history_entries):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "history",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_history_empty(self) -> None:
        with _patch_client_init(), _patch_client("query_history", []):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "resource",
                    "history",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0
            assert "No history found" in result.output

    def test_history_json(self) -> None:
        history_entries = [
            {
                "history_id": "h1",
                "version": 1,
                "change_type": "create",
            }
        ]
        with _patch_client_init(), _patch_client("query_history", history_entries):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--json",
                    "resource",
                    "history",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0

    def test_history_quiet(self) -> None:
        history_entries = [
            {"history_id": "h1", "version": 1},
        ]
        with _patch_client_init(), _patch_client("query_history", history_entries):
            runner = CliRunner()
            result = runner.invoke(
                madsci,
                [
                    "--quiet",
                    "resource",
                    "history",
                    _RES_ID_1,
                    "--resource-url",
                    "http://localhost:8003/",
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------


class TestResourceRegistered:
    """Test that the resource command is properly registered."""

    def test_resource_in_lazy_commands(self) -> None:
        from madsci.client.cli import _LAZY_COMMANDS

        assert "resource" in _LAZY_COMMANDS

    def test_res_alias(self) -> None:
        from madsci.client.cli import AliasedGroup

        assert "res" in AliasedGroup._aliases
        assert AliasedGroup._aliases["res"] == "resource"
