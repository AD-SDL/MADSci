"""Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component."""

import contextlib
import contextvars
from collections.abc import Generator
from typing import Any

from madsci.common.types.context_types import MadsciContext


class GlobalMadsciContext:
    """A global MadsciContext object that can be accessed and modified throughout the application. This is intended to be used as a singleton that can be accessed from anywhere in the codebase, but should not be modified directly. Instead, use the madsci_context context manager to temporarily override values in the context."""

    _context = MadsciContext()

    @property
    @classmethod
    def context(cls) -> MadsciContext:
        """Returns the current MadsciContext object."""
        return cls._context

    @context.setter
    @classmethod
    def context(cls, value: MadsciContext) -> None:
        """Sets the current MadsciContext object."""
        cls._context = value


_current_madsci_context = contextvars.ContextVar(
    "current_madsci_context",
    default=GlobalMadsciContext._context,
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


def set_current_madsci_context(context: MadsciContext) -> None:
    """Sets the current MadsciContext object."""
    _current_madsci_context.set(context)
