"""Provides the OwnershipHandler class for managing global ownership context of objects throughout a MADSci system component."""

import asyncio
import contextlib
import contextvars
import functools
import inspect
from collections.abc import Callable, Generator
from typing import Any, Optional, Union, overload

from madsci.common.types.auth_types import OwnershipInfo
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = Any  # Using Any for return type to avoid TypeVar complexity with decorators

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
def ownership_context(**overrides: Any) -> Generator[OwnershipInfo, None, None]:
    """Updates the current OwnershipInfo (as returned by get_current_ownership_info) with the provided overrides."""
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


def has_ownership_context() -> bool:
    """
    Check if an ownership context different from global is active.

    Returns:
        True if a non-global ownership context is active, False otherwise.
    """
    return _current_ownership_info.get() is not global_ownership_info


# =============================================================================
# Ownership Context Decorators
# =============================================================================


@overload
def with_ownership(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def with_ownership(
    *,
    user_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    project_id: Optional[str] = None,
    node_id: Optional[str] = None,
    workcell_id: Optional[str] = None,
    lab_id: Optional[str] = None,
    step_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def with_ownership(
    func: Optional[Callable[P, R]] = None,
    *,
    user_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    project_id: Optional[str] = None,
    node_id: Optional[str] = None,
    workcell_id: Optional[str] = None,
    lab_id: Optional[str] = None,
    step_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
    """
    Decorator that establishes an OwnershipInfo context for a function.

    This decorator wraps a function (sync or async) so that all code executed
    within it has access to the specified ownership context via
    get_current_ownership_info(). The decorated function can optionally receive
    the OwnershipInfo as a keyword argument named 'ownership_info'.

    Can be used with or without arguments:
        @with_ownership
        def my_function(): ...

        @with_ownership(experiment_id="exp-123", workflow_id="wf-456")
        def my_workflow(): ...

    Args:
        func: The function to wrap (when used without parentheses).
        user_id: User ID to set in ownership context.
        experiment_id: Experiment ID to set in ownership context.
        campaign_id: Campaign ID to set in ownership context.
        project_id: Project ID to set in ownership context.
        node_id: Node ID to set in ownership context.
        workcell_id: Workcell ID to set in ownership context.
        lab_id: Lab ID to set in ownership context.
        step_id: Step ID to set in ownership context.
        workflow_id: Workflow ID to set in ownership context.
        manager_id: Manager ID to set in ownership context.

    Returns:
        The decorated function that runs within an ownership context.

    Example:
        @with_ownership(experiment_id="exp-123")
        def process_data():
            info = get_current_ownership_info()
            print(f"Processing for experiment: {info.experiment_id}")

        @with_ownership(node_id="node-001", step_id="step-1")
        def run_step(ownership_info: OwnershipInfo = None):
            # ownership_info is automatically injected
            print(f"Running step {ownership_info.step_id}")

        @with_ownership(workflow_id="wf-123")
        async def async_workflow():
            info = get_current_ownership_info()
            await process_async()
    """
    # Collect non-None overrides
    overrides = {
        k: v
        for k, v in {
            "user_id": user_id,
            "experiment_id": experiment_id,
            "campaign_id": campaign_id,
            "project_id": project_id,
            "node_id": node_id,
            "workcell_id": workcell_id,
            "lab_id": lab_id,
            "step_id": step_id,
            "workflow_id": workflow_id,
            "manager_id": manager_id,
        }.items()
        if v is not None
    }

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        # Check if the function accepts 'ownership_info' parameter
        sig = inspect.signature(fn)
        accepts_ownership_info = "ownership_info" in sig.parameters

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with ownership_context(**overrides) as info:
                    if accepts_ownership_info and "ownership_info" not in kwargs:
                        kwargs["ownership_info"] = info  # type: ignore[assignment]
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with ownership_context(**overrides) as info:
                if accepts_ownership_info and "ownership_info" not in kwargs:
                    kwargs["ownership_info"] = info  # type: ignore[assignment]
                return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    # Handle both @with_ownership and @with_ownership(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


def ownership_class(
    user_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    project_id: Optional[str] = None,
    node_id: Optional[str] = None,
    workcell_id: Optional[str] = None,
    lab_id: Optional[str] = None,
    step_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Callable[[type], type]:
    """
    Class decorator that establishes an OwnershipInfo context for method calls.

    This decorator modifies a class so that all public methods run within an
    OwnershipInfo context. The class gains an 'ownership_info' property that
    returns the current context's OwnershipInfo.

    Args:
        user_id: User ID to set in ownership context.
        experiment_id: Experiment ID to set in ownership context.
        campaign_id: Campaign ID to set in ownership context.
        project_id: Project ID to set in ownership context.
        node_id: Node ID to set in ownership context.
        workcell_id: Workcell ID to set in ownership context.
        lab_id: Lab ID to set in ownership context.
        step_id: Step ID to set in ownership context.
        workflow_id: Workflow ID to set in ownership context.
        manager_id: Manager ID to set in ownership context.

    Returns:
        A class decorator.

    Example:
        @ownership_class(experiment_id="exp-123")
        class DataProcessor:
            def process(self, data):
                # self.ownership_info is available
                print(f"Processing for {self.ownership_info.experiment_id}")
                return data.upper()

        @ownership_class(node_id="node-001")
        class NodeWorker:
            def get_ownership_overrides(self) -> dict:
                # Add instance-specific ownership
                return {"step_id": self.current_step_id}

            def work(self):
                # Includes both class-level and instance-level ownership
                print(f"Node: {self.ownership_info.node_id}")
    """
    # Collect non-None overrides
    class_overrides = {
        k: v
        for k, v in {
            "user_id": user_id,
            "experiment_id": experiment_id,
            "campaign_id": campaign_id,
            "project_id": project_id,
            "node_id": node_id,
            "workcell_id": workcell_id,
            "lab_id": lab_id,
            "step_id": step_id,
            "workflow_id": workflow_id,
            "manager_id": manager_id,
        }.items()
        if v is not None
    }

    def class_decorator(cls: type) -> type:
        # Store overrides on the class
        cls._ownership_context_overrides = class_overrides  # type: ignore[attr-defined]

        # Add ownership_info property if needed
        _add_ownership_info_property(cls)

        # Wrap public methods
        _wrap_ownership_methods(cls, class_overrides)

        return cls

    return class_decorator


def _add_ownership_info_property(cls: type) -> None:
    """Add an ownership_info property to a class if it doesn't already have one."""
    if hasattr(cls, "ownership_info") and isinstance(
        getattr(cls, "ownership_info", None), property
    ):
        return

    @property
    def ownership_info_property(self: Any) -> OwnershipInfo:  # noqa: ARG001
        """Get the current OwnershipInfo."""
        return get_current_ownership_info()

    cls.ownership_info = ownership_info_property  # type: ignore[attr-defined]


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


def _should_wrap_ownership_method(cls: type, attr_name: str) -> bool:
    """Determine if a class attribute should be wrapped with ownership context."""
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


def _wrap_ownership_methods(cls: type, class_overrides: dict[str, Any]) -> None:
    """Wrap all public methods of a class with ownership context."""
    for attr_name in dir(cls):
        if not _should_wrap_ownership_method(cls, attr_name):
            continue

        attr = getattr(cls, attr_name)
        wrapped = _wrap_ownership_method(attr, class_overrides)
        setattr(cls, attr_name, wrapped)


def _wrap_ownership_method(
    method: Callable[..., R],
    class_overrides: dict[str, Any],
) -> Callable[..., R]:
    """Wrap a method to run within an ownership context."""
    if asyncio.iscoroutinefunction(method):

        @functools.wraps(method)
        async def async_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            # Get instance-specific overrides if available
            overrides = dict(class_overrides)
            if hasattr(self, "get_ownership_overrides"):
                overrides.update(self.get_ownership_overrides())

            with ownership_context(**overrides):
                return await method(self, *args, **kwargs)

        return async_method_wrapper  # type: ignore[return-value]

    @functools.wraps(method)
    def sync_method_wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        # Get instance-specific overrides if available
        overrides = dict(class_overrides)
        if hasattr(self, "get_ownership_overrides"):
            overrides.update(self.get_ownership_overrides())

        with ownership_context(**overrides):
            return method(self, *args, **kwargs)

    return sync_method_wrapper  # type: ignore[return-value]
