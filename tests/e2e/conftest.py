"""Pytest configuration for E2E tests."""

from pathlib import Path

import pytest
from madsci.common.testing.runner import E2ETestRunner
from madsci.common.testing.types import TestMode


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom pytest options for E2E tests."""
    parser.addoption(
        "--e2e-mode",
        action="store",
        default="python",
        choices=["python", "docker", "hybrid"],
        help="Execution mode for E2E tests",
    )
    parser.addoption(
        "--e2e-verbose",
        action="store_true",
        default=False,
        help="Enable verbose output for E2E tests",
    )
    parser.addoption(
        "--tutorial-filter",
        action="store",
        default=None,
        help="Filter tutorials by tag (e.g., 'no-docker')",
    )
    parser.addoption(
        "--docker-enabled",
        action="store_true",
        default=False,
        help="Enable Docker-based tests",
    )


@pytest.fixture(scope="session")
def e2e_mode(request: pytest.FixtureRequest) -> TestMode:
    """Get the E2E test mode from command line."""
    mode_str = request.config.getoption("--e2e-mode")
    return TestMode(mode_str)


@pytest.fixture(scope="session")
def e2e_verbose(request: pytest.FixtureRequest) -> bool:
    """Get verbose flag from command line."""
    return request.config.getoption("--e2e-verbose")


@pytest.fixture(scope="session")
def docker_enabled(request: pytest.FixtureRequest) -> bool:
    """Check if Docker tests are enabled."""
    return request.config.getoption("--docker-enabled")


@pytest.fixture(scope="session")
def tutorial_filter(request: pytest.FixtureRequest) -> str | None:
    """Get tutorial filter from command line."""
    return request.config.getoption("--tutorial-filter")


@pytest.fixture
def e2e_runner(tmp_path: Path, e2e_mode: TestMode, e2e_verbose: bool) -> E2ETestRunner:
    """Create an E2E test runner."""
    return E2ETestRunner(
        working_dir=tmp_path,
        mode=e2e_mode,
        verbose=e2e_verbose,
    )


@pytest.fixture(scope="session")
def tutorials_dir() -> Path:
    """Get the tutorials directory."""
    return Path(__file__).parent / "tutorials"


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """
    Modify test collection to skip Docker tests when not enabled.
    """
    docker_enabled = config.getoption("--docker-enabled")

    if not docker_enabled:
        skip_docker = pytest.mark.skip(
            reason="Docker tests not enabled (use --docker-enabled)"
        )
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)
