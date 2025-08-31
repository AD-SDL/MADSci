"""Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component."""

import contextlib
import contextvars
from collections.abc import Generator
from typing import Any

from madsci.common.types.context_types import MadsciContext

global_madsci_context = MadsciContext()
"""
Global MADSci context
To change the context for a system component, set fields on this object.
This is then used by the madsci_context context manager to create temporary contexts as needed.
"""

_current_madsci_context = contextvars.ContextVar(
    "current_madsci_context",
    default=global_madsci_context,
)


@contextlib.contextmanager
def madsci_context(**overrides: dict[str, Any]) -> Generator[None, MadsciContext, None]:
    """Updates the current MadsciContext (as returned by get_current_madsci_context) with the provided overrides."""
    prev_context = _current_madsci_context.get()
    context = prev_context.model_copy()
    for k, v in overrides.items():
        setattr(context, k, v)
    token = _current_madsci_context.set(context)
    try:
        yield _current_madsci_context.get()
    finally:
        _current_madsci_context.reset(token)


def get_current_madsci_context() -> MadsciContext:
    """Returns the current MadsciContext object."""
    return _current_madsci_context.get()
