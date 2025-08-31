"""Unit tests for madsci.common.warnings module."""

from madsci.common.warnings import MadsciLocalOnlyWarning


def test_madsci_local_only_warning_creation():
    """Test creating MadsciLocalOnlyWarning."""
    message = "This is a test warning message"
    warning = MadsciLocalOnlyWarning(message)

    assert isinstance(warning, Warning)
    assert warning.message == message
    assert str(warning) == message


def test_madsci_local_only_warning_inheritance():
    """Test that MadsciLocalOnlyWarning inherits from Warning."""
    warning = MadsciLocalOnlyWarning("test")
    assert isinstance(warning, Warning)


def test_madsci_local_only_warning_with_empty_message():
    """Test MadsciLocalOnlyWarning with empty message."""
    warning = MadsciLocalOnlyWarning("")
    assert warning.message == ""
    assert str(warning) == ""


def test_madsci_local_only_warning_with_multiline_message():
    """Test MadsciLocalOnlyWarning with multiline message."""
    message = "Line 1\nLine 2\nLine 3"
    warning = MadsciLocalOnlyWarning(message)
    assert warning.message == message
    assert str(warning) == message
