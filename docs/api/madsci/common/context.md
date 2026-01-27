Module madsci.common.context
============================
Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component.

Functions
---------

`get_current_madsci_context() ‑> madsci.common.types.context_types.MadsciContext`
:   Returns the current MadsciContext object.

`madsci_context(**overrides: dict[str, typing.Any]) ‑> Generator[None, madsci.common.types.context_types.MadsciContext, None]`
:   Updates the current MadsciContext (as returned by get_current_madsci_context) with the provided overrides.

`set_current_madsci_context(context: madsci.common.types.context_types.MadsciContext) ‑> None`
:   Sets the current MadsciContext object.

Classes
-------

`GlobalMadsciContext()`
:   A global MadsciContext object for the application.

    This singleton can be accessed from anywhere in the codebase, but should
    not be modified directly. Instead, use the madsci_context context manager
    to temporarily override values in the context.

    ### Static methods

    `get_context() ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the global context, creating it lazily if needed.

        Returns:
            The global MadsciContext instance.

    `set_context(context: madsci.common.types.context_types.MadsciContext) ‑> None`
    :   Set the global context.

        Args:
            context: The MadsciContext instance to set as global.
