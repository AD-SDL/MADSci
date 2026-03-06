"""Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component."""

import asyncio
import contextlib
import contextvars
import functools
import inspect
from collections.abc import Callable, Generator
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    TypeVar,
    Union,
    overload,
)

from madsci.common.types.context_types import MadsciContext
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient
    from madsci.common.types.event_types import EventClientContext

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

__all__ = [
    "GlobalMadsciContext",
    "_event_client_context",
    "event_client_class",
    "event_client_context",
    "get_current_madsci_context",
    "get_event_client",
    "get_event_client_context",
    "has_event_client_context",
    "has_madsci_context",
    "madsci_context",
    "madsci_context_class",
    "set_current_madsci_context",
    "with_event_client",
    "with_madsci_context",
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
def madsci_context(**overrides: Any) -> Generator[MadsciContext, None, None]:
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


def has_madsci_context() -> bool:
    """
    Check if a MadsciContext has been explicitly set (not just using global default).

    Returns:
        True if a context has been explicitly set, False otherwise.
    """
    return _current_madsci_context.get() is not None


# =============================================================================
# MadsciContext Decorators
# =============================================================================


@overload
def with_madsci_context(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def with_madsci_context(
    *,
    lab_server_url: Optional[str] = None,
    event_server_url: Optional[str] = None,
    experiment_server_url: Optional[str] = None,
    data_server_url: Optional[str] = None,
    resource_server_url: Optional[str] = None,
    workcell_server_url: Optional[str] = None,
    location_server_url: Optional[str] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def with_madsci_context(
    func: Optional[Callable[P, R]] = None,
    *,
    lab_server_url: Optional[str] = None,
    event_server_url: Optional[str] = None,
    experiment_server_url: Optional[str] = None,
    data_server_url: Optional[str] = None,
    resource_server_url: Optional[str] = None,
    workcell_server_url: Optional[str] = None,
    location_server_url: Optional[str] = None,
) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
    """
    Decorator that establishes a MadsciContext for a function.

    This decorator wraps a function (sync or async) so that all code executed
    within it has access to the specified MadsciContext configuration via
    get_current_madsci_context(). The decorated function can optionally receive
    the MadsciContext as a keyword argument named 'madsci_ctx'.

    Can be used with or without arguments:
        @with_madsci_context
        def my_function(): ...

        @with_madsci_context(event_server_url="http://localhost:8001")
        def my_workflow(): ...

    Args:
        func: The function to wrap (when used without parentheses).
        lab_server_url: Lab server URL to set in context.
        event_server_url: Event server URL to set in context.
        experiment_server_url: Experiment server URL to set in context.
        data_server_url: Data server URL to set in context.
        resource_server_url: Resource server URL to set in context.
        workcell_server_url: Workcell server URL to set in context.
        location_server_url: Location server URL to set in context.

    Returns:
        The decorated function that runs within a MadsciContext.

    Example:
        @with_madsci_context(event_server_url="http://localhost:8001")
        def log_events():
            ctx = get_current_madsci_context()
            print(f"Logging to: {ctx.event_server_url}")

        @with_madsci_context(lab_server_url="http://lab:8000")
        def connect_to_lab(madsci_ctx: MadsciContext = None):
            # madsci_ctx is automatically injected
            print(f"Connecting to: {madsci_ctx.lab_server_url}")

        @with_madsci_context(data_server_url="http://data:8004")
        async def async_data_op():
            ctx = get_current_madsci_context()
            await upload_data(ctx.data_server_url)
    """
    # Collect non-None overrides
    overrides = {
        k: v
        for k, v in {
            "lab_server_url": lab_server_url,
            "event_server_url": event_server_url,
            "experiment_server_url": experiment_server_url,
            "data_server_url": data_server_url,
            "resource_server_url": resource_server_url,
            "workcell_server_url": workcell_server_url,
            "location_server_url": location_server_url,
        }.items()
        if v is not None
    }

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        # Check if the function accepts 'madsci_ctx' parameter
        sig = inspect.signature(fn)
        accepts_madsci_ctx = "madsci_ctx" in sig.parameters

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with madsci_context(**overrides) as ctx:
                    if accepts_madsci_ctx and "madsci_ctx" not in kwargs:
                        kwargs["madsci_ctx"] = ctx  # type: ignore[assignment]
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with madsci_context(**overrides) as ctx:
                if accepts_madsci_ctx and "madsci_ctx" not in kwargs:
                    kwargs["madsci_ctx"] = ctx  # type: ignore[assignment]
                return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    # Handle both @with_madsci_context and @with_madsci_context(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


def madsci_context_class(
    lab_server_url: Optional[str] = None,
    event_server_url: Optional[str] = None,
    experiment_server_url: Optional[str] = None,
    data_server_url: Optional[str] = None,
    resource_server_url: Optional[str] = None,
    workcell_server_url: Optional[str] = None,
    location_server_url: Optional[str] = None,
) -> Callable[[type], type]:
    """
    Class decorator that establishes a MadsciContext for method calls.

    This decorator modifies a class so that all public methods run within a
    MadsciContext. The class gains a 'madsci_context' property that returns
    the current context.

    Args:
        lab_server_url: Lab server URL to set in context.
        event_server_url: Event server URL to set in context.
        experiment_server_url: Experiment server URL to set in context.
        data_server_url: Data server URL to set in context.
        resource_server_url: Resource server URL to set in context.
        workcell_server_url: Workcell server URL to set in context.
        location_server_url: Location server URL to set in context.

    Returns:
        A class decorator.

    Example:
        @madsci_context_class(event_server_url="http://localhost:8001")
        class EventLogger:
            def log_event(self, message):
                # self.madsci_context is available
                print(f"Logging to: {self.madsci_context.event_server_url}")

        @madsci_context_class(lab_server_url="http://lab:8000")
        class LabConnector:
            def get_context_overrides(self) -> dict:
                # Add instance-specific context overrides
                return {"workcell_server_url": self.workcell_url}

            def connect(self):
                # Uses both class-level and instance-level context
                print(f"Lab: {self.madsci_context.lab_server_url}")
    """
    # Collect non-None overrides
    class_overrides = {
        k: v
        for k, v in {
            "lab_server_url": lab_server_url,
            "event_server_url": event_server_url,
            "experiment_server_url": experiment_server_url,
            "data_server_url": data_server_url,
            "resource_server_url": resource_server_url,
            "workcell_server_url": workcell_server_url,
            "location_server_url": location_server_url,
        }.items()
        if v is not None
    }

    def class_decorator(cls: type) -> type:
        # Store overrides on the class
        cls._madsci_context_overrides = class_overrides  # type: ignore[attr-defined]

        # Add madsci_context property if needed
        _add_madsci_context_property(cls)

        # Wrap public methods
        _wrap_madsci_context_methods(cls, class_overrides)

        return cls

    return class_decorator


def _add_madsci_context_property(cls: type) -> None:
    """Add a madsci_context property to a class if it doesn't already have one."""
    if hasattr(cls, "madsci_context") and isinstance(
        getattr(cls, "madsci_context", None), property
    ):
        return

    @property
    def madsci_context_property(self: Any) -> MadsciContext:  # noqa: ARG001
        """Get the current MadsciContext."""
        return get_current_madsci_context()

    cls.madsci_context = madsci_context_property  # type: ignore[attr-defined]


def _should_wrap_madsci_context_method(cls: type, attr_name: str) -> bool:
    """Determine if a class attribute should be wrapped with madsci context."""
    # Skip private/magic methods
    if attr_name.startswith("_"):
        return False

    # Skip methods that could cause recursion with stacked decorators
    if attr_name in _DECORATOR_EXCLUDED_METHODS:
        return False

    attr = getattr(cls, attr_name, None)

    # Only wrap callable attributes
    if not callable(attr):
        return False

    # Skip class attributes that are types (classes) - they are callable but not methods
    # This prevents wrapping class attributes like DEFINITION_CLASS, SETTINGS_CLASS, etc.
    if isinstance(attr, type):
        return False

    # Skip classmethods, staticmethods, and properties
    static_attr = inspect.getattr_static(cls, attr_name)
    return not isinstance(static_attr, (classmethod, staticmethod, property))


def _wrap_madsci_context_methods(cls: type, class_overrides: dict[str, Any]) -> None:
    """Wrap all public methods of a class with madsci context."""
    for attr_name in dir(cls):
        if not _should_wrap_madsci_context_method(cls, attr_name):
            continue

        attr = getattr(cls, attr_name)
        wrapped = _wrap_madsci_context_method(attr, class_overrides)
        setattr(cls, attr_name, wrapped)


def _wrap_madsci_context_method(
    method: Callable[..., R],
    class_overrides: dict[str, Any],
) -> Callable[..., R]:
    """Wrap a method to run within a madsci context."""
    if asyncio.iscoroutinefunction(method):

        @functools.wraps(method)
        async def async_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            # Get instance-specific overrides if available
            overrides = dict(class_overrides)
            if hasattr(self, "get_context_overrides"):
                overrides.update(self.get_context_overrides())

            with madsci_context(**overrides):
                return await method(self, *args, **kwargs)

        return async_method_wrapper  # type: ignore[return-value]

    @functools.wraps(method)
    def sync_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        # Get instance-specific overrides if available
        overrides = dict(class_overrides)
        if hasattr(self, "get_context_overrides"):
            overrides.update(self.get_context_overrides())

        with madsci_context(**overrides):
            return method(self, *args, **kwargs)

    return sync_method_wrapper  # type: ignore[return-value]


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

    Uses inspect.currentframe() and f_back traversal instead of
    inspect.stack() for better performance (avoids building full stack list).

    Returns:
        Inferred module name, or "madsci" as fallback.
    """
    frame = inspect.currentframe()
    # Skip this function's own frame
    if frame is not None:
        frame = frame.f_back

    # Walk back through frames without constructing the full stack
    try:
        depth = 0
        while frame is not None and depth < 50:
            module = frame.f_globals.get("__name__", "")
            # Skip context module frames
            if not module.startswith("madsci.common.context"):
                return module
            frame = frame.f_back
            depth += 1
    finally:
        # Avoid reference cycles involving frame objects
        del frame

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


# =============================================================================
# EventClient Context Decorators
# =============================================================================


@overload
def with_event_client(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def with_event_client(
    *,
    name: Optional[str] = None,
    inherit: bool = True,
    **context_metadata: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def with_event_client(
    func: Optional[Callable[P, R]] = None,
    *,
    name: Optional[str] = None,
    inherit: bool = True,
    **context_metadata: Any,
) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
    """
    Decorator that establishes an EventClient context for a function.

    This decorator wraps a function (sync or async) so that all code executed
    within it has access to an EventClient via get_event_client(), with
    accumulated context. The decorated function can optionally receive the
    EventClient as a keyword argument named 'event_client'.

    Can be used with or without arguments:
        @with_event_client
        def my_function(): ...

        @with_event_client(name="my_workflow", workflow_id="wf-123")
        def my_workflow(): ...

    Args:
        func: The function to wrap (when used without parentheses).
        name: Name for this context level. If not provided, uses the
              function's qualified name.
        inherit: If True (default), inherit and extend parent context.
                If False, create a fresh context.
        **context_metadata: Additional context to bind to all log messages
                           within this function (e.g., experiment_id, node_id).

    Returns:
        The decorated function that runs within an EventClient context.

    Example:
        @with_event_client
        def process_data():
            logger = get_event_client()
            logger.info("Processing data...")

        @with_event_client(name="experiment", experiment_id="exp-123")
        def run_experiment(event_client: EventClient = None):
            # event_client is automatically injected
            event_client.info("Running experiment")

        @with_event_client(name="async_task")
        async def async_operation():
            logger = get_event_client()
            await some_async_work()
            logger.info("Done")
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        # Determine the context name
        context_name = name or fn.__qualname__

        # Check if the function accepts 'event_client' parameter
        sig = inspect.signature(fn)
        accepts_event_client = "event_client" in sig.parameters

        if asyncio.iscoroutinefunction(fn):
            # Async function wrapper
            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with event_client_context(
                    name=context_name,
                    inherit=inherit,
                    **context_metadata,
                ) as client:
                    if accepts_event_client and "event_client" not in kwargs:
                        kwargs["event_client"] = client  # type: ignore[assignment]
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        # Sync function wrapper
        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with event_client_context(
                name=context_name,
                inherit=inherit,
                **context_metadata,
            ) as client:
                if accepts_event_client and "event_client" not in kwargs:
                    kwargs["event_client"] = client  # type: ignore[assignment]
                return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    # Handle both @with_event_client and @with_event_client(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


def event_client_class(
    name: Optional[str] = None,
    inherit: bool = True,
    **context_metadata: Any,
) -> Callable[[type[T]], type[T]]:
    """
    Class decorator that establishes an EventClient context for method calls.

    This decorator modifies a class so that specified methods (or all public
    methods if none specified) run within an EventClient context. The class
    gains an 'event_client' property that returns the current context's client.

    Args:
        name: Base name for the context. Defaults to the class name.
              Method contexts will be named "{class_name}.{method_name}".
        inherit: If True (default), inherit and extend parent context.
                If False, create a fresh context for each method call.
        **context_metadata: Additional context to bind to all log messages
                           within this class (e.g., component_type="processor").

    Returns:
        A class decorator.

    Example:
        @event_client_class(component_type="data_processor")
        class DataProcessor:
            def process(self, data):
                # self.event_client is available
                self.event_client.info("Processing", data_size=len(data))
                return self._transform(data)

            def _transform(self, data):  # Private methods not wrapped
                return data.upper()

        @event_client_class(name="CustomName", wrap_methods=["run", "execute"])
        class Workflow:
            def run(self):
                self.event_client.info("Running workflow")

            def execute(self):
                self.event_client.info("Executing")

            def helper(self):  # Not wrapped
                pass
    """

    def class_decorator(cls: type[T]) -> type[T]:
        class_name = name or cls.__name__

        # Store context settings on the class
        cls._event_client_context_name = class_name  # type: ignore[attr-defined]
        cls._event_client_context_inherit = inherit  # type: ignore[attr-defined]
        cls._event_client_context_metadata = context_metadata  # type: ignore[attr-defined]

        # Add event_client property if needed
        _add_event_client_property(cls)

        # Wrap public methods
        _wrap_public_methods(cls, class_name, inherit, context_metadata)

        return cls

    return class_decorator


def _add_event_client_property(cls: type) -> None:
    """Add an event_client property to a class if it doesn't already have one."""
    if hasattr(cls, "event_client") and isinstance(
        getattr(cls, "event_client", None), property
    ):
        return

    @property
    def event_client_property(self: Any) -> "EventClient":
        """Get the EventClient for this instance from the current context."""
        instance_metadata = {
            **self._event_client_context_metadata,
        }
        # Add instance-specific context if available
        if hasattr(self, "get_event_context"):
            instance_metadata.update(self.get_event_context())
        return get_event_client(**instance_metadata)

    cls.event_client = event_client_property  # type: ignore[attr-defined]


# Methods that should never be wrapped by class decorators to avoid recursion
# when multiple decorators are stacked
_DECORATOR_EXCLUDED_METHODS = frozenset(
    {
        # EventClient context
        "get_event_context",
        # Ownership context
        "get_ownership_overrides",
        # MadsciContext
        "get_context_overrides",
        # OTEL tracing
        "get_span_attributes",
    }
)


def _should_wrap_method(cls: type, attr_name: str) -> bool:
    """Determine if a class attribute should be wrapped with event client context."""
    # Skip private/magic methods
    if attr_name.startswith("_"):
        return False

    # Skip methods that could cause recursion with stacked decorators
    if attr_name in _DECORATOR_EXCLUDED_METHODS:
        return False

    attr = getattr(cls, attr_name, None)

    # Only wrap callable attributes
    if not callable(attr):
        return False

    # Skip class attributes that are types (classes) - they are callable but not methods
    # This prevents wrapping class attributes like DEFINITION_CLASS, SETTINGS_CLASS, etc.
    if isinstance(attr, type):
        return False

    # Skip classmethods, staticmethods, and properties
    static_attr = inspect.getattr_static(cls, attr_name)
    return not isinstance(static_attr, (classmethod, staticmethod, property))


def _wrap_public_methods(
    cls: type,
    class_name: str,
    inherit: bool,
    context_metadata: dict[str, Any],
) -> None:
    """Wrap all public methods of a class with event client context."""
    for attr_name in dir(cls):
        if not _should_wrap_method(cls, attr_name):
            continue

        attr = getattr(cls, attr_name)
        method_context_name = f"{class_name}.{attr_name}"
        wrapped = _wrap_method(attr, method_context_name, inherit, context_metadata)
        setattr(cls, attr_name, wrapped)


def _wrap_method(
    method: Callable[..., R],
    context_name: str,
    inherit: bool,
    context_metadata: dict[str, Any],
) -> Callable[..., R]:
    """
    Wrap a method to run within an EventClient context.

    Args:
        method: The method to wrap.
        context_name: Name for the context.
        inherit: Whether to inherit parent context.
        context_metadata: Additional context metadata.

    Returns:
        The wrapped method.
    """
    if asyncio.iscoroutinefunction(method):

        @functools.wraps(method)
        async def async_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            # Get instance-specific context if available
            instance_metadata = dict(context_metadata)
            if hasattr(self, "get_event_context"):
                instance_metadata.update(self.get_event_context())

            with event_client_context(
                name=context_name,
                inherit=inherit,
                **instance_metadata,
            ):
                return await method(self, *args, **kwargs)

        return async_method_wrapper  # type: ignore[return-value]

    @functools.wraps(method)
    def sync_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        # Get instance-specific context if available
        instance_metadata = dict(context_metadata)
        if hasattr(self, "get_event_context"):
            instance_metadata.update(self.get_event_context())

        with event_client_context(
            name=context_name,
            inherit=inherit,
            **instance_metadata,
        ):
            return method(self, *args, **kwargs)

    return sync_method_wrapper  # type: ignore[return-value]
