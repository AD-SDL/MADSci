"""Root conftest.py for MADSci test suite.

This file provides fixtures and hooks that apply to all tests across the entire
test suite. Its primary purpose is to prevent resource leaks (particularly file
descriptors) that can cause "Too many open files" errors when running the full
test suite.
"""

import contextlib
import gc
import logging
import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, Optional

import pytest


def _patch_field_default_recursive(cls: type, field_name: str, value: object) -> None:
    """Patch a Pydantic field default on a class and all its subclasses.

    Pydantic v2 gives each subclass its own copy of ``model_fields``, so
    patching the parent's ``FieldInfo.default`` does NOT propagate.  We
    must walk the entire subclass tree and patch each one individually.
    """
    field = cls.model_fields.get(field_name)
    if field is not None:
        field.default = value
    with contextlib.suppress(Exception):
        cls.model_rebuild(force=True)
    for sub in cls.__subclasses__():
        _patch_field_default_recursive(sub, field_name, value)


@pytest.fixture(autouse=True, scope="session")
def _isolate_registry_global(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[None, None, None]:
    """Session-scoped safety net: isolate all tests from the real registry.

    This fixture:
    1. Points ``MADSCI_REGISTRY_PATH`` at a temp file so no test touches the
       real ``~/.madsci/registry.json``.
    2. Monkeypatches the default value of ``enable_registry_resolution`` on
       both ``ManagerSettings`` and ``NodeConfig`` to ``False``, preventing
       registry file-lock contention and heartbeat-thread spawning in tests.

    Individual tests that *need* registry behaviour should explicitly pass
    ``enable_registry_resolution=True`` and use the ``isolated_registry``
    fixture for a per-test registry path.
    """
    from madsci.common.types.manager_types import ManagerSettings  # noqa: PLC0415
    from madsci.common.types.node_types import NodeConfig  # noqa: PLC0415

    # 1. Redirect all registry I/O to a throwaway temp file.
    tmp_registry = tmp_path_factory.mktemp("registry") / "registry.json"
    old_env = os.environ.get("MADSCI_REGISTRY_PATH")
    os.environ["MADSCI_REGISTRY_PATH"] = str(tmp_registry)

    # 2. Patch field defaults so that newly-created settings objects default to
    #    registry resolution *off* (belt-and-suspenders with the explicit
    #    ``enable_registry_resolution=False`` added to each test file).
    orig_manager_default = ManagerSettings.model_fields[
        "enable_registry_resolution"
    ].default
    orig_node_default = NodeConfig.model_fields["enable_registry_resolution"].default

    # Patch the field default on the base class AND every subclass, then
    # rebuild all of them so Pydantic picks up the change.
    _patch_field_default_recursive(ManagerSettings, "enable_registry_resolution", False)
    _patch_field_default_recursive(NodeConfig, "enable_registry_resolution", False)

    yield

    # Teardown: restore originals.
    _patch_field_default_recursive(
        ManagerSettings, "enable_registry_resolution", orig_manager_default
    )
    _patch_field_default_recursive(
        NodeConfig, "enable_registry_resolution", orig_node_default
    )

    if old_env is None:
        os.environ.pop("MADSCI_REGISTRY_PATH", None)
    else:
        os.environ["MADSCI_REGISTRY_PATH"] = old_env


@pytest.fixture()
def isolated_registry(tmp_path: Path) -> Generator[Path, None, None]:
    """Per-test isolated registry path.

    Use this fixture in tests that specifically need to exercise registry
    behaviour.  It sets ``MADSCI_REGISTRY_PATH`` to a unique temp file
    for the duration of the test and restores the previous value on teardown.
    """
    registry_path = tmp_path / "registry.json"
    old_env = os.environ.get("MADSCI_REGISTRY_PATH")
    os.environ["MADSCI_REGISTRY_PATH"] = str(registry_path)

    yield registry_path

    if old_env is None:
        os.environ.pop("MADSCI_REGISTRY_PATH", None)
    else:
        os.environ["MADSCI_REGISTRY_PATH"] = old_env


@pytest.fixture(autouse=True, scope="module")
def cleanup_resources_after_module() -> Generator[None, None, None]:
    """Clean up resources after each test module to prevent file descriptor leaks.

    Uses module scope to reduce overhead while still preventing "too many open files"
    errors. Resources are cleaned up after each test module completes rather than
    after every individual test.

    This fixture ensures:
    1. All logging handlers are closed and removed
    2. Temporary files created during the module are cleaned up
    3. Garbage collection is triggered to clean up any remaining resources
    """
    # Track temp files before module
    temp_dir = Path(tempfile.gettempdir())
    before_files = set(temp_dir.glob("tmp*"))

    yield

    # Clean up logging handlers from all loggers
    # This is critical because EventClient creates file handlers that need to be closed
    _cleanup_all_logging_handlers()

    # Clean up new temp files created during the module
    after_files = set(temp_dir.glob("tmp*"))
    new_files = after_files - before_files
    for filepath in new_files:
        with contextlib.suppress(Exception):
            if filepath.is_file():
                filepath.unlink()
            elif filepath.is_dir():
                shutil.rmtree(filepath, ignore_errors=True)

    # Force garbage collection to clean up unreferenced objects
    # This helps ensure __del__ methods are called on orphaned EventClients
    gc.collect()


def _cleanup_all_logging_handlers() -> None:
    """Close and remove all handlers from all loggers.

    This ensures that file handlers created by EventClient instances are
    properly closed, preventing file descriptor leaks.
    """
    # Get all loggers including the root logger
    loggers: list[logging.Logger] = [logging.getLogger()]  # Root logger

    # Get all named loggers from the logger manager
    logger_dict = logging.Logger.manager.loggerDict
    for name in list(logger_dict.keys()):
        logger_obj = logger_dict.get(name)
        if isinstance(logger_obj, logging.Logger):
            loggers.append(logger_obj)

    # Close and remove handlers from all loggers
    for logger in loggers:
        if not hasattr(logger, "handlers"):
            continue
        handlers = logger.handlers[:]
        for handler in handlers:
            with contextlib.suppress(Exception):
                handler.close()
                logger.removeHandler(handler)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item: Any, nextitem: Optional[Any]) -> None:
    """Hook that runs after each test teardown.

    This provides additional cleanup opportunity after pytest's normal
    teardown process completes. Only runs gc.collect() periodically to
    reduce overhead while still preventing resource leaks.
    """
    # Only run gc.collect() when transitioning between modules to reduce overhead
    # nextitem is None when this is the last test, or we check if module changed
    if nextitem is None or (
        hasattr(item, "module")
        and hasattr(nextitem, "module")
        and item.module != nextitem.module
    ):
        gc.collect()
