Module madsci.common.ownership
==============================
Provides the OwnershipHandler class for managing global ownership context of objects throughout a MADSci system component.

Variables
---------

`global_ownership_info`
:   Global ownership info
    To change the ownership info for a system component, set fields on this object.
    This is then used by the ownership_context context manager to create temporary ownership contexts as needed.

Functions
---------

`get_current_ownership_info() ‑> madsci.common.types.auth_types.OwnershipInfo`
:   Returns the current OwnershipInfo object.

`has_ownership_context() ‑> bool`
:   Check if an ownership context different from global is active.
    
    Returns:
        True if a non-global ownership context is active, False otherwise.

`ownership_class(user_id: str | None = None, experiment_id: str | None = None, campaign_id: str | None = None, project_id: str | None = None, node_id: str | None = None, workcell_id: str | None = None, lab_id: str | None = None, step_id: str | None = None, workflow_id: str | None = None, manager_id: str | None = None) ‑> Callable[[type], type]`
:   Class decorator that establishes an OwnershipInfo context for method calls.
    
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

`ownership_context(**overrides: Any) ‑> Generator[madsci.common.types.auth_types.OwnershipInfo, None, None]`
:   Updates the current OwnershipInfo (as returned by get_current_ownership_info) with the provided overrides.

`with_ownership(func: Callable[~P, typing.Any] | None = None, *, user_id: str | None = None, experiment_id: str | None = None, campaign_id: str | None = None, project_id: str | None = None, node_id: str | None = None, workcell_id: str | None = None, lab_id: str | None = None, step_id: str | None = None, workflow_id: str | None = None, manager_id: str | None = None) ‑> Callable[~P, typing.Any] | Callable[[Callable[~P, typing.Any]], Callable[~P, typing.Any]]`
:   Decorator that establishes an OwnershipInfo context for a function.
    
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