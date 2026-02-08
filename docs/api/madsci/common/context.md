Module madsci.common.context
============================
Provides the ContextHandler class for managing global MadsciContext throughout a MADSci system component.

Functions
---------

`event_client_class(name: str | None = None, inherit: bool = True, **context_metadata: Any) ‑> Callable[[type[~T]], type[~T]]`
:   Class decorator that establishes an EventClient context for method calls.

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

`has_madsci_context() ‑> bool`
:   Check if a MadsciContext has been explicitly set (not just using global default).

    Returns:
        True if a context has been explicitly set, False otherwise.

`madsci_context(**overrides: Any) ‑> Generator[madsci.common.types.context_types.MadsciContext, None, None]`
:   Updates the current MadsciContext (as returned by get_current_madsci_context) with the provided overrides.

`madsci_context_class(lab_server_url: str | None = None, event_server_url: str | None = None, experiment_server_url: str | None = None, data_server_url: str | None = None, resource_server_url: str | None = None, workcell_server_url: str | None = None, location_server_url: str | None = None) ‑> Callable[[type], type]`
:   Class decorator that establishes a MadsciContext for method calls.

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

`set_current_madsci_context(context: madsci.common.types.context_types.MadsciContext) ‑> None`
:   Sets the current MadsciContext object.

`with_event_client(func: Callable[~P, ~R] | None = None, *, name: str | None = None, inherit: bool = True, **context_metadata: Any) ‑> Callable[~P, ~R] | Callable[[Callable[~P, ~R]], Callable[~P, ~R]]`
:   Decorator that establishes an EventClient context for a function.

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

`with_madsci_context(func: Callable[~P, ~R] | None = None, *, lab_server_url: str | None = None, event_server_url: str | None = None, experiment_server_url: str | None = None, data_server_url: str | None = None, resource_server_url: str | None = None, workcell_server_url: str | None = None, location_server_url: str | None = None) ‑> Callable[~P, ~R] | Callable[[Callable[~P, ~R]], Callable[~P, ~R]]`
:   Decorator that establishes a MadsciContext for a function.

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
