"""Deprecation utilities for MADSci.

This module provides utilities for managing deprecation warnings and
migration paths for deprecated features in MADSci.

Deprecation Timeline:
    - v0.7.0: Definition files hard-deprecated and removed
"""

import warnings
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# Deprecation version constants
DEPRECATED_IN = "0.7.0"
REMOVAL_IN = "0.7.0"


class MadsciDeprecationWarning(DeprecationWarning):
    """Custom deprecation warning for MADSci.

    This warning is used to indicate features that are deprecated and
    will be removed in a future version of MADSci.
    """


# Ensure MadsciDeprecationWarning is not filtered by default
warnings.filterwarnings("default", category=MadsciDeprecationWarning)


def emit_definition_deprecation_warning(
    definition_path: Path,
    definition_type: str = "definition",
    migration_command: Optional[str] = None,
) -> None:
    """Emit a deprecation warning for definition file loading.

    Args:
        definition_path: Path to the definition file being loaded.
        definition_type: Type of definition (e.g., "manager", "node", "workflow").
        migration_command: Optional CLI command to run for migration.
    """
    migration_hint = (
        f"\n  Run '{migration_command}' to migrate."
        if migration_command
        else "\n  Run 'madsci migrate' for migration assistance."
    )

    message = (
        f"\n\n⚠️  DEPRECATION WARNING: Loading {definition_type} from file\n"
        f"  File: {definition_path}\n"
        f"\n"
        f"  Definition files are deprecated as of v{DEPRECATED_IN} and will be\n"
        f"  removed in v{REMOVAL_IN}. Please migrate to the new settings-based\n"
        f"  configuration system.\n"
        f"{migration_hint}\n"
        f"\n"
        f"  For more information, see:\n"
        f"  https://ad-sdl.github.io/MADSci/migration\n"
    )

    warnings.warn(message, MadsciDeprecationWarning, stacklevel=3)


def emit_auto_write_deprecation_warning(
    file_path: Path,
    file_type: str = "configuration",
) -> None:
    """Emit a deprecation warning for auto-writing of configuration files.

    Args:
        file_path: Path to the file being auto-written.
        file_type: Type of file (e.g., "manager definition", "node info").
    """
    message = (
        f"\n\n⚠️  DEPRECATION WARNING: Auto-writing {file_type} file\n"
        f"  File: {file_path}\n"
        f"\n"
        f"  Auto-writing of {file_type} files is deprecated as of v{DEPRECATED_IN}\n"
        f"  and will be removed in v{REMOVAL_IN}. Use 'madsci config export'\n"
        f"  to export configuration explicitly.\n"
        f"\n"
        f"  For more information, see:\n"
        f"  https://ad-sdl.github.io/MADSci/migration-from-definitions\n"
    )
    warnings.warn(message, MadsciDeprecationWarning, stacklevel=3)


def deprecated(
    reason: str,
    deprecated_in: str = DEPRECATED_IN,
    removal_in: str = REMOVAL_IN,
    replacement: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to mark a function or method as deprecated.

    Args:
        reason: Explanation of why this is deprecated.
        deprecated_in: Version when deprecation was introduced.
        removal_in: Version when the feature will be removed.
        replacement: Optional replacement to use instead.

    Returns:
        Decorated function that emits a deprecation warning when called.

    Example:
        @deprecated(
            reason="Use new_function instead",
            replacement="new_function"
        )
        def old_function():
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            replacement_hint = f" Use '{replacement}' instead." if replacement else ""
            message = (
                f"{func.__qualname__} is deprecated as of v{deprecated_in} "
                f"and will be removed in v{removal_in}. "
                f"{reason}{replacement_hint}"
            )
            warnings.warn(message, MadsciDeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def deprecated_parameter(
    param_name: str,
    reason: str,
    deprecated_in: str = DEPRECATED_IN,
    removal_in: str = REMOVAL_IN,
    replacement: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to mark a function parameter as deprecated.

    The decorated function will emit a warning if the deprecated parameter
    is passed.

    Args:
        param_name: Name of the deprecated parameter.
        reason: Explanation of why this parameter is deprecated.
        deprecated_in: Version when deprecation was introduced.
        removal_in: Version when the parameter will be removed.
        replacement: Optional replacement parameter to use instead.

    Returns:
        Decorated function that emits a deprecation warning when the
        deprecated parameter is used.

    Example:
        @deprecated_parameter(
            "old_param",
            reason="Use new_param instead",
            replacement="new_param"
        )
        def my_function(new_param=None, old_param=None):
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if param_name in kwargs and kwargs[param_name] is not None:
                replacement_hint = (
                    f" Use '{replacement}' instead." if replacement else ""
                )
                message = (
                    f"Parameter '{param_name}' of {func.__qualname__} is deprecated "
                    f"as of v{deprecated_in} and will be removed in v{removal_in}. "
                    f"{reason}{replacement_hint}"
                )
                warnings.warn(message, MadsciDeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


class DeprecatedClass:
    """Mixin class to mark a class as deprecated.

    Inherit from this class to emit a deprecation warning when the class
    is instantiated.

    Example:
        class OldClass(DeprecatedClass):
            _deprecation_reason = "Use NewClass instead"
            _deprecation_replacement = "NewClass"
    """

    _deprecation_reason: str = "This class is deprecated"
    _deprecation_replacement: Optional[str] = None
    _deprecated_in: str = DEPRECATED_IN
    _removal_in: str = REMOVAL_IN

    _deprecation_wrapped: bool = False
    """Internal flag to track whether __init__ has already been wrapped."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Emit deprecation warning when subclass is instantiated."""
        super().__init_subclass__(**kwargs)

        # Don't warn for the mixin class itself
        if cls.__name__ == "DeprecatedClass":
            return

        # Only wrap __init__ for classes that directly define _deprecation_reason
        # (not inherited), and haven't already been wrapped. This prevents
        # double-warnings when a deprecated class is further subclassed.
        if "_deprecation_reason" not in cls.__dict__:
            return

        if cls._deprecation_wrapped:
            return

        replacement_hint = (
            f" Use '{cls._deprecation_replacement}' instead."
            if cls._deprecation_replacement
            else ""
        )
        original_init = cls.__init__

        @wraps(original_init)
        def warning_init(self: Any, *args: Any, **kwargs: Any) -> None:
            message = (
                f"{cls.__name__} is deprecated as of v{cls._deprecated_in} "
                f"and will be removed in v{cls._removal_in}. "
                f"{cls._deprecation_reason}{replacement_hint}"
            )
            warnings.warn(message, MadsciDeprecationWarning, stacklevel=2)
            original_init(self, *args, **kwargs)

        cls.__init__ = warning_init  # type: ignore[method-assign]
        cls._deprecation_wrapped = True
