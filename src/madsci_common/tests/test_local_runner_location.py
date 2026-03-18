"""Tests for LocalRunner location manager handler setup."""

from madsci.common.local_backends.local_runner import LocalRunner


def test_local_runner_location_manager_has_both_handlers():
    """Verify LocalRunner creates a document handler for the location manager."""
    runner = LocalRunner()
    assert hasattr(runner, "_location_document_handler")
    assert runner._location_document_handler is not None
    assert hasattr(runner, "_cache_handler")
    assert runner._cache_handler is not None
