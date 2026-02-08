"""OpenTelemetry tracing decorators and context managers for MADSci.

This module provides convenient decorators and context managers for creating
OpenTelemetry spans in MADSci code, following the same patterns as the
event client and ownership context decorators.
"""

import asyncio
import contextlib
import functools
import inspect
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, Optional, Union, overload

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind, Status, StatusCode, Tracer
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = Any  # Using Any for return type to avoid TypeVar complexity with decorators

# Default tracer name when none is specified
_DEFAULT_TRACER_NAME = "madsci"


def get_tracer(name: Optional[str] = None) -> Tracer:
    """
    Get an OpenTelemetry tracer.

    Args:
        name: The tracer name. Defaults to "madsci".

    Returns:
        An OpenTelemetry Tracer instance.
    """
    return trace.get_tracer(name or _DEFAULT_TRACER_NAME)


def get_current_span() -> Span:
    """
    Get the current active span.

    Returns:
        The current Span, or a non-recording span if none is active.
    """
    return trace.get_current_span()


def is_span_recording() -> bool:
    """
    Check if the current span is recording.

    Returns:
        True if there's an active recording span, False otherwise.
    """
    return trace.get_current_span().is_recording()


@contextmanager
def span_context(
    name: str,
    *,
    tracer_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Generator[Span, None, None]:
    """
    Context manager that creates an OpenTelemetry span.

    This is a convenience wrapper around tracer.start_as_current_span() that
    handles the common case of creating a span with attributes and automatic
    exception recording.

    Args:
        name: The name of the span.
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER).
        attributes: Optional dictionary of span attributes.
        record_exception: If True, record exceptions as span events.
        set_status_on_exception: If True, set span status to ERROR on exception.

    Yields:
        The created Span object.

    Example:
        with span_context("process_data", attributes={"data.size": 100}) as span:
            result = process(data)
            span.set_attribute("result.count", len(result))

        with span_context("fetch_resource", kind=SpanKind.CLIENT) as span:
            response = requests.get(url)
            span.set_attribute("http.status_code", response.status_code)
    """
    tracer = get_tracer(tracer_name)

    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes,
        record_exception=record_exception,
        set_status_on_exception=set_status_on_exception,
    ) as span:
        yield span


@contextmanager
def safe_span_context(
    name: str,
    *,
    tracer_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
) -> Generator[Optional[Span], None, None]:
    """
    Context manager that creates a span if OTEL is configured, otherwise no-op.

    This is useful for code that may run with or without OTEL configured.
    It never raises exceptions related to tracing.

    Args:
        name: The name of the span.
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind.
        attributes: Optional dictionary of span attributes.

    Yields:
        The created Span object, or None if tracing is not available.

    Example:
        with safe_span_context("optional_trace") as span:
            if span:
                span.set_attribute("custom", "value")
            do_work()
    """
    try:
        tracer = get_tracer(tracer_name)
        with tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes,
            record_exception=True,
            set_status_on_exception=True,
        ) as span:
            if span.is_recording():
                yield span
            else:
                yield None
    except Exception:
        # If anything goes wrong with tracing, just yield None
        yield None


# =============================================================================
# Span Decorators
# =============================================================================


@overload
def with_span(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def with_span(
    *,
    name: Optional[str] = None,
    tracer_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def with_span(
    func: Optional[Callable[P, R]] = None,
    *,
    name: Optional[str] = None,
    tracer_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
    """
    Decorator that wraps a function in an OpenTelemetry span.

    This decorator creates a span for each function invocation, automatically
    recording the function name, arguments (optionally), and any exceptions.
    Works with both sync and async functions.

    Can be used with or without arguments:
        @with_span
        def my_function(): ...

        @with_span(name="custom_span", attributes={"component": "processor"})
        def my_function(): ...

    Args:
        func: The function to wrap (when used without parentheses).
        name: Custom span name. Defaults to the function's qualified name.
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER).
        attributes: Optional dictionary of span attributes to add.
        record_exception: If True, record exceptions as span events.
        set_status_on_exception: If True, set span status to ERROR on exception.

    Returns:
        The decorated function that runs within a span.

    Example:
        @with_span
        def process_data(data):
            return transform(data)

        @with_span(name="fetch_user", kind=SpanKind.CLIENT)
        def get_user(user_id: str):
            return api.fetch(user_id)

        @with_span(attributes={"workflow.type": "batch"})
        async def run_batch_workflow():
            await process_batch()
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        span_name = name or fn.__qualname__
        tracer = get_tracer(tracer_name)

        # Check if the function accepts 'span' parameter
        sig = inspect.signature(fn)
        accepts_span = "span" in sig.parameters

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with tracer.start_as_current_span(
                    span_name,
                    kind=kind,
                    attributes=attributes,
                    record_exception=record_exception,
                    set_status_on_exception=set_status_on_exception,
                ) as span:
                    if accepts_span and "span" not in kwargs:
                        kwargs["span"] = span  # type: ignore[assignment]
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
            ) as span:
                if accepts_span and "span" not in kwargs:
                    kwargs["span"] = span  # type: ignore[assignment]
                return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    # Handle both @with_span and @with_span(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


def traced_class(
    name: Optional[str] = None,
    *,
    tracer_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Callable[[type], type]:
    """
    Class decorator that wraps all public methods in OpenTelemetry spans.

    This decorator modifies a class so that all public methods (not starting
    with underscore) are automatically traced. The class gains a 'current_span'
    property that returns the active span.

    Args:
        name: Base name for spans. Defaults to the class name.
              Method spans will be named "{class_name}.{method_name}".
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind for method spans.
        attributes: Optional dictionary of span attributes to add to all spans.
        record_exception: If True, record exceptions as span events.
        set_status_on_exception: If True, set span status to ERROR on exception.

    Returns:
        A class decorator.

    Example:
        @traced_class(attributes={"component": "data_processor"})
        class DataProcessor:
            def process(self, data):
                # This method is automatically traced
                self.current_span.set_attribute("data.size", len(data))
                return transform(data)

            def _helper(self, x):  # Private methods are NOT traced
                return x * 2

        @traced_class(name="CustomWorker")
        class Worker:
            def get_span_attributes(self) -> dict:
                # Return instance-specific attributes
                return {"worker.id": self.worker_id}

            def work(self):
                # Span includes both class-level and instance attributes
                self.current_span.add_event("started")
                do_work()
    """
    class_attributes = attributes or {}

    def class_decorator(cls: type) -> type:
        class_name = name or cls.__name__

        # Store settings on the class
        cls._span_tracer_name = tracer_name  # type: ignore[attr-defined]
        cls._span_class_name = class_name  # type: ignore[attr-defined]
        cls._span_kind = kind  # type: ignore[attr-defined]
        cls._span_attributes = class_attributes  # type: ignore[attr-defined]
        cls._span_record_exception = record_exception  # type: ignore[attr-defined]
        cls._span_set_status_on_exception = set_status_on_exception  # type: ignore[attr-defined]

        # Add current_span property if needed
        _add_current_span_property(cls)

        # Wrap public methods
        _wrap_traced_methods(
            cls,
            class_name,
            tracer_name,
            kind,
            class_attributes,
            record_exception,
            set_status_on_exception,
        )

        return cls

    return class_decorator


def _add_current_span_property(cls: type) -> None:
    """Add a current_span property to a class if it doesn't already have one."""
    if hasattr(cls, "current_span") and isinstance(
        getattr(cls, "current_span", None), property
    ):
        return

    @property
    def current_span_property(self: Any) -> Span:  # noqa: ARG001
        """Get the current active span."""
        return trace.get_current_span()

    cls.current_span = current_span_property  # type: ignore[attr-defined]


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


def _should_wrap_traced_method(cls: type, attr_name: str) -> bool:
    """Determine if a class attribute should be wrapped with span tracing."""
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

    # Skip classmethods, staticmethods, and properties
    static_attr = inspect.getattr_static(cls, attr_name)
    return not isinstance(static_attr, (classmethod, staticmethod, property))


def _wrap_traced_methods(
    cls: type,
    class_name: str,
    tracer_name: Optional[str],
    kind: SpanKind,
    class_attributes: dict[str, Any],
    record_exception: bool,
    set_status_on_exception: bool,
) -> None:
    """Wrap all public methods of a class with span tracing."""
    for attr_name in dir(cls):
        if not _should_wrap_traced_method(cls, attr_name):
            continue

        attr = getattr(cls, attr_name)
        span_name = f"{class_name}.{attr_name}"
        wrapped = _wrap_traced_method(
            attr,
            span_name,
            tracer_name,
            kind,
            class_attributes,
            record_exception,
            set_status_on_exception,
        )
        setattr(cls, attr_name, wrapped)


def _wrap_traced_method(
    method: Callable[..., R],
    span_name: str,
    tracer_name: Optional[str],
    kind: SpanKind,
    class_attributes: dict[str, Any],
    record_exception: bool,
    set_status_on_exception: bool,
) -> Callable[..., R]:
    """Wrap a method to run within a span."""
    tracer = get_tracer(tracer_name)

    if asyncio.iscoroutinefunction(method):

        @functools.wraps(method)
        async def async_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            # Get instance-specific attributes if available
            span_attrs = dict(class_attributes)
            if hasattr(self, "get_span_attributes"):
                with contextlib.suppress(Exception):
                    span_attrs.update(self.get_span_attributes())

            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=span_attrs or None,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
            ):
                return await method(self, *args, **kwargs)

        return async_method_wrapper  # type: ignore[return-value]

    @functools.wraps(method)
    def sync_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        # Get instance-specific attributes if available
        span_attrs = dict(class_attributes)
        if hasattr(self, "get_span_attributes"):
            with contextlib.suppress(Exception):
                span_attrs.update(self.get_span_attributes())

        with tracer.start_as_current_span(
            span_name,
            kind=kind,
            attributes=span_attrs or None,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        ):
            return method(self, *args, **kwargs)

    return sync_method_wrapper  # type: ignore[return-value]


# =============================================================================
# Utility Functions
# =============================================================================


def set_span_error(
    span: Optional[Span] = None,
    exception: Optional[BaseException] = None,
    message: Optional[str] = None,
) -> None:
    """
    Set the current or provided span to error status.

    Args:
        span: The span to mark as error. Uses current span if not provided.
        exception: Optional exception to record.
        message: Optional error message.

    Example:
        try:
            risky_operation()
        except Exception as e:
            set_span_error(exception=e, message="Operation failed")
            raise
    """
    target_span = span or trace.get_current_span()
    if not target_span.is_recording():
        return

    if exception:
        target_span.record_exception(exception)
    target_span.set_status(
        Status(StatusCode.ERROR, message or (str(exception) if exception else None))
    )


def add_span_event(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    span: Optional[Span] = None,
) -> None:
    """
    Add an event to the current or provided span.

    Args:
        name: The event name.
        attributes: Optional event attributes.
        span: The span to add the event to. Uses current span if not provided.

    Example:
        add_span_event("cache_hit", {"key": cache_key})
        add_span_event("validation_complete", {"items_validated": 100})
    """
    target_span = span or trace.get_current_span()
    if target_span.is_recording():
        target_span.add_event(name, attributes=attributes)


def set_span_attributes(
    attributes: dict[str, Any],
    span: Optional[Span] = None,
) -> None:
    """
    Set multiple attributes on the current or provided span.

    Args:
        attributes: Dictionary of attributes to set.
        span: The span to set attributes on. Uses current span if not provided.

    Example:
        set_span_attributes({
            "user.id": user_id,
            "request.size": len(data),
            "cache.enabled": True,
        })
    """
    target_span = span or trace.get_current_span()
    if target_span.is_recording():
        for key, value in attributes.items():
            target_span.set_attribute(key, value)
