"""Provides the OwnershipHandler class for managing global ownership context of objects throughout a MADSci system component."""

import contextlib
import contextvars
from collections.abc import Generator
from typing import Any

from madsci.common.types.auth_types import OwnershipInfo

_current_ownership_info = contextvars.ContextVar(
    "current_ownership_info",
    default=OwnershipInfo(),  # noqa: B039
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
