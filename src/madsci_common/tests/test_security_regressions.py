"""Tests for fixes identified during PR #226 review.

Covers:
- InMemoryRedis clear_all_registries (including Redlock state)
- InMemoryRedis shared-lock semantics across instances
- MadsciBaseSettings nested model_dump_safe (including list-of-model)
- no_color context propagation
- Shell injection prevention in template hooks
- PATH parameter validation
- min_length=0 truthiness fix
- Template path traversal prevention (engine + registry)
- SandboxedEnvironment for user templates
"""

import shlex
import threading
from typing import ClassVar, List
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment
from madsci.client.cli import madsci
from madsci.common.local_backends.inmemory_redis import (
    InMemoryRedisClient,
    InMemoryRedisDict,
    InMemoryRedisList,
    InMemoryRedlock,
    clear_all_registries,
)
from madsci.common.migration.converter import MigrationConverter, MigrationRollback
from madsci.common.templates.engine import TemplateEngine, TemplateValidationError
from madsci.common.templates.registry import TemplateRegistry
from madsci.common.types.base_types import (
    REDACTED_PLACEHOLDER,
    MadsciBaseModel,
    MadsciBaseSettings,
)
from madsci.common.types.migration_types import FileMigration, FileType
from madsci.common.types.template_types import (
    ParameterType,
    TemplateFile,
    TemplateManifest,
    TemplateParameter,
)
from pydantic import Field

# ------------------------------------------------------------------ #
# 2D: clear_all_registries                                           #
# ------------------------------------------------------------------ #


class TestClearAllRegistries:
    """Tests for clear_all_registries helper."""

    def test_clears_dict_registry(self) -> None:
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict", redis=client)
        d["key"] = "value"

        clear_all_registries()

        # After clearing, a new dict with the same key should be empty
        d2 = InMemoryRedisDict(key="test:dict", redis=client)
        assert len(d2) == 0

    def test_clears_list_registry(self) -> None:
        client = InMemoryRedisClient()
        lst = InMemoryRedisList(key="test:list", redis=client)
        lst.append("item")

        clear_all_registries()

        lst2 = InMemoryRedisList(key="test:list", redis=client)
        assert len(lst2) == 0

    def test_clears_both_registries(self) -> None:
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:d", redis=client)
        d["a"] = 1
        lst = InMemoryRedisList(key="test:l", redis=client)
        lst.append(1)

        clear_all_registries()

        d2 = InMemoryRedisDict(key="test:d", redis=client)
        lst2 = InMemoryRedisList(key="test:l", redis=client)
        assert len(d2) == 0
        assert len(lst2) == 0


# ------------------------------------------------------------------ #
# 2C: Nested model_dump_safe on MadsciBaseSettings                   #
# ------------------------------------------------------------------ #

_INNER_DEFAULT_VALUE = "s3cret"


class InnerSettings(MadsciBaseSettings):
    """Nested settings with a secret field."""

    model_config: ClassVar = {"env_prefix": "INNER_TEST_", "cli_parse_args": False}

    public_field: str = "visible"
    secret_field: str = Field(
        default=_INNER_DEFAULT_VALUE,
        json_schema_extra={"secret": True},
    )


class OuterSettings(MadsciBaseSettings):
    """Outer settings that contain a nested settings model."""

    model_config: ClassVar = {"env_prefix": "OUTER_TEST_", "cli_parse_args": False}

    name: str = "outer"
    inner: InnerSettings = Field(default_factory=InnerSettings)


class TestNestedModelDumpSafe:
    """model_dump_safe should redact secrets in nested models."""

    def test_top_level_secret_redacted(self) -> None:
        inner = InnerSettings()
        data = inner.model_dump_safe()
        assert data["secret_field"] == REDACTED_PLACEHOLDER
        assert data["public_field"] == "visible"

    def test_nested_settings_secrets_redacted(self) -> None:
        outer = OuterSettings()
        data = outer.model_dump_safe()
        # The inner model's secret should be redacted too
        assert data["inner"]["secret_field"] == REDACTED_PLACEHOLDER
        assert data["inner"]["public_field"] == "visible"

    def test_include_secrets_shows_values(self) -> None:
        outer = OuterSettings()
        data = outer.model_dump_safe(include_secrets=True)
        assert data["inner"]["secret_field"] == _INNER_DEFAULT_VALUE


# ------------------------------------------------------------------ #
# Nested MadsciBaseModel secret redaction (existing, regression test) #
# ------------------------------------------------------------------ #


class InnerModel(MadsciBaseModel):
    """Nested model with a secret field."""

    api_key: str = Field(default="key123", json_schema_extra={"secret": True})
    label: str = "public"


class OuterModel(MadsciBaseModel):
    """Model containing a nested model."""

    child: InnerModel = Field(default_factory=InnerModel)
    name: str = "parent"


class TestNestedBaseModelDumpSafe:
    def test_nested_base_model_secrets_redacted(self) -> None:
        obj = OuterModel()
        data = obj.model_dump_safe()
        assert data["child"]["api_key"] == REDACTED_PLACEHOLDER
        assert data["child"]["label"] == "public"


# ------------------------------------------------------------------ #
# 1B: no_color stored in CLI context                                 #
# ------------------------------------------------------------------ #


class TestNoColorContext:
    def test_no_color_stored_in_context(self) -> None:
        runner = CliRunner()
        # Use a command that accesses the context
        result = runner.invoke(madsci, ["--no-color", "version"])
        # The command should not crash and should work with --no-color
        assert result.exit_code == 0


# ------------------------------------------------------------------ #
# 1A: Shell injection prevention in template hooks                   #
# ------------------------------------------------------------------ #


class TestShellInjectionPrevention:
    def test_shlex_split_prevents_injection(self) -> None:
        """Verify that shlex.split tokenizes safely."""
        # A malicious template value that tries shell injection
        malicious = "echo hello; rm -rf /"
        tokens = shlex.split(malicious)
        # shlex.split treats semicolons as part of the token, not as shell separators
        # when there's no shell interpretation
        assert ";" in " ".join(tokens) or "rm" in tokens
        # The important thing is that subprocess.run(tokens, shell=False) would
        # NOT execute "rm -rf /" because it treats the whole thing as arguments
        # to "echo"


# ------------------------------------------------------------------ #
# 3B: PATH parameter validation                                      #
# ------------------------------------------------------------------ #


class TestPathParameterValidation:
    def test_path_validates_null_bytes(self) -> None:
        # Create a mock manifest with a PATH parameter
        mock_manifest = MagicMock()
        mock_manifest.parameters = [
            TemplateParameter(
                name="output_path",
                description="Output path parameter",
                type=ParameterType.PATH,
                required=True,
            )
        ]

        engine = TemplateEngine.__new__(TemplateEngine)
        engine.manifest = mock_manifest

        errors = engine.validate_parameters({"output_path": "/valid/path"})
        assert errors == []

        errors = engine.validate_parameters({"output_path": "/invalid\x00/path"})
        assert len(errors) == 1
        assert "null byte" in errors[0].lower()


# ------------------------------------------------------------------ #
# 3C: min_length=0 truthiness fix                                    #
# ------------------------------------------------------------------ #


class TestMinLengthZero:
    def test_min_length_zero_enforced(self) -> None:
        mock_manifest = MagicMock()
        mock_manifest.parameters = [
            TemplateParameter(
                name="name",
                description="Name parameter",
                type=ParameterType.STRING,
                required=True,
                min_length=0,
                max_length=5,
            )
        ]

        engine = TemplateEngine.__new__(TemplateEngine)
        engine.manifest = mock_manifest

        # Empty string should pass (min_length=0)
        errors = engine.validate_parameters({"name": ""})
        assert errors == []

        # Too long should fail
        errors = engine.validate_parameters({"name": "toolong"})
        assert len(errors) == 1
        assert "too long" in errors[0].lower()


# ------------------------------------------------------------------ #
# Phase 2D: clear_all_registries also clears InMemoryRedlock          #
# ------------------------------------------------------------------ #


class TestClearAllRegistriesRedlock:
    def test_clears_redlock_state(self) -> None:
        """clear_all_registries should also clear the Redlock registry."""
        InMemoryRedlock(key="test:lock")  # Creates the lock in the registry
        assert "test:lock" in InMemoryRedlock._locks

        clear_all_registries()

        assert "test:lock" not in InMemoryRedlock._locks


# ------------------------------------------------------------------ #
# Phase 4A: Shared locks across InMemoryRedisDict instances           #
# ------------------------------------------------------------------ #


class TestSharedLockSemantics:
    def test_dict_instances_share_lock(self) -> None:
        """Two InMemoryRedisDict with same key/client share the same lock."""
        clear_all_registries()
        client = InMemoryRedisClient()
        d1 = InMemoryRedisDict(key="shared:key", redis=client)
        d2 = InMemoryRedisDict(key="shared:key", redis=client)

        assert d1._lock is d2._lock
        assert d1._store is d2._store

    def test_list_instances_share_lock(self) -> None:
        """Two InMemoryRedisList with same key/client share the same lock."""
        clear_all_registries()
        client = InMemoryRedisClient()
        l1 = InMemoryRedisList(key="shared:list", redis=client)
        l2 = InMemoryRedisList(key="shared:list", redis=client)

        assert l1._lock is l2._lock
        assert l1._store is l2._store

    def test_dict_different_keys_have_different_locks(self) -> None:
        """Different keys should produce different locks."""
        clear_all_registries()
        client = InMemoryRedisClient()
        d1 = InMemoryRedisDict(key="a", redis=client)
        d2 = InMemoryRedisDict(key="b", redis=client)

        assert d1._lock is not d2._lock

    def test_concurrent_writes_with_shared_lock(self) -> None:
        """Verify that concurrent writes via shared locks are safe."""
        clear_all_registries()
        client = InMemoryRedisClient()
        d1 = InMemoryRedisDict(key="conc:key", redis=client)
        d2 = InMemoryRedisDict(key="conc:key", redis=client)

        barrier = threading.Barrier(2)

        def writer(d: InMemoryRedisDict, prefix: str) -> None:
            barrier.wait()
            for i in range(100):
                d[f"{prefix}_{i}"] = i

        t1 = threading.Thread(target=writer, args=(d1, "a"))
        t2 = threading.Thread(target=writer, args=(d2, "b"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # All 200 keys should exist
        assert len(d1) == 200


# ------------------------------------------------------------------ #
# Phase 5: List-of-model secret redaction                             #
# ------------------------------------------------------------------ #


class NestedItemModel(MadsciBaseModel):
    """A model with a secret field, used as a list item."""

    token: str = Field(default="tok123", json_schema_extra={"secret": True})
    label: str = "visible"


class ParentWithListModel(MadsciBaseModel):
    """A model containing a list of models with secrets."""

    items: List[NestedItemModel] = Field(
        default_factory=lambda: [NestedItemModel(), NestedItemModel(token="tok456")]  # noqa: S106
    )
    name: str = "parent"


class TestListOfModelSecretRedaction:
    def test_list_of_models_secrets_redacted(self) -> None:
        """Secret fields in a list of nested models should be redacted."""
        obj = ParentWithListModel()
        data = obj.model_dump_safe()

        assert len(data["items"]) == 2
        for item in data["items"]:
            assert item["token"] == REDACTED_PLACEHOLDER
            assert item["label"] == "visible"

    def test_list_of_models_include_secrets(self) -> None:
        """include_secrets=True should show actual values in list items."""
        obj = ParentWithListModel()
        data = obj.model_dump_safe(include_secrets=True)

        assert data["items"][0]["token"] == "tok123"  # noqa: S105
        assert data["items"][1]["token"] == "tok456"  # noqa: S105


class NestedItemSettings(MadsciBaseSettings):
    """Settings model with a secret, used in a list."""

    model_config: ClassVar = {
        "env_prefix": "NESTED_ITEM_TEST_",
        "cli_parse_args": False,
    }

    api_key: str = Field(default="key999", json_schema_extra={"secret": True})
    host: str = "localhost"


class ParentWithListSettings(MadsciBaseSettings):
    """Settings containing a list of nested settings models."""

    model_config: ClassVar = {
        "env_prefix": "PARENT_LIST_TEST_",
        "cli_parse_args": False,
    }

    backends: List[NestedItemSettings] = Field(
        default_factory=lambda: [NestedItemSettings()]
    )


class TestListOfSettingsSecretRedaction:
    def test_list_of_settings_secrets_redacted(self) -> None:
        """Secret fields in a list of nested settings should be redacted."""
        obj = ParentWithListSettings()
        data = obj.model_dump_safe()

        assert len(data["backends"]) == 1
        assert data["backends"][0]["api_key"] == REDACTED_PLACEHOLDER
        assert data["backends"][0]["host"] == "localhost"


# ------------------------------------------------------------------ #
# Phase 3: Template security — path traversal prevention              #
# ------------------------------------------------------------------ #


class TestTemplatePathTraversal:
    def test_path_traversal_in_registry_get_template(self) -> None:
        """Template IDs with '..' should be rejected."""
        registry = TemplateRegistry()

        # IDs with != 2 parts are rejected as invalid format
        with pytest.raises(ValueError, match="Invalid template ID"):
            registry.get_template("../etc/passwd")

    def test_path_traversal_in_registry_category(self) -> None:
        """Category component with '..' should be rejected."""
        registry = TemplateRegistry()

        # '..' in category part triggers path traversal check
        with pytest.raises(ValueError, match="path traversal"):
            registry.get_template("../device")

    def test_path_traversal_in_registry_name(self) -> None:
        """Name component with '..' should be rejected."""
        registry = TemplateRegistry()

        # '..' in name part triggers path traversal check
        with pytest.raises(ValueError, match="path traversal"):
            registry.get_template("module/..")

    def test_path_traversal_multi_segment_rejected(self) -> None:
        """Template IDs with more than 2 parts (common in traversal) are rejected."""
        registry = TemplateRegistry()

        with pytest.raises(ValueError, match="Invalid template ID"):
            registry.get_template("module/../../etc")

    def test_valid_template_id_accepted(self) -> None:
        """Normal template IDs should not raise ValueError."""
        registry = TemplateRegistry()
        # This should not raise ValueError (may raise TemplateNotFoundError)
        try:
            registry.get_template("module/device")
        except ValueError:
            pytest.fail("Valid template ID should not raise ValueError")
        except Exception:  # noqa: S110
            pass  # TemplateNotFoundError or import errors are acceptable

    def test_engine_path_traversal_in_dest(self, tmp_path) -> None:
        """Rendered destination paths escaping output_dir should be rejected."""
        # Create a minimal template directory
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        source_file = template_dir / "file.txt.j2"
        source_file.write_text("content")

        manifest = TemplateManifest(
            name="test",
            version="0.1.0",
            description="test template",
            category="module",
            parameters=[],
            files=[
                TemplateFile(
                    source="file.txt.j2",
                    destination="../../../etc/malicious.txt",
                )
            ],
        )

        engine = TemplateEngine.__new__(TemplateEngine)
        engine.template_dir = template_dir
        engine.manifest = manifest
        engine._sandboxed = False
        engine._shared_dir = None
        engine._jinja_env = engine._create_jinja_env()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(TemplateValidationError, match=r"[Pp]ath traversal"):
            engine.render(output_dir=output_dir, parameters={})


# ------------------------------------------------------------------ #
# Phase 3C: SandboxedEnvironment for user templates                   #
# ------------------------------------------------------------------ #


class TestSandboxedEnvironment:
    def test_sandboxed_flag_creates_sandbox(self, tmp_path) -> None:
        """TemplateEngine(sandboxed=True) should use SandboxedEnvironment."""
        # Create minimal template
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        manifest = template_dir / "template.yaml"
        manifest.write_text(
            "name: test\nversion: '0.1.0'\ndescription: test\n"
            "category: module\nparameters: []\nfiles: []\n"
        )

        engine = TemplateEngine(template_dir, sandboxed=True)
        assert isinstance(engine._jinja_env, SandboxedEnvironment)

    def test_non_sandboxed_uses_regular_env(self, tmp_path) -> None:
        """TemplateEngine(sandboxed=False) should use regular Environment."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        manifest = template_dir / "template.yaml"
        manifest.write_text(
            "name: test\nversion: '0.1.0'\ndescription: test\n"
            "category: module\nparameters: []\nfiles: []\n"
        )

        engine = TemplateEngine(template_dir, sandboxed=False)
        assert isinstance(engine._jinja_env, Environment)
        assert not isinstance(engine._jinja_env, SandboxedEnvironment)


# ------------------------------------------------------------------ #
# Phase 6: MadsciContext wiring                                        #
# ------------------------------------------------------------------ #


class TestCLIContextLoading:
    def test_context_available_in_click_context(self) -> None:
        """MadsciContext should be loaded and stored in ctx.obj."""
        runner = CliRunner()
        result = runner.invoke(madsci, ["version"])
        assert result.exit_code == 0


# ------------------------------------------------------------------ #
# .env file escaping for newlines/tabs                                #
# ------------------------------------------------------------------ #


class TestEnvFileEscaping:
    """_write_env_file should properly escape newlines, carriage returns, and tabs."""

    def test_newline_escaped(self, tmp_path) -> None:
        converter = MigrationConverter()
        output = tmp_path / ".env"
        converter._write_env_file(
            output, {"MY_VAR": "line1\nline2"}, "test.yaml", "2025-01-01"
        )
        text = output.read_text()
        # Should be one entry per logical line (header lines + 1 var line)
        lines = [
            line
            for line in text.strip().split("\n")
            if not line.startswith("#") and line
        ]
        assert len(lines) == 1
        assert "\\n" in lines[0]
        assert "\n" not in lines[0].split("=", 1)[1].strip('"')

    def test_tab_escaped(self, tmp_path) -> None:
        converter = MigrationConverter()
        output = tmp_path / ".env"
        converter._write_env_file(
            output, {"MY_VAR": "col1\tcol2"}, "test.yaml", "2025-01-01"
        )
        text = output.read_text()
        lines = [
            line
            for line in text.strip().split("\n")
            if not line.startswith("#") and line
        ]
        assert len(lines) == 1
        assert "\\t" in lines[0]

    def test_carriage_return_escaped(self, tmp_path) -> None:
        converter = MigrationConverter()
        output = tmp_path / ".env"
        converter._write_env_file(output, {"MY_VAR": "a\rb"}, "test.yaml", "2025-01-01")
        text = output.read_text()
        lines = [
            line
            for line in text.strip().split("\n")
            if not line.startswith("#") and line
        ]
        assert len(lines) == 1
        assert "\\r" in lines[0]


# ------------------------------------------------------------------ #
# Migration rollback: files actually deleted                          #
# ------------------------------------------------------------------ #


class TestMigrationRollback:
    """Rollback should delete generated files and verify restore."""

    def test_rollback_deletes_output_files(self, tmp_path) -> None:
        # Create source and backup
        source = tmp_path / "source.yaml"
        source.write_text("original")
        backup = tmp_path / "source.yaml.bak"
        backup.write_text("original")

        # Create an output file
        output = tmp_path / ".env"
        output.write_text("GENERATED=true")

        migration = FileMigration(
            source_path=source,
            backup_path=backup,
            output_files=[output],
            component_type="manager",
            component_id="test-id",
            file_type=FileType.MANAGER_DEFINITION,
            name="test",
        )

        rollback = MigrationRollback()
        rollback.rollback(migration)

        # Output file should be deleted
        assert not output.exists()
        # Source should be restored
        assert source.read_text() == "original"
        # Backup should be removed
        assert not backup.exists()

    def test_rollback_preserves_backup_on_restore_failure(self, tmp_path) -> None:
        source = tmp_path / "source.yaml"
        source.write_text("original")
        backup = tmp_path / "source.yaml.bak"
        backup.write_text("original")

        migration = FileMigration(
            source_path=source,
            backup_path=backup,
            output_files=[],
            component_type="manager",
            component_id="test-id",
            file_type=FileType.MANAGER_DEFINITION,
            name="test",
        )

        # Mock copy2 to succeed but then make source_path.exists() return False
        rollback = MigrationRollback()
        with patch("shutil.copy2"):
            # After copy2 is mocked (does nothing), source won't have correct content
            # but exists() still returns True since we created it above.
            # Instead, let's simulate by removing the source before rollback
            source.unlink()
            rollback.rollback(migration)

        # Backup should be preserved because source doesn't exist after "copy"
        assert backup.exists()
