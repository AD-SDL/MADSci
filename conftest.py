"""Root conftest.py for MADSci test suite.

This file provides fixtures and hooks that apply to all tests across the entire
test suite. Its primary purpose is to prevent resource leaks (particularly file
descriptors) that can cause "Too many open files" errors when running the full
test suite.
"""

import contextlib
import gc
import logging
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, Optional

import pytest


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
