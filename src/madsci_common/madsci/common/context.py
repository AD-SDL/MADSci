"""Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component."""

import contextlib
import contextvars
from collections.abc import Generator
from typing import Any

from madsci.common.types.context_types import MadsciContext


class GlobalMadsciContext:
    """
    A global MadsciContext object for the application.

    This singleton can be accessed from anywhere in the codebase, but should
    not be modified directly. Instead, use the madsci_context context manager
    to temporarily override values in the context.
    """

    _context: MadsciContext | None = None

    @classmethod
    def get_context(cls) -> MadsciContext:
        """
        Get the global context, creating it lazily if needed.

        Returns:
            The global MadsciContext instance.
        """
        if cls._context is None:
            cls._context = MadsciContext()
        return cls._context

    @classmethod
    def set_context(cls, context: MadsciContext) -> None:
        """
        Set the global context.

        Args:
            context: The MadsciContext instance to set as global.
        """
        cls._context = context


_current_madsci_context: contextvars.ContextVar[MadsciContext | None] = (
    contextvars.ContextVar(
        "current_madsci_context",
        default=None,
    )
)


@contextlib.contextmanager
def madsci_context(**overrides: dict[str, Any]) -> Generator[None, MadsciContext, None]:
    """Updates the current MadsciContext (as returned by get_current_madsci_context) with the provided overrides."""
    prev_context = _current_madsci_context.get()
    if prev_context is None:
        prev_context = GlobalMadsciContext.get_context()
    context = prev_context.model_copy()
    for k, v in overrides.items():
        setattr(context, k, v)
    token = _current_madsci_context.set(context)
    try:
        yield _current_madsci_context.get()  # type: ignore[misc]
    finally:
        _current_madsci_context.reset(token)


def get_current_madsci_context() -> MadsciContext:
    """Returns the current MadsciContext object."""
    context = _current_madsci_context.get()
    if context is None:
        context = GlobalMadsciContext.get_context()
        _current_madsci_context.set(context)
    return context


def set_current_madsci_context(context: MadsciContext) -> None:
    """Sets the current MadsciContext object."""
    _current_madsci_context.set(context)
