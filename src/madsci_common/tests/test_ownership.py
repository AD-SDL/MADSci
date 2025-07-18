"""Unit tests for madsci.common.ownership module."""

import threading

from madsci.common.ownership import (
    get_current_ownership_info,
    global_ownership_info,
    ownership_context,
)
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.utils import new_ulid_str


def test_global_ownership_info_default() -> None:
    """Test that global_ownership_info is an instance of OwnershipInfo by default."""
    assert isinstance(global_ownership_info, OwnershipInfo)


def test_global_ownership_across_threads() -> None:
    """Tests that changes to global_ownership_info are consistent across threads."""
    original_id = getattr(global_ownership_info, "node_id", None)
    test_id = new_ulid_str()
    global_ownership_info.node_id = test_id
    assert global_ownership_info.node_id == test_id

    def check_ownership() -> bool:
        """Function to check ownership in a separate thread."""
        assert global_ownership_info.node_id == test_id
        global_ownership_info.node_id = original_id

    # Run the check in a separate thread
    thread = threading.Thread(target=check_ownership)
    thread.start()
    thread.join()
    # Ensure the original state is restored
    global_ownership_info.node_id = original_id


def test_ownership_context_temporary_override() -> None:
    """Test that ownership_context temporarily overrides and restores ownership info."""
    original_id = getattr(global_ownership_info, "node_id", None)
    test_id = new_ulid_str()
    global_ownership_info.node_id = original_id
    with ownership_context(node_id=test_id) as info:
        assert info.node_id == test_id
        assert get_current_ownership_info().node_id == test_id
    # After context, should be restored
    assert get_current_ownership_info().node_id == original_id


def test_get_current_ownership_info() -> None:
    """Test that get_current_ownership_info returns an OwnershipInfo instance."""
    info = get_current_ownership_info()
    assert isinstance(info, OwnershipInfo)
