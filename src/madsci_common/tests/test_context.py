"""Unit tests for madsci.common.context module."""

import threading

from madsci.common.context import (
    GlobalMadsciContext,
    get_current_madsci_context,
    madsci_context,
)
from madsci.common.types.context_types import MadsciContext


def test_global_madsci_context_default() -> None:
    """Test that GlobalMadsciContext returns a MadsciContext instance."""
    context = GlobalMadsciContext.get_context()
    assert isinstance(context, MadsciContext)


def test_global_context_across_threads() -> None:
    """Tests that changes to GlobalMadsciContext are consistent across threads."""
    original_context = GlobalMadsciContext.get_context()
    original_url = original_context.lab_server_url
    test_url = "http://test-lab:8000"

    # Create a new context with modified URL
    new_context = original_context.model_copy()
    new_context.lab_server_url = test_url
    GlobalMadsciContext.set_context(new_context)
    assert str(GlobalMadsciContext.get_context().lab_server_url) == "http://test-lab:8000/"

    def check_context() -> None:
        """Function to check context in a separate thread."""
        assert (
            str(GlobalMadsciContext.get_context().lab_server_url)
            == "http://test-lab:8000/"
        )
        # Restore original context
        restore_context = GlobalMadsciContext.get_context().model_copy()
        restore_context.lab_server_url = original_url
        GlobalMadsciContext.set_context(restore_context)

    # Run the check in a separate thread
    thread = threading.Thread(target=check_context)
    thread.start()
    thread.join()
    # Ensure the original state is restored
    final_context = GlobalMadsciContext.get_context().model_copy()
    final_context.lab_server_url = original_url
    GlobalMadsciContext.set_context(final_context)


def test_madsci_context_temporary_override() -> None:
    """Test that madsci_context temporarily overrides and restores context."""
    original_context = GlobalMadsciContext.get_context()
    original_lab_url = original_context.lab_server_url
    original_event_url = original_context.event_server_url
    test_lab_url = "http://test-lab:8000"
    test_event_url = "http://test-event:8001"

    # Ensure we start with known state
    base_context = original_context.model_copy()
    base_context.lab_server_url = original_lab_url
    base_context.event_server_url = original_event_url
    GlobalMadsciContext.set_context(base_context)

    with madsci_context(
        lab_server_url=test_lab_url, event_server_url=test_event_url
    ) as context:
        assert str(context.lab_server_url) == "http://test-lab:8000/"
        assert str(context.event_server_url) == "http://test-event:8001/"
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab:8000/"
        )
        assert (
            str(get_current_madsci_context().event_server_url)
            == "http://test-event:8001/"
        )

    # After context, should be restored
    assert get_current_madsci_context().lab_server_url == original_lab_url
    assert get_current_madsci_context().event_server_url == original_event_url


def test_madsci_context_partial_override() -> None:
    """Test that madsci_context only overrides specified fields."""
    original_context = GlobalMadsciContext.get_context()
    original_lab_url = original_context.lab_server_url
    original_event_url = original_context.event_server_url
    test_lab_url = "http://test-lab:8000"

    # Ensure we start with known state
    base_context = original_context.model_copy()
    base_context.lab_server_url = original_lab_url
    base_context.event_server_url = original_event_url
    GlobalMadsciContext.set_context(base_context)

    with madsci_context(lab_server_url=test_lab_url):
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab:8000/"
        )
        # event_server_url should remain unchanged
        assert get_current_madsci_context().event_server_url == original_event_url

    # After context, should be restored
    assert get_current_madsci_context().lab_server_url == original_lab_url
    assert get_current_madsci_context().event_server_url == original_event_url


def test_get_current_madsci_context() -> None:
    """Test that get_current_madsci_context returns a MadsciContext instance."""
    context = get_current_madsci_context()
    assert isinstance(context, MadsciContext)


def test_nested_madsci_context() -> None:
    """Test that nested context managers work correctly."""
    original_context = GlobalMadsciContext.get_context()
    original_lab_url = original_context.lab_server_url
    original_event_url = original_context.event_server_url
    test_lab_url1 = "http://test-lab1:8000"
    test_lab_url2 = "http://test-lab2:8000"
    test_event_url = "http://test-event:8001"

    # Ensure we start with known state
    base_context = original_context.model_copy()
    base_context.lab_server_url = original_lab_url
    base_context.event_server_url = original_event_url
    GlobalMadsciContext.set_context(base_context)

    with madsci_context(lab_server_url=test_lab_url1, event_server_url=test_event_url):
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab1:8000/"
        )
        assert (
            str(get_current_madsci_context().event_server_url)
            == "http://test-event:8001/"
        )

        with madsci_context(lab_server_url=test_lab_url2):
            # Inner context overrides lab_server_url but keeps event_server_url
            assert (
                str(get_current_madsci_context().lab_server_url)
                == "http://test-lab2:8000/"
            )
            assert (
                str(get_current_madsci_context().event_server_url)
                == "http://test-event:8001/"
            )

        # Back to outer context
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab1:8000/"
        )
        assert (
            str(get_current_madsci_context().event_server_url)
            == "http://test-event:8001/"
        )

    # Back to original context
    assert get_current_madsci_context().lab_server_url == original_lab_url
    assert get_current_madsci_context().event_server_url == original_event_url


def test_madsci_context_with_all_fields() -> None:
    """Test that madsci_context works with all available context fields."""
    original_context = get_current_madsci_context()

    test_values = {
        "lab_server_url": "http://test-lab:8000",
        "event_server_url": "http://test-event:8001",
        "experiment_server_url": "http://test-experiment:8002",
        "data_server_url": "http://test-data:8003",
        "resource_server_url": "http://test-resource:8004",
        "workcell_server_url": "http://test-workcell:8005",
    }

    with madsci_context(**test_values):
        current = get_current_madsci_context()
        # Check that all URLs are set correctly (with trailing slash added by AnyUrl)
        assert str(current.lab_server_url) == "http://test-lab:8000/"
        assert str(current.event_server_url) == "http://test-event:8001/"
        assert str(current.experiment_server_url) == "http://test-experiment:8002/"
        assert str(current.data_server_url) == "http://test-data:8003/"
        assert str(current.resource_server_url) == "http://test-resource:8004/"
        assert str(current.workcell_server_url) == "http://test-workcell:8005/"

    # After context, should be restored
    restored_context = get_current_madsci_context()
    for field in test_values:
        assert getattr(restored_context, field) == getattr(original_context, field)
