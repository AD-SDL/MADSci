"""Tests for settings directory resolution with walk-up file discovery.

Tests cover:
- resolve_settings_dir resolution chain
- walk_up_find traversal
- resolve_file_paths path resolution
- MadsciBaseSettings integration with _settings_dir
- Backward compatibility (no regressions when walk-up is not opted in)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from madsci.common.settings_dir import (
    _settings_dir_var,
    resolve_file_paths,
    resolve_settings_dir,
    walk_up_find,
)
from madsci.common.types.base_types import MadsciBaseSettings
from madsci.common.types.node_types import NodeConfig, RestNodeConfig
from pydantic import Field, ValidationError
from pydantic_settings import SettingsConfigDict

# ---------------------------------------------------------------------------
# Test helpers / fixtures
# ---------------------------------------------------------------------------


class SimpleSettings(MadsciBaseSettings):
    """Minimal settings class for testing walk-up."""

    model_config = SettingsConfigDict(
        yaml_file="settings.yaml",
        env_prefix="TEST_SIMPLE_",
        env_file=None,
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    greeting: str = Field(default="hello")


class MultiFileSettings(MadsciBaseSettings):
    """Settings class with multiple yaml files (shared + specific)."""

    model_config = SettingsConfigDict(
        yaml_file=("settings.yaml", "app.settings.yaml"),
        env_file=(".env",),
        env_prefix="MULTI_",
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    greeting: str = Field(default="hello")
    app_name: str = Field(default="default-app")
    secret_key: str = Field(default="changeme")


class JsonTestSettings(MadsciBaseSettings):
    """Settings class that reads from JSON files."""

    model_config = SettingsConfigDict(
        json_file="settings.json",
        yaml_file=None,
        env_file=None,
        env_prefix="JSONTEST_",
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    value: str = Field(default="default")


class TomlTestSettings(MadsciBaseSettings):
    """Settings class that reads from TOML files."""

    model_config = SettingsConfigDict(
        toml_file="settings.toml",
        yaml_file=None,
        env_file=None,
        env_prefix="TOMLTEST_",
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    value: str = Field(default="default")


# ---------------------------------------------------------------------------
# TestResolveSettingsDir
# ---------------------------------------------------------------------------


class TestResolveSettingsDir:
    """Unit tests for the resolution chain."""

    def test_kwarg_wins_over_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        kwarg_dir = tmp_path / "kwarg"
        kwarg_dir.mkdir()
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        monkeypatch.setenv("MADSCI_SETTINGS_DIR", str(env_dir))

        result = resolve_settings_dir(kwarg_dir)
        assert result == kwarg_dir.resolve()

    def test_env_var_used_when_no_kwarg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_dir = tmp_path / "from_env"
        env_dir.mkdir()
        monkeypatch.setenv("MADSCI_SETTINGS_DIR", str(env_dir))

        result = resolve_settings_dir(None)
        assert result == env_dir.resolve()

    def test_cwd_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MADSCI_SETTINGS_DIR", raising=False)
        result = resolve_settings_dir(None)
        assert result == Path.cwd().resolve()

    def test_tilde_expansion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MADSCI_SETTINGS_DIR", raising=False)
        result = resolve_settings_dir("~/some_dir")
        assert result == Path("~/some_dir").expanduser().resolve()

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        result = resolve_settings_dir(tmp_path)
        assert result.is_absolute()


# ---------------------------------------------------------------------------
# TestWalkUpFind
# ---------------------------------------------------------------------------


class TestWalkUpFind:
    """Unit tests for walk-up file discovery."""

    def test_finds_file_in_start_directory(self, tmp_path: Path) -> None:
        (tmp_path / "settings.yaml").write_text("greeting: hi\n")
        result = walk_up_find("settings.yaml", tmp_path)
        assert result == (tmp_path / "settings.yaml").resolve()

    def test_walks_up_to_parent(self, tmp_path: Path) -> None:
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: parent\n")
        result = walk_up_find("settings.yaml", child)
        assert result == (tmp_path / "settings.yaml").resolve()

    def test_walks_up_to_grandparent(self, tmp_path: Path) -> None:
        grandchild = tmp_path / "a" / "b"
        grandchild.mkdir(parents=True)
        (tmp_path / "settings.yaml").write_text("greeting: grandparent\n")
        result = walk_up_find("settings.yaml", grandchild)
        assert result == (tmp_path / "settings.yaml").resolve()

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        result = walk_up_find("nonexistent.yaml", tmp_path)
        assert result is None

    def test_respects_max_levels(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (tmp_path / "settings.yaml").write_text("greeting: root\n")
        # max_levels=2 should not reach tmp_path (4 levels up from deep)
        result = walk_up_find("settings.yaml", deep, max_levels=2)
        assert result is None

    def test_finds_within_max_levels(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b"
        deep.mkdir(parents=True)
        (tmp_path / "settings.yaml").write_text("greeting: root\n")
        result = walk_up_find("settings.yaml", deep, max_levels=2)
        assert result == (tmp_path / "settings.yaml").resolve()

    def test_prefers_closest_file(self, tmp_path: Path) -> None:
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: parent\n")
        (child / "settings.yaml").write_text("greeting: child\n")
        result = walk_up_find("settings.yaml", child)
        assert result == (child / "settings.yaml").resolve()

    def test_stops_at_madsci_sentinel(self, tmp_path: Path) -> None:
        """Walk-up should not find files above a .madsci/ sentinel directory."""
        # tmp_path/settings.yaml  <- should NOT be found
        # tmp_path/project/       <- has .madsci/ sentinel
        # tmp_path/project/child/ <- start here
        project = tmp_path / "project"
        child = project / "child"
        child.mkdir(parents=True)
        (project / ".madsci").mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: above-sentinel\n")

        result = walk_up_find("settings.yaml", child)
        assert result is None

    def test_searches_sentinel_directory_itself(self, tmp_path: Path) -> None:
        """The directory containing .madsci/ should still be searched."""
        project = tmp_path / "project"
        child = project / "child"
        child.mkdir(parents=True)
        (project / ".madsci").mkdir()
        (project / "settings.yaml").write_text("greeting: at-sentinel\n")

        result = walk_up_find("settings.yaml", child)
        assert result == (project / "settings.yaml").resolve()

    def test_stops_at_home_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Walk-up should not find files above the home directory."""
        # tmp_path/settings.yaml     <- should NOT be found
        # tmp_path/fakehome/         <- monkeypatched as home
        # tmp_path/fakehome/child/   <- start here
        fakehome = tmp_path / "fakehome"
        child = fakehome / "child"
        child.mkdir(parents=True)
        (tmp_path / "settings.yaml").write_text("greeting: above-home\n")
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = walk_up_find("settings.yaml", child)
        assert result is None

    def test_searches_home_directory_itself(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The home directory itself should be searched before stopping."""
        fakehome = tmp_path / "fakehome"
        child = fakehome / "child"
        child.mkdir(parents=True)
        (fakehome / "settings.yaml").write_text("greeting: at-home\n")
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = walk_up_find("settings.yaml", child)
        assert result == (fakehome / "settings.yaml").resolve()

    def test_stops_at_git_boundary(self, tmp_path: Path) -> None:
        """Walk-up should not find files above a .git/ boundary directory."""
        # tmp_path/settings.yaml  <- should NOT be found
        # tmp_path/project/       <- has .git/
        # tmp_path/project/child/ <- start here
        project = tmp_path / "project"
        child = project / "child"
        child.mkdir(parents=True)
        (project / ".git").mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: above-git\n")

        result = walk_up_find("settings.yaml", child)
        assert result is None

    def test_searches_git_boundary_directory_itself(self, tmp_path: Path) -> None:
        """The directory containing .git/ should still be searched."""
        project = tmp_path / "project"
        child = project / "child"
        child.mkdir(parents=True)
        (project / ".git").mkdir()
        (project / "settings.yaml").write_text("greeting: at-git\n")

        result = walk_up_find("settings.yaml", child)
        assert result == (project / "settings.yaml").resolve()

    def test_madsci_sentinel_takes_priority_over_git(self, tmp_path: Path) -> None:
        """.madsci/ sentinel stops walk-up before .git/ is reached."""
        # tmp_path/.git/            <- secondary boundary
        # tmp_path/project/.madsci/ <- primary boundary
        # tmp_path/project/child/   <- start here
        project = tmp_path / "project"
        child = project / "child"
        child.mkdir(parents=True)
        (project / ".madsci").mkdir()
        (tmp_path / ".git").mkdir()
        (project / "settings.yaml").write_text("greeting: at-madsci\n")

        result = walk_up_find("settings.yaml", child)
        assert result == (project / "settings.yaml").resolve()


# ---------------------------------------------------------------------------
# TestResolveFilePaths
# ---------------------------------------------------------------------------


class TestResolveFilePaths:
    """Unit tests for path resolution."""

    def test_none_input_returns_none(self, tmp_path: Path) -> None:
        assert resolve_file_paths(None, tmp_path) is None

    def test_single_string_input(self, tmp_path: Path) -> None:
        (tmp_path / "settings.yaml").write_text("x: 1\n")
        result = resolve_file_paths("settings.yaml", tmp_path)
        assert result is not None
        assert len(result) == 1
        assert result[0] == (tmp_path / "settings.yaml").resolve()

    def test_tuple_input(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text("x: 1\n")
        (tmp_path / "b.yaml").write_text("y: 2\n")
        result = resolve_file_paths(("a.yaml", "b.yaml"), tmp_path)
        assert result is not None
        assert len(result) == 2

    def test_resolves_each_filename_independently(self, tmp_path: Path) -> None:
        """shared.yaml in parent, specific.yaml in child — both resolved."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "shared.yaml").write_text("x: 1\n")
        (child / "specific.yaml").write_text("y: 2\n")

        result = resolve_file_paths(("shared.yaml", "specific.yaml"), child)
        assert result is not None
        assert result[0] == (tmp_path / "shared.yaml").resolve()
        assert result[1] == (child / "specific.yaml").resolve()

    def test_absolute_paths_unchanged(self, tmp_path: Path) -> None:
        abs_path = tmp_path / "abs.yaml"
        abs_path.write_text("x: 1\n")
        result = resolve_file_paths((str(abs_path),), tmp_path)
        assert result is not None
        assert result[0] == abs_path

    def test_not_found_falls_back_to_settings_dir(self, tmp_path: Path) -> None:
        result = resolve_file_paths("missing.yaml", tmp_path)
        assert result is not None
        assert result[0] == tmp_path / "missing.yaml"


# ---------------------------------------------------------------------------
# TestSettingsDirIntegration
# ---------------------------------------------------------------------------


class TestSettingsDirIntegration:
    """End-to-end tests with real settings classes."""

    def test_walk_up_yaml_shared_in_parent(self, tmp_path: Path) -> None:
        """settings.yaml in parent dir, loaded via walk-up from child."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: from-parent\n")

        settings = SimpleSettings(_settings_dir=child)
        assert settings.greeting == "from-parent"

    def test_walk_up_multi_file(self, tmp_path: Path) -> None:
        """shared settings.yaml in parent, specific app.settings.yaml in child."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: shared\n")
        (child / "app.settings.yaml").write_text("app_name: my-app\n")

        settings = MultiFileSettings(_settings_dir=child)
        assert settings.greeting == "shared"
        assert settings.app_name == "my-app"

    def test_walk_up_dotenv(self, tmp_path: Path) -> None:
        """Walk-up for .env files."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / ".env").write_text("MULTI_SECRET_KEY=from-parent-env\n")

        settings = MultiFileSettings(_settings_dir=child)
        expected = "from-parent-env"
        assert settings.secret_key == expected

    def test_walk_up_json(self, tmp_path: Path) -> None:
        """Walk-up for JSON config files."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.json").write_text('{"value": "from-json"}\n')

        settings = JsonTestSettings(_settings_dir=child)
        assert settings.value == "from-json"

    def test_walk_up_toml(self, tmp_path: Path) -> None:
        """Walk-up for TOML config files."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.toml").write_text('value = "from-toml"\n')

        settings = TomlTestSettings(_settings_dir=child)
        assert settings.value == "from-toml"

    def test_env_var_activation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MADSCI_SETTINGS_DIR env var triggers walk-up."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: via-env-var\n")
        monkeypatch.setenv("MADSCI_SETTINGS_DIR", str(child))

        settings = SimpleSettings()
        assert settings.greeting == "via-env-var"

    def test_init_kwarg_takes_precedence_over_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_settings_dir kwarg wins over MADSCI_SETTINGS_DIR."""
        env_dir = tmp_path / "env_dir"
        env_dir.mkdir()
        kwarg_dir = tmp_path / "kwarg_dir"
        kwarg_dir.mkdir()

        (env_dir / "settings.yaml").write_text("greeting: from-env\n")
        (kwarg_dir / "settings.yaml").write_text("greeting: from-kwarg\n")
        monkeypatch.setenv("MADSCI_SETTINGS_DIR", str(env_dir))

        settings = SimpleSettings(_settings_dir=kwarg_dir)
        assert settings.greeting == "from-kwarg"

    def test_env_vars_override_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Source precedence: env vars still override YAML even with walk-up."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: from-yaml\n")
        monkeypatch.setenv("TEST_SIMPLE_GREETING", "from-env")

        settings = SimpleSettings(_settings_dir=child)
        assert settings.greeting == "from-env"

    def test_node_config_walk_up(self, tmp_path: Path) -> None:
        """NodeConfig with walk-up: settings.yaml in parent, node.settings.yaml in child."""
        lab = tmp_path / "lab"
        node_dir = lab / "nodes" / "arm"
        node_dir.mkdir(parents=True)
        (lab / "settings.yaml").write_text("node_name: from-parent\n")
        (node_dir / "node.settings.yaml").write_text("node_id: arm-001\n")

        config = NodeConfig(_settings_dir=node_dir)
        assert config.node_name == "from-parent"
        assert config.node_id == "arm-001"

    def test_rest_node_config_walk_up(self, tmp_path: Path) -> None:
        """RestNodeConfig with walk-up: settings.yaml in parent, node.settings.yaml in child."""
        lab = tmp_path / "lab"
        node_dir = lab / "nodes" / "arm"
        node_dir.mkdir(parents=True)
        (lab / "settings.yaml").write_text("node_name: from-parent\n")
        (node_dir / "node.settings.yaml").write_text("node_url: http://arm:8080/\n")

        config = RestNodeConfig(_settings_dir=node_dir)
        assert config.node_name == "from-parent"
        assert str(config.node_url) == "http://arm:8080/"

    def test_contextvar_does_not_leak(self, tmp_path: Path) -> None:
        """ContextVar is reset after __init__, even on success."""
        (tmp_path / "settings.yaml").write_text("greeting: test\n")

        SimpleSettings(_settings_dir=tmp_path)
        assert _settings_dir_var.get() is None

    def test_contextvar_does_not_leak_on_error(self, tmp_path: Path) -> None:
        """ContextVar is reset even when __init__ raises."""

        class BadSettings(MadsciBaseSettings):
            model_config = SettingsConfigDict(
                yaml_file="settings.yaml",
                env_file=None,
                extra="forbid",
                cli_parse_args=False,
            )
            required_field: str  # No default — will fail without value

        with pytest.raises(ValidationError):
            BadSettings(_settings_dir=tmp_path)

        assert _settings_dir_var.get() is None

    def test_child_dir_yaml_overrides_parent(self, tmp_path: Path) -> None:
        """If the same file exists in both child and parent, child wins (closest)."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "settings.yaml").write_text("greeting: parent\n")
        (child / "settings.yaml").write_text("greeting: child\n")

        settings = SimpleSettings(_settings_dir=child)
        assert settings.greeting == "child"


# ---------------------------------------------------------------------------
# TestBackwardCompatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Verify no regressions when walk-up is not opted in."""

    def test_cwd_yaml_still_works(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """monkeypatch.chdir + settings.yaml in CWD still works without _settings_dir."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MADSCI_SETTINGS_DIR", raising=False)
        (tmp_path / "settings.yaml").write_text("greeting: from-cwd\n")

        settings = SimpleSettings()
        assert settings.greeting == "from-cwd"

    def test_no_config_files_works(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Settings with no config files, no _settings_dir — uses defaults."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MADSCI_SETTINGS_DIR", raising=False)

        settings = SimpleSettings()
        assert settings.greeting == "hello"

    def test_settings_with_env_file_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings class with env_file=None — unaffected."""
        monkeypatch.delenv("MADSCI_SETTINGS_DIR", raising=False)

        class NoEnvSettings(MadsciBaseSettings):
            model_config = SettingsConfigDict(
                env_file=None,
                yaml_file=None,
                env_prefix="NOENV_",
                validate_default=True,
                extra="ignore",
                cli_parse_args=False,
            )
            val: str = Field(default="default")

        settings = NoEnvSettings()
        assert settings.val == "default"

    def test_in_memory_kwargs_still_work(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Constructor kwargs without _settings_dir work as before."""
        monkeypatch.delenv("MADSCI_SETTINGS_DIR", raising=False)

        settings = SimpleSettings(greeting="custom")
        assert settings.greeting == "custom"


# ---------------------------------------------------------------------------
# Extra search dirs — test helpers
# ---------------------------------------------------------------------------


class ManagerLikeSettings(MadsciBaseSettings):
    """Settings class that searches managers/ and config/ subdirs."""

    _extra_search_dirs = ("managers", "config")

    model_config = SettingsConfigDict(
        yaml_file="mgr.settings.yaml",
        env_prefix="MGRLIKE_",
        env_file=None,
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    port: int = Field(default=8000)


class NoExtraDirsSettings(MadsciBaseSettings):
    """Settings class without extra search dirs (default behaviour)."""

    model_config = SettingsConfigDict(
        yaml_file="mgr.settings.yaml",
        env_prefix="NOEXTRA_",
        env_file=None,
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    port: int = Field(default=8000)


class ExtraJsonSettings(MadsciBaseSettings):
    """Settings class with extra dirs reading JSON."""

    _extra_search_dirs = ("managers",)

    model_config = SettingsConfigDict(
        json_file="mgr.settings.json",
        yaml_file=None,
        env_file=None,
        env_prefix="EXTRAJSON_",
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    port: int = Field(default=8000)


class ExtraTomlSettings(MadsciBaseSettings):
    """Settings class with extra dirs reading TOML."""

    _extra_search_dirs = ("managers",)

    model_config = SettingsConfigDict(
        toml_file="mgr.settings.toml",
        yaml_file=None,
        env_file=None,
        env_prefix="EXTRATOML_",
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    port: int = Field(default=8000)


class ExtraEnvSettings(MadsciBaseSettings):
    """Settings class with extra dirs reading .env."""

    _extra_search_dirs = ("managers",)

    model_config = SettingsConfigDict(
        env_file="mgr.env",
        yaml_file=None,
        env_prefix="EXTRAENV_",
        validate_default=True,
        extra="ignore",
        cli_parse_args=False,
    )

    port: int = Field(default=8000)


# ---------------------------------------------------------------------------
# TestExtraSearchDirs
# ---------------------------------------------------------------------------


class TestExtraSearchDirs:
    """Tests for the extra_search_dirs parameter on resolve_file_paths
    and its integration with MadsciBaseSettings._extra_search_dirs."""

    # ---- Unit tests on resolve_file_paths ----

    def test_file_found_in_extra_subdir(self, tmp_path: Path) -> None:
        """File in settings_dir/managers/ is found via extra_search_dirs."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (mgr_dir / "mgr.settings.yaml").write_text("port: 9000\n")

        result = resolve_file_paths(
            "mgr.settings.yaml", tmp_path, extra_search_dirs=("managers",)
        )
        assert result is not None
        assert result[0] == (mgr_dir / "mgr.settings.yaml").resolve()

    def test_first_extra_dir_wins(self, tmp_path: Path) -> None:
        """When file exists in multiple extra dirs, first match wins."""
        mgr_dir = tmp_path / "managers"
        cfg_dir = tmp_path / "config"
        mgr_dir.mkdir()
        cfg_dir.mkdir()
        (mgr_dir / "settings.yaml").write_text("port: 1111\n")
        (cfg_dir / "settings.yaml").write_text("port: 2222\n")

        result = resolve_file_paths(
            "settings.yaml", tmp_path, extra_search_dirs=("managers", "config")
        )
        assert result is not None
        assert result[0] == (mgr_dir / "settings.yaml").resolve()

    def test_walk_up_takes_priority_over_extra_dirs(self, tmp_path: Path) -> None:
        """Walk-up discovery wins over extra_search_dirs."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (tmp_path / "settings.yaml").write_text("port: 5555\n")
        (mgr_dir / "settings.yaml").write_text("port: 6666\n")

        result = resolve_file_paths(
            "settings.yaml", tmp_path, extra_search_dirs=("managers",)
        )
        assert result is not None
        # Walk-up finds it in tmp_path itself, so extra dirs are skipped
        assert result[0] == (tmp_path / "settings.yaml").resolve()

    def test_extra_dirs_ignored_when_walk_up_finds(self, tmp_path: Path) -> None:
        """Extra dirs are only consulted when walk-up returns None."""
        child = tmp_path / "child"
        child.mkdir()
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (tmp_path / "settings.yaml").write_text("port: 7777\n")
        (mgr_dir / "settings.yaml").write_text("port: 8888\n")

        # Start from child; walk-up will find settings.yaml in tmp_path
        result = resolve_file_paths(
            "settings.yaml", child, extra_search_dirs=("managers",)
        )
        assert result is not None
        assert result[0] == (tmp_path / "settings.yaml").resolve()

    def test_empty_extra_dirs_unchanged(self, tmp_path: Path) -> None:
        """Empty extra_search_dirs = current behaviour (fallback to settings_dir / name)."""
        result = resolve_file_paths("missing.yaml", tmp_path, extra_search_dirs=())
        assert result is not None
        assert result[0] == tmp_path / "missing.yaml"

    def test_extra_dir_does_not_exist(self, tmp_path: Path) -> None:
        """Non-existent extra dir is silently skipped."""
        result = resolve_file_paths(
            "missing.yaml", tmp_path, extra_search_dirs=("nonexistent",)
        )
        assert result is not None
        assert result[0] == tmp_path / "missing.yaml"

    # ---- Integration tests with settings classes ----

    def test_manager_like_settings_finds_subdir(self, tmp_path: Path) -> None:
        """Settings class with _extra_search_dirs finds file in managers/."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (mgr_dir / "mgr.settings.yaml").write_text("port: 9001\n")

        settings = ManagerLikeSettings(_settings_dir=tmp_path)
        assert settings.port == 9001

    def test_no_extra_dirs_does_not_find_subdir(self, tmp_path: Path) -> None:
        """Settings class without _extra_search_dirs does NOT find subdir files."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (mgr_dir / "mgr.settings.yaml").write_text("port: 9002\n")

        settings = NoExtraDirsSettings(_settings_dir=tmp_path)
        # Falls back to default because the file is not discovered
        assert settings.port == 8000

    def test_shared_yaml_plus_subdir_both_loaded(self, tmp_path: Path) -> None:
        """Shared settings.yaml in CWD + manager-specific file in managers/."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()

        class CombinedSettings(MadsciBaseSettings):
            _extra_search_dirs = ("managers",)

            model_config = SettingsConfigDict(
                yaml_file=("settings.yaml", "mgr.settings.yaml"),
                env_prefix="COMBINED_",
                env_file=None,
                validate_default=True,
                extra="ignore",
                cli_parse_args=False,
            )

            greeting: str = Field(default="hello")
            port: int = Field(default=8000)

        (tmp_path / "settings.yaml").write_text("greeting: shared\n")
        (mgr_dir / "mgr.settings.yaml").write_text("port: 9003\n")

        settings = CombinedSettings(_settings_dir=tmp_path)
        assert settings.greeting == "shared"
        assert settings.port == 9003

    def test_config_subdir_works(self, tmp_path: Path) -> None:
        """Second extra_search_dir 'config' is found when managers/ has no file."""
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "mgr.settings.yaml").write_text("port: 9004\n")

        settings = ManagerLikeSettings(_settings_dir=tmp_path)
        assert settings.port == 9004

    def test_extra_dirs_json(self, tmp_path: Path) -> None:
        """Extra search dirs work for JSON config files."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (mgr_dir / "mgr.settings.json").write_text('{"port": 9005}\n')

        settings = ExtraJsonSettings(_settings_dir=tmp_path)
        assert settings.port == 9005

    def test_extra_dirs_toml(self, tmp_path: Path) -> None:
        """Extra search dirs work for TOML config files."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (mgr_dir / "mgr.settings.toml").write_text("port = 9006\n")

        settings = ExtraTomlSettings(_settings_dir=tmp_path)
        assert settings.port == 9006

    def test_extra_dirs_env(self, tmp_path: Path) -> None:
        """Extra search dirs work for .env files."""
        mgr_dir = tmp_path / "managers"
        mgr_dir.mkdir()
        (mgr_dir / "mgr.env").write_text("EXTRAENV_PORT=9007\n")

        settings = ExtraEnvSettings(_settings_dir=tmp_path)
        assert settings.port == 9007
