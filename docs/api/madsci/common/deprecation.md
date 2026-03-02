Module madsci.common.deprecation
================================
Deprecation utilities for MADSci.

This module provides utilities for managing deprecation warnings and
migration paths for deprecated features in MADSci.

Deprecation Timeline:
    - v0.7.0: Definition files hard-deprecated and removed

Functions
---------

`deprecated(reason: str, deprecated_in: str = '0.7.0', removal_in: str = '0.7.0', replacement: str | None = None) ‑> Callable[[~F], ~F]`
:   Decorator to mark a function or method as deprecated.
    
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

`deprecated_parameter(param_name: str, reason: str, deprecated_in: str = '0.7.0', removal_in: str = '0.7.0', replacement: str | None = None) ‑> Callable[[~F], ~F]`
:   Decorator to mark a function parameter as deprecated.
    
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

`emit_auto_write_deprecation_warning(file_path: pathlib.Path, file_type: str = 'configuration') ‑> None`
:   Emit a deprecation warning for auto-writing of configuration files.
    
    Args:
        file_path: Path to the file being auto-written.
        file_type: Type of file (e.g., "manager definition", "node info").

`emit_definition_deprecation_warning(definition_path: pathlib.Path, definition_type: str = 'definition', migration_command: str | None = None) ‑> None`
:   Emit a deprecation warning for definition file loading.
    
    Args:
        definition_path: Path to the definition file being loaded.
        definition_type: Type of definition (e.g., "manager", "node", "workflow").
        migration_command: Optional CLI command to run for migration.

Classes
-------

`DeprecatedClass()`
:   Mixin class to mark a class as deprecated.
    
    Inherit from this class to emit a deprecation warning when the class
    is instantiated.
    
    Example:
        class OldClass(DeprecatedClass):
            _deprecation_reason = "Use NewClass instead"
            _deprecation_replacement = "NewClass"

`MadsciDeprecationWarning(*args, **kwargs)`
:   Custom deprecation warning for MADSci.
    
    This warning is used to indicate features that are deprecated and
    will be removed in a future version of MADSci.

    ### Ancestors (in MRO)

    * builtins.DeprecationWarning
    * builtins.Warning
    * builtins.Exception
    * builtins.BaseException