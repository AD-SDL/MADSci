"""Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component."""

import contextlib
import contextvars
import inspect
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, Optional

from madsci.common.types.context_types import MadsciContext

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient
    from madsci.common.types.event_types import EventClientContext

__all__ = [
    "GlobalMadsciContext",
    "_event_client_context",
    "event_client_context",
    "get_current_madsci_context",
    "get_event_client",
    "get_event_client_context",
    "has_event_client_context",
    "madsci_context",
    "set_current_madsci_context",
]


class GlobalMadsciContext:
    """
    A global MadsciContext object for the application.

    This singleton can be accessed from anywhere in the codebase, but should
    not be modified directly. Instead, use the madsci_context context manager
    to temporarily override values in the context.
    """

    _context: Optional[MadsciContext] = None

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


_current_madsci_context: contextvars.ContextVar[Optional[MadsciContext]] = (
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


# =============================================================================
# EventClient Context Management
# =============================================================================

_event_client_context: contextvars.ContextVar[Optional["EventClientContext"]] = (
    contextvars.ContextVar(
        "event_client_context",
        default=None,
    )
)


def get_event_client(
    name: Optional[str] = None,
    create_if_missing: bool = True,
    **context_kwargs: Any,
) -> "EventClient":
    """
    Get the current EventClient from context, or create one if none exists.

    This is the primary way to obtain an EventClient in MADSci code.
    It enables automatic context propagation and hierarchical logging.

    Args:
        name: Optional name override. If provided without existing context,
              uses this as the client name. Ignored if context exists.
        create_if_missing: If True (default), create a new EventClient when
                          no context exists. If False, raises RuntimeError.
        **context_kwargs: Additional context to bind to the returned client.
                         If context exists, returns a bound child client.
                         If creating new, these become initial bound context.

    Returns:
        An EventClient instance, potentially with inherited context.

    Raises:
        RuntimeError: If create_if_missing=False and no context exists.

    Example:
        # In a component that should inherit context:
        logger = get_event_client()
        logger.info("Processing...")

        # In a component that wants to add context:
        logger = get_event_client(node_id="node-123")
        logger.info("Node action")  # Includes node_id
    """
    ctx = _event_client_context.get()

    if ctx is not None:
        # We have an existing context - use it or extend it
        if context_kwargs:
            # Caller wants to add context - return a bound child
            return ctx.client.bind(**context_kwargs)
        return ctx.client

    # No context exists
    if not create_if_missing:
        raise RuntimeError(
            "No EventClient context available. "
            "Wrap your code in an event_client_context() block or use create_if_missing=True."
        )

    # Create a new root EventClient
    # Use stack inspection as fallback for name
    if name is None:
        name = _infer_caller_name()

    from madsci.client.event_client import EventClient  # noqa: PLC0415

    client = EventClient(name=name)

    # Bind any provided context
    if context_kwargs:
        client = client.bind(**context_kwargs)

    return client


def _infer_caller_name() -> str:
    """
    Infer a reasonable name from the call stack.

    Walks up the stack to find the first frame that's not in the
    context module, and uses its module name.

    Returns:
        Inferred module name, or "madsci" as fallback.
    """
    stack = inspect.stack()
    for frame_info in stack[1:]:  # Skip this function
        module = frame_info.frame.f_globals.get("__name__", "")
        # Skip context module frames
        if not module.startswith("madsci.common.context"):
            return module
    return "madsci"


@contextlib.contextmanager
def event_client_context(
    name: Optional[str] = None,
    client: Optional["EventClient"] = None,
    inherit: bool = True,
    **context_metadata: Any,
) -> Generator["EventClient", None, None]:
    """
    Establish or extend an EventClient context.

    All code executed within this context manager will have access to
    the EventClient via get_event_client(), with accumulated context.

    Args:
        name: Name for this context level (e.g., "workflow", "node").
              Added to the hierarchy.
        client: Explicit EventClient to use. If None, inherits from
               parent context or creates a new one.
        inherit: If True (default), inherit and extend parent context.
                If False, create a fresh context.
        **context_metadata: Additional context to bind to all log messages
                           (e.g., experiment_id, workflow_id).

    Yields:
        The EventClient for this context.

    Example:
        # Establish root context in an experiment
        with event_client_context(name="experiment", experiment_id="exp-123") as logger:
            logger.info("Starting experiment")

            # Nested context for workflow
            with event_client_context(name="workflow", workflow_id="wf-456") as wf_logger:
                wf_logger.info("Running workflow")
                # Log includes both experiment_id and workflow_id
    """
    from madsci.client.event_client import EventClient  # noqa: PLC0415
    from madsci.common.types.event_types import EventClientContext  # noqa: PLC0415

    parent_ctx = _event_client_context.get()

    if client is not None:
        # Explicit client provided - use it
        new_client = client.bind(**context_metadata) if context_metadata else client
        hierarchy = [name] if name else []
        new_ctx = EventClientContext(
            client=new_client,
            hierarchy=hierarchy,
            metadata=dict(context_metadata),
        )
    elif parent_ctx is not None and inherit:
        # Inherit from parent context
        # Use provided name, or generate one from caller if not provided
        effective_name = name or _infer_caller_name().split(".")[-1]
        new_ctx = parent_ctx.child(effective_name, **context_metadata)
    else:
        # Create new root context
        effective_name = name or _infer_caller_name()
        new_client = EventClient(name=effective_name)
        if context_metadata:
            new_client = new_client.bind(**context_metadata)
        # Use effective_name for hierarchy to ensure consistency
        new_ctx = EventClientContext(
            client=new_client,
            hierarchy=[effective_name] if effective_name else [],
            metadata=dict(context_metadata),
        )

    token = _event_client_context.set(new_ctx)
    try:
        yield new_ctx.client
    finally:
        _event_client_context.reset(token)


def get_event_client_context() -> Optional["EventClientContext"]:
    """
    Get the current EventClientContext, if any.

    Returns:
        The current EventClientContext, or None if no context is active.

    Example:
        ctx = get_event_client_context()
        if ctx:
            print(f"Current hierarchy: {ctx.name}")
            print(f"Metadata: {ctx.metadata}")
    """
    return _event_client_context.get()


def has_event_client_context() -> bool:
    """
    Check if an EventClient context is currently active.

    Returns:
        True if a context is active, False otherwise.

    Example:
        if has_event_client_context():
            logger = get_event_client()  # Uses context
        else:
            logger = EventClient(name="standalone")  # Create new
    """
    return _event_client_context.get() is not None
