"""Tests for the .madsci/ sentry directory resolution module.

Tests cover:
- find_madsci_dir walk-up, boundaries, fallback
- get_madsci_subdir creation and delegation
- ensure_madsci_dir scaffolding
- get_global_madsci_subdir home-only behaviour
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from madsci.common.sentry import (
    REGISTRY_FILE,
    SENTRY_DIR_NAME,
    STANDARD_SUBDIRS,
    ensure_madsci_dir,
    find_madsci_dir,
    get_global_madsci_subdir,
    get_madsci_subdir,
)

# ---------------------------------------------------------------------------
# find_madsci_dir
# ---------------------------------------------------------------------------


class TestFindMadsciDir:
    """Tests for the canonical .madsci/ resolution function."""

    def test_finds_madsci_in_start_dir(self, tmp_path: Path) -> None:
        """Direct .madsci/ in start_dir is found immediately."""
        (tmp_path / SENTRY_DIR_NAME).mkdir()
        result = find_madsci_dir(tmp_path)
        assert result == tmp_path / SENTRY_DIR_NAME

    def test_walks_up_to_find_madsci(self, tmp_path: Path) -> None:
        """Walk up from child to find .madsci/ in parent."""
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)
        (tmp_path / SENTRY_DIR_NAME).mkdir()

        result = find_madsci_dir(child)
        assert result == tmp_path / SENTRY_DIR_NAME

    def test_stops_at_madsci_sentinel(self, tmp_path: Path) -> None:
        """Walk-up stops at the first .madsci/ found."""
        project = tmp_path / "project"
        child = project / "sub"
        child.mkdir(parents=True)
        (project / SENTRY_DIR_NAME).mkdir()
        # Another .madsci/ higher up should not be found
        (tmp_path / SENTRY_DIR_NAME).mkdir()

        result = find_madsci_dir(child)
        assert result == project / SENTRY_DIR_NAME

    def test_git_boundary_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no .madsci/ exists, .git/ serves as a boundary."""
        fakehome = tmp_path / "fakehome"
        project = fakehome / "project"
        child = project / "sub"
        child.mkdir(parents=True)
        (project / ".git").mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = find_madsci_dir(child)
        assert result == project / SENTRY_DIR_NAME

    def test_madsci_takes_priority_over_git(self, tmp_path: Path) -> None:
        """.madsci/ takes priority over .git/ when both exist."""
        project = tmp_path / "project"
        child = project / "sub"
        child.mkdir(parents=True)
        (project / SENTRY_DIR_NAME).mkdir()
        (project / ".git").mkdir()

        result = find_madsci_dir(child)
        assert result == project / SENTRY_DIR_NAME

    def test_falls_back_to_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to ~/.madsci/ when neither .madsci/ nor .git/ found."""
        fakehome = tmp_path / "fakehome"
        child = fakehome / "project" / "sub"
        child.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = find_madsci_dir(child)
        assert result == fakehome / SENTRY_DIR_NAME

    def test_respects_max_levels(self, tmp_path: Path) -> None:
        """max_levels limits how far up the walk goes."""
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (tmp_path / SENTRY_DIR_NAME).mkdir()

        # max_levels=2 should not reach tmp_path (4 levels up)
        result = find_madsci_dir(deep, max_levels=2)
        # Should fall back to home
        assert result == Path.home() / SENTRY_DIR_NAME

    def test_respects_home_boundary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Walk-up stops at home directory."""
        fakehome = tmp_path / "fakehome"
        child = fakehome / "project"
        child.mkdir(parents=True)
        # .madsci/ above home — should not be found via walk-up
        (tmp_path / SENTRY_DIR_NAME).mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = find_madsci_dir(child)
        # Falls back to ~/.madsci/ (not the one above home)
        assert result == fakehome / SENTRY_DIR_NAME

    def test_respects_settings_dir_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MADSCI_SETTINGS_DIR env var overrides CWD as start."""
        project = tmp_path / "my_project"
        project.mkdir()
        (project / SENTRY_DIR_NAME).mkdir()
        monkeypatch.setenv("MADSCI_SETTINGS_DIR", str(project))

        result = find_madsci_dir()
        assert result == project / SENTRY_DIR_NAME

    def test_auto_create_creates_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """auto_create=True creates the .madsci/ dir when not found."""
        fakehome = tmp_path / "fakehome"
        fakehome.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = find_madsci_dir(fakehome, auto_create=True)
        assert result == fakehome / SENTRY_DIR_NAME
        assert result.is_dir()

    def test_auto_create_false_does_not_create(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """auto_create=False does not create directories."""
        fakehome = tmp_path / "fakehome"
        fakehome.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = find_madsci_dir(fakehome, auto_create=False)
        assert result == fakehome / SENTRY_DIR_NAME
        assert not result.is_dir()

    def test_git_boundary_auto_create(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """auto_create creates .madsci/ when inferred from .git/ boundary."""
        fakehome = tmp_path / "fakehome"
        project = fakehome / "project"
        project.mkdir(parents=True)
        (project / ".git").mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = find_madsci_dir(project, auto_create=True)
        assert result == project / SENTRY_DIR_NAME
        assert result.is_dir()


# ---------------------------------------------------------------------------
# get_madsci_subdir
# ---------------------------------------------------------------------------


class TestGetMadsciSubdir:
    """Tests for subdirectory resolution."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        (tmp_path / SENTRY_DIR_NAME).mkdir()
        result = get_madsci_subdir("pids", tmp_path)
        assert result == tmp_path / SENTRY_DIR_NAME / "pids"

    def test_creates_when_create_true(self, tmp_path: Path) -> None:
        (tmp_path / SENTRY_DIR_NAME).mkdir()
        result = get_madsci_subdir("pids", tmp_path, create=True)
        assert result.is_dir()

    def test_does_not_create_when_create_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fakehome = tmp_path / "fakehome"
        fakehome.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = get_madsci_subdir("pids", tmp_path, create=False)
        assert not result.is_dir()


# ---------------------------------------------------------------------------
# ensure_madsci_dir
# ---------------------------------------------------------------------------


class TestEnsureMadsciDir:
    """Tests for .madsci/ scaffolding."""

    def test_creates_standard_subdirs(self, tmp_path: Path) -> None:
        result = ensure_madsci_dir(tmp_path)
        assert result == tmp_path / SENTRY_DIR_NAME
        assert result.is_dir()
        for subdir in STANDARD_SUBDIRS:
            assert (result / subdir).is_dir()

    def test_creates_registry_json(self, tmp_path: Path) -> None:
        result = ensure_madsci_dir(tmp_path)
        registry_path = result / REGISTRY_FILE
        assert registry_path.exists()
        data = json.loads(registry_path.read_text())
        assert "entries" in data

    def test_idempotent(self, tmp_path: Path) -> None:
        """Calling twice should be safe."""
        result1 = ensure_madsci_dir(tmp_path)
        # Write something to registry to verify it's not overwritten
        registry_path = result1 / REGISTRY_FILE
        custom = {"entries": {"test": "value"}}
        registry_path.write_text(json.dumps(custom))

        result2 = ensure_madsci_dir(tmp_path)
        assert result2 == result1
        # Registry should NOT be overwritten since it already existed
        data = json.loads(registry_path.read_text())
        assert data == custom


# ---------------------------------------------------------------------------
# get_global_madsci_subdir
# ---------------------------------------------------------------------------


class TestGetGlobalMadsciSubdir:
    """Tests for the global (home-only) variant."""

    def test_uses_home_regardless_of_sentinel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should always use ~/.madsci/, ignoring any project sentinels."""
        fakehome = tmp_path / "fakehome"
        fakehome.mkdir()
        project = tmp_path / "project"
        project.mkdir()
        (project / SENTRY_DIR_NAME).mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = get_global_madsci_subdir("templates", create=True)
        assert result == fakehome / SENTRY_DIR_NAME / "templates"
        assert result.is_dir()

    def test_does_not_create_when_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fakehome = tmp_path / "fakehome"
        fakehome.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fakehome))

        result = get_global_madsci_subdir("templates", create=False)
        assert result == fakehome / SENTRY_DIR_NAME / "templates"
        assert not result.is_dir()
