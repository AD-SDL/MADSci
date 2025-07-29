"""Provides the OwnershipHandler class for managing global ownership context of objects throughout a MADSci system component."""

import contextlib
import contextvars
from collections.abc import Generator
from typing import Any

from madsci.common.types.auth_types import OwnershipInfo

global_ownership_info = OwnershipInfo()
"""
Global ownership info
To change the ownership info for a system component, set fields on this object.
This is then used by the ownership_context context manager to create temporary ownership contexts as needed.
"""

_current_ownership_info = contextvars.ContextVar(
    "current_ownership_info",
    default=global_ownership_info,
)


@contextlib.contextmanager
def ownership_context(**overrides: Any) -> Generator[None, OwnershipInfo, None]:
    """Updates the current OwnershipInfo (as returned by get_ownership_info) with the provided overrides."""
    prev_info = _current_ownership_info.get()
    info = prev_info.model_copy()
    for k, v in overrides.items():
        setattr(info, k, v)
    token = _current_ownership_info.set(info)
    try:
        yield _current_ownership_info.get()
    finally:
        _current_ownership_info.reset(token)


def get_current_ownership_info() -> OwnershipInfo:
    """Returns the current OwnershipInfo object."""
    return _current_ownership_info.get()
