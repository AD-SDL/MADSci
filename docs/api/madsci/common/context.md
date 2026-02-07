Module madsci.common.context
============================
Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component.

Functions
---------

`event_client_context(name: str | None = None, client: ForwardRef('EventClient') | None = None, inherit: bool = True, **context_metadata: Any) ‑> Generator['EventClient', None, None]`
:   Establish or extend an EventClient context.

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

`get_current_madsci_context() ‑> madsci.common.types.context_types.MadsciContext`
:   Returns the current MadsciContext object.

`get_event_client(name: str | None = None, create_if_missing: bool = True, **context_kwargs: Any) ‑> EventClient`
:   Get the current EventClient from context, or create one if none exists.

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

`get_event_client_context() ‑> EventClientContext | None`
:   Get the current EventClientContext, if any.

    Returns:
        The current EventClientContext, or None if no context is active.

    Example:
        ctx = get_event_client_context()
        if ctx:
            print(f"Current hierarchy: {ctx.name}")
            print(f"Metadata: {ctx.metadata}")

`has_event_client_context() ‑> bool`
:   Check if an EventClient context is currently active.

    Returns:
        True if a context is active, False otherwise.

    Example:
        if has_event_client_context():
            logger = get_event_client()  # Uses context
        else:
            logger = EventClient(name="standalone")  # Create new

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
