"""Tests that run all tutorial YAML definitions."""

from pathlib import Path

import pytest
from madsci.common.testing.runner import E2ETestRunner
from madsci.common.testing.types import E2ETestDefinition, TestMode


def get_tutorial_files(tutorials_dir: Path) -> list[Path]:
    """Get all tutorial YAML files."""
    return list(tutorials_dir.glob("*.tutorial.yaml"))


def should_skip_tutorial(
    test_def: E2ETestDefinition,
    tutorial_filter: str | None,
    docker_enabled: bool,
) -> tuple[bool, str]:
    """
    Determine if a tutorial should be skipped.

    Returns:
        Tuple of (should_skip, reason)
    """
    # Check tag filter
    if tutorial_filter and tutorial_filter not in test_def.tags:
        return True, f"Tutorial does not have tag '{tutorial_filter}'"

    # Check Docker requirement
    if test_def.requirements.docker and not docker_enabled:
        return True, "Tutorial requires Docker (use --docker-enabled)"

    if test_def.mode == TestMode.DOCKER and not docker_enabled:
        return True, "Tutorial requires Docker mode (use --docker-enabled)"

    return False, ""


class TestTutorials:
    """Test class for running tutorial definitions."""

    @pytest.fixture(scope="class")
    def tutorial_files(self, tutorials_dir: Path) -> list[Path]:
        """Get all tutorial files."""
        return get_tutorial_files(tutorials_dir)

    def test_tutorials_exist(self, tutorial_files: list[Path]):
        """Verify that tutorial files exist."""
        assert len(tutorial_files) > 0, "No tutorial files found"

    def test_tutorials_parse(self, tutorial_files: list[Path]):
        """Verify that all tutorial files parse correctly."""
        for tutorial_path in tutorial_files:
            test_def = E2ETestDefinition.from_yaml(tutorial_path)
            assert test_def.name, f"Tutorial {tutorial_path} has no name"
            assert len(test_def.steps) > 0, f"Tutorial {tutorial_path} has no steps"


@pytest.mark.parametrize(
    "tutorial_file",
    get_tutorial_files(Path(__file__).parent / "tutorials"),
    ids=lambda p: p.stem,
)
def test_tutorial(
    tutorial_file: Path,
    e2e_runner: E2ETestRunner,
    tutorial_filter: str | None,
    docker_enabled: bool,
):
    """
    Run a single tutorial test.

    This test is parametrized to run each tutorial file found in the
    tutorials directory.
    """
    test_def = E2ETestDefinition.from_yaml(tutorial_file)

    # Check if should skip
    skip, reason = should_skip_tutorial(test_def, tutorial_filter, docker_enabled)
    if skip:
        pytest.skip(reason)

    # Run the tutorial
    result = e2e_runner.run(test_def)

    # Assert success
    assert result.passed, f"Tutorial '{test_def.name}' failed:\n{result.summary()}"


class TestBasicTutorial:
    """Test the basic tutorial specifically."""

    def test_basic_tutorial_runs(
        self,
        tutorials_dir: Path,
        e2e_runner: E2ETestRunner,
    ):
        """Run the basic tutorial test."""
        tutorial_path = tutorials_dir / "basic_test.tutorial.yaml"
        if not tutorial_path.exists():
            pytest.skip("Basic tutorial not found")

        test_def = E2ETestDefinition.from_yaml(tutorial_path)
        result = e2e_runner.run(test_def)

        assert result.passed, f"Basic tutorial failed:\n{result.summary()}"
        assert result.steps_passed >= 4, "Expected at least 4 steps to pass"
