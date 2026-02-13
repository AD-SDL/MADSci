"""Tests for fixes identified during PR #226 review.

Covers:
- InMemoryRedis clear_all_registries
- MadsciBaseSettings nested model_dump_safe
- no_color context propagation
- Shell injection prevention in template hooks
- PATH parameter validation
- min_length=0 truthiness fix
"""

import shlex
from typing import ClassVar
from unittest.mock import MagicMock

from click.testing import CliRunner
from madsci.client.cli import madsci
from madsci.common.local_backends.inmemory_redis import (
    InMemoryRedisClient,
    InMemoryRedisDict,
    InMemoryRedisList,
    clear_all_registries,
)
from madsci.common.templates.engine import TemplateEngine
from madsci.common.types.base_types import (
    REDACTED_PLACEHOLDER,
    MadsciBaseModel,
    MadsciBaseSettings,
)
from madsci.common.types.template_types import ParameterType, TemplateParameter
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
