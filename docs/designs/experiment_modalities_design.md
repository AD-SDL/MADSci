# MADSci Experiment Modalities Design Document

**Status**: Draft
**Date**: 2026-02-08
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for Phase 4 of the UX Overhaul: ExperimentApplication Modalities. The goal is to support different experiment execution contexts explicitly, allowing scientists to work in their preferred environments (scripts, notebooks, interactive TUI, or server mode).

## Problem Statement

### Current State

The current `ExperimentApplication` class inherits from `RestNode`, which means:

1. **Server mode baggage**: Even simple scripts carry REST server infrastructure
2. **Configuration complexity**: `ExperimentApplicationConfig` extends `RestNodeConfig`, bringing node-specific settings
3. **Single pattern**: All experiments follow the same pattern regardless of execution context
4. **Mixed concerns**: Experiment lifecycle is tightly coupled to node lifecycle

### Current Class Hierarchy

```
RestNode (from madsci.node_module.rest_node_module)
    └── ExperimentApplication
            └── User's experiment class
```

### Goals

1. **Separation of concerns**: Decouple experiment lifecycle from server infrastructure
2. **Multiple modalities**: Support scripts, notebooks, TUI, and server modes explicitly
3. **Composition over inheritance**: Use mixins for client management instead of deep inheritance
4. **Progressive complexity**: Simpler modalities have simpler implementations
5. **Backward compatibility**: Existing `ExperimentApplication` users can migrate gradually

---

## New Architecture

### Design Principles

1. **ExperimentBase uses composition**: Client management via `MadsciClientMixin`, not node inheritance
2. **Modalities extend ExperimentBase**: Each modality adds context-specific features
3. **ExperimentNode wraps RestNode**: Only server mode needs RestNode functionality
4. **Configuration is modality-specific**: Each modality has its own focused config class

### Class Hierarchy

```
MadsciClientMixin (from madsci.client.client_mixin)
    └── ExperimentBase (new, core lifecycle)
            ├── ExperimentScript (simplest, run-once)
            ├── ExperimentNotebook (Jupyter-friendly)
            ├── ExperimentTUI (interactive terminal)
            └── ExperimentNode (server mode, wraps RestNode)

ExperimentApplication (deprecated, wraps ExperimentNode for backward compat)
```

### Key Design Decisions

1. **No breaking changes initially**: `ExperimentApplication` remains but is marked deprecated
2. **MadsciClientMixin for clients**: All modalities get clients the same way
3. **Context manager pattern**: `manage_experiment()` works across all modalities
4. **Modality-specific entry points**: Each modality has a clear `run()` or `start()` method

---

## Type Definitions

### ExperimentBaseConfig

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_base.py

class ExperimentBaseConfig(
    MadsciBaseSettings,
    env_file=(".env", "experiment.env"),
    toml_file=("settings.toml", "experiment.settings.toml"),
    yaml_file=("settings.yaml", "experiment.settings.yaml"),
    json_file=("settings.json", "experiment.settings.json"),
    env_prefix="EXPERIMENT_",
):
    """Base configuration for all experiment modalities.

    Contains only experiment-relevant settings, not server/node settings.
    """

    # Lab connection
    lab_server_url: Optional[AnyUrl] = None
    """The URL of the lab server to connect to for context and service discovery."""

    # Manager URLs (can be auto-discovered from lab_server_url)
    event_server_url: Optional[AnyUrl] = None
    experiment_server_url: Optional[AnyUrl] = None
    workcell_server_url: Optional[AnyUrl] = None
    data_server_url: Optional[AnyUrl] = None
    resource_server_url: Optional[AnyUrl] = None
    location_server_url: Optional[AnyUrl] = None
```

### ExperimentScriptConfig

```python
class ExperimentScriptConfig(ExperimentBaseConfig):
    """Configuration for script-based experiments."""

    # Script execution
    run_args: list[Any] = Field(default_factory=list)
    """Positional arguments to pass to run_experiment()."""
    run_kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass to run_experiment()."""
```

### ExperimentNotebookConfig

```python
class ExperimentNotebookConfig(ExperimentBaseConfig):
    """Configuration for notebook-based experiments."""

    # Display settings
    rich_output: bool = True
    """Use Rich for formatted output in notebooks."""
    progress_widget: bool = True
    """Show interactive progress widgets (IPywidgets)."""
    auto_display_results: bool = True
    """Automatically display results after workflow completion."""
```

### ExperimentTUIConfig

```python
class ExperimentTUIConfig(ExperimentBaseConfig):
    """Configuration for TUI-based experiments."""

    # TUI settings
    refresh_interval: float = 1.0
    """Status refresh interval in seconds."""
    show_logs: bool = True
    """Show log panel in TUI."""
```

### ExperimentNodeConfig

```python
class ExperimentNodeConfig(ExperimentBaseConfig):
    """Configuration for node-based experiments (server mode).

    Extends base config with REST server settings.
    """

    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 6000
    cors_enabled: bool = True
    cors_origins: list[str] = ["*"]

    # Node identity (for registration with workcell)
    node_name: Optional[str] = None
    """Name for registering with workcell. Defaults to experiment name."""
```

---

## Implementation

### ExperimentBase

The core class that all modalities inherit from:

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_base.py

class ExperimentBase(MadsciClientMixin):
    """Base class for all experiment modalities.

    Provides core experiment lifecycle management using composition rather
    than inheritance from RestNode. All manager clients are available via
    the MadsciClientMixin.

    Subclasses should:
    1. Set `experiment_design` class attribute or pass in __init__
    2. Override `run_experiment()` with experiment logic
    3. Use `manage_experiment()` context manager for automatic lifecycle

    Example:
        class MyExperiment(ExperimentBase):
            experiment_design = ExperimentDesign(name="My Experiment")

            def run_experiment(self):
                with self.manage_experiment():
                    result = self.workcell_client.run_workflow("my_workflow")
                    return result
    """

    # Client requirements
    OPTIONAL_CLIENTS: ClassVar[list[str]] = [
        "experiment", "workcell", "location", "lab", "event", "resource", "data"
    ]

    # Class attributes
    experiment_design: Optional[ExperimentDesign] = None
    experiment: Optional[Experiment] = None
    config: ExperimentBaseConfig
    config_model: type[ExperimentBaseConfig] = ExperimentBaseConfig

    def __init__(
        self,
        experiment_design: Optional[ExperimentDesign] = None,
        experiment: Optional[Experiment] = None,
        config: Optional[ExperimentBaseConfig] = None,
        lab_server_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize experiment base.

        Args:
            experiment_design: Design for new experiments
            experiment: Existing experiment to continue
            config: Configuration settings
            lab_server_url: Override lab server URL
            **kwargs: Additional config overrides
        """
        # Initialize config
        if config is not None:
            self.config = config
        else:
            self.config = self.config_model(**kwargs)

        # Override lab_server_url if provided
        if lab_server_url:
            self.lab_server_url = lab_server_url
        elif self.config.lab_server_url:
            self.lab_server_url = str(self.config.lab_server_url)

        # Setup experiment design
        self.experiment_design = experiment_design or self.experiment_design
        if isinstance(self.experiment_design, (str, Path)):
            self.experiment_design = ExperimentDesign.from_yaml(self.experiment_design)

        self.experiment = experiment

        # Setup lab context and clients
        if hasattr(self, 'lab_server_url') and self.lab_server_url:
            set_current_madsci_context(self.lab_client.get_lab_context())

        self.setup_clients()

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def start_experiment_run(
        self,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> Experiment:
        """Start a new experiment run.

        Registers the experiment with the Experiment Manager and returns
        the created Experiment object.

        Args:
            run_name: Optional name for this run
            run_description: Optional description for this run

        Returns:
            The created Experiment object

        Raises:
            ValueError: If experiment_design is not set
        """
        if self.experiment_design is None:
            raise ValueError("experiment_design is required to start a new experiment run")

        self.experiment = self.experiment_client.start_experiment(
            experiment_design=self.experiment_design,
            run_name=run_name,
            run_description=run_description,
        )

        self.logger.info(
            "Experiment run started",
            event_type=EventType.EXPERIMENT_START,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
        )

        return self.experiment

    def end_experiment(self, status: Optional[ExperimentStatus] = None) -> Experiment:
        """End the current experiment run.

        Args:
            status: Final status (defaults to COMPLETED)

        Returns:
            The updated Experiment object
        """
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id,
            status=status,
        )

        event_type = (
            EventType.EXPERIMENT_COMPLETE
            if status in {None, ExperimentStatus.COMPLETED}
            else EventType.EXPERIMENT_FAILED
            if status == ExperimentStatus.FAILED
            else EventType.EXPERIMENT_COMPLETE
        )

        self.logger.info(
            "Experiment run ended",
            event_type=event_type,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=self.experiment.experiment_design.experiment_name,
            status=str(status) if status else None,
        )

        return self.experiment

    def pause_experiment(self) -> Experiment:
        """Pause the current experiment."""
        self.experiment = self.experiment_client.pause_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.info(
            "Experiment run paused",
            event_type=EventType.EXPERIMENT_PAUSE,
            experiment_id=self.experiment.experiment_id,
        )
        return self.experiment

    def cancel_experiment(self) -> Experiment:
        """Cancel the current experiment."""
        self.experiment = self.experiment_client.cancel_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.info(
            "Experiment run cancelled",
            event_type=EventType.EXPERIMENT_CANCELLED,
            experiment_id=self.experiment.experiment_id,
        )
        return self.experiment

    def fail_experiment(self) -> Experiment:
        """Mark the current experiment as failed."""
        return self.end_experiment(status=ExperimentStatus.FAILED)

    # =========================================================================
    # Context Manager
    # =========================================================================

    @contextmanager
    def manage_experiment(
        self,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> Generator["ExperimentBase", None, None]:
        """Context manager for experiment lifecycle.

        Automatically starts and ends the experiment, handling exceptions
        appropriately.

        Args:
            run_name: Optional name for this run
            run_description: Optional description

        Yields:
            Self for chaining

        Example:
            with self.manage_experiment() as exp:
                result = exp.workcell_client.run_workflow("my_workflow")
        """
        self.start_experiment_run(run_name=run_name, run_description=run_description)

        experiment_id = self.experiment.experiment_id if self.experiment else None
        experiment_name = (
            self.experiment.experiment_design.experiment_name
            if self.experiment and self.experiment.experiment_design
            else None
        )

        with event_client_context(
            name="experiment",
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            run_name=run_name,
            experiment_type=self.__class__.__name__,
        ):
            try:
                yield self
            except Exception as e:
                self.handle_exception(e)
                raise
            else:
                self.end_experiment()

    # =========================================================================
    # Exception Handling
    # =========================================================================

    def handle_exception(self, exception: Exception) -> None:
        """Handle an exception during experiment execution.

        Override this method for custom exception handling.

        Args:
            exception: The exception that occurred
        """
        self.logger.error(
            "Experiment run raised exception",
            event_type=EventType.EXPERIMENT_FAILED,
            experiment_id=self.experiment.experiment_id if self.experiment else None,
            error=str(exception),
        )
        self.end_experiment(ExperimentStatus.FAILED)

    # =========================================================================
    # Status Checking
    # =========================================================================

    def check_experiment_status(self) -> None:
        """Check current experiment status and handle state changes.

        Raises:
            ExperimentCancelledError: If experiment was cancelled
            ExperimentFailedError: If experiment failed externally
        """
        self.experiment = self.experiment_client.get_experiment(
            experiment_id=self.experiment.experiment_id
        )

        if self.experiment.status == ExperimentStatus.PAUSED:
            self.logger.warning(
                "Experiment run paused; waiting for resume",
                event_type=EventType.EXPERIMENT_PAUSE,
                experiment_id=self.experiment.experiment_id,
            )
            while True:
                time.sleep(5)
                self.experiment = self.experiment_client.get_experiment(
                    experiment_id=self.experiment.experiment_id
                )
                if self.experiment.status != ExperimentStatus.PAUSED:
                    break

        if self.experiment.status == ExperimentStatus.CANCELLED:
            raise ExperimentCancelledError("Experiment has been cancelled.")
        elif self.experiment.status == ExperimentStatus.FAILED:
            raise ExperimentFailedError("Experiment has failed.")

    # =========================================================================
    # Convenience Properties
    # =========================================================================

    @property
    def logger(self) -> EventClient:
        """Alias for event_client for logging convenience."""
        return self.event_client

    # =========================================================================
    # Abstract Methods (for subclasses)
    # =========================================================================

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:
        """Override this method with experiment logic.

        This method should contain the core experiment implementation.
        It will be called by modality-specific entry points.

        Returns:
            Experiment results (format depends on experiment)
        """
        raise NotImplementedError("Subclasses must implement run_experiment()")
```

### ExperimentScript

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_script.py

class ExperimentScript(ExperimentBase):
    """Experiment modality for simple run-once scripts.

    This is the simplest experiment modality, designed for experiments
    that run once from start to finish without interaction.

    Example:
        class MyExperiment(ExperimentScript):
            experiment_design = ExperimentDesign(name="My Experiment")

            def run_experiment(self):
                # Your experiment logic here
                result = self.workcell_client.run_workflow("synthesis")
                return {"yield": result["product_mass"]}

        if __name__ == "__main__":
            MyExperiment().run()
    """

    config: ExperimentScriptConfig
    config_model = ExperimentScriptConfig

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the experiment.

        This is the main entry point for script-based experiments.
        It wraps run_experiment() with automatic lifecycle management.

        Args:
            *args: Passed to run_experiment()
            **kwargs: Passed to run_experiment()

        Returns:
            Results from run_experiment()
        """
        # Merge config args with passed args
        final_args = list(self.config.run_args) + list(args)
        final_kwargs = {**self.config.run_kwargs, **kwargs}

        with self.manage_experiment():
            return self.run_experiment(*final_args, **final_kwargs)

    @classmethod
    def main(cls, *args: Any, **kwargs: Any) -> Any:
        """Class method entry point for scripts.

        Convenience method for running experiments from __main__.

        Example:
            if __name__ == "__main__":
                MyExperiment.main()
        """
        instance = cls(*args, **kwargs)
        return instance.run()
```

### ExperimentNotebook

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_notebook.py

class ExperimentNotebook(ExperimentBase):
    """Experiment modality for Jupyter notebooks.

    Provides notebook-friendly features like:
    - Rich display of results
    - Progress widgets (optional)
    - Cell-based execution
    - Interactive status updates

    Example:
        # In a notebook cell:
        class MyExperiment(ExperimentNotebook):
            experiment_design = ExperimentDesign(name="My Experiment")

        exp = MyExperiment()

        # Start experiment (in another cell)
        exp.start()

        # Run steps (in subsequent cells)
        result = exp.run_workflow("synthesis")
        exp.display(result)

        # End experiment
        exp.end()
    """

    config: ExperimentNotebookConfig
    config_model = ExperimentNotebookConfig
    _is_started: bool = False

    def start(
        self,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> "ExperimentNotebook":
        """Start the experiment for notebook use.

        Unlike the context manager pattern, this allows cell-by-cell
        execution in notebooks.

        Args:
            run_name: Optional name for this run
            run_description: Optional description

        Returns:
            Self for method chaining
        """
        if self._is_started:
            self.logger.warning("Experiment already started")
            return self

        self.start_experiment_run(run_name=run_name, run_description=run_description)
        self._is_started = True

        # Display startup info in notebook
        self._display_status("Experiment Started")

        return self

    def end(self, status: Optional[ExperimentStatus] = None) -> "ExperimentNotebook":
        """End the experiment.

        Args:
            status: Final status (defaults to COMPLETED)

        Returns:
            Self for method chaining
        """
        if not self._is_started:
            self.logger.warning("Experiment not started")
            return self

        self.end_experiment(status=status)
        self._is_started = False

        # Display summary in notebook
        self._display_summary()

        return self

    def run_workflow(
        self,
        workflow_name: str,
        parameters: Optional[dict] = None,
        display_result: bool = True,
    ) -> Any:
        """Run a workflow and optionally display results.

        Convenience method that wraps workcell_client.run_workflow()
        with notebook-friendly display.

        Args:
            workflow_name: Name of workflow to run
            parameters: Workflow parameters
            display_result: Whether to display result in notebook

        Returns:
            Workflow result
        """
        if not self._is_started:
            raise RuntimeError("Experiment not started. Call start() first.")

        result = self.workcell_client.run_workflow(
            workflow_name=workflow_name,
            parameters=parameters or {},
        )

        if display_result and self.config.auto_display_results:
            self.display(result)

        return result

    def display(self, data: Any, title: Optional[str] = None) -> None:
        """Display data in notebook-friendly format.

        Uses Rich for formatting when available.

        Args:
            data: Data to display
            title: Optional title for the display
        """
        if not self.config.rich_output:
            print(data)
            return

        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.pretty import Pretty

            console = Console()
            content = Pretty(data)
            if title:
                console.print(Panel(content, title=title))
            else:
                console.print(content)
        except ImportError:
            # Fallback without Rich
            if title:
                print(f"=== {title} ===")
            print(data)

    def _display_status(self, message: str) -> None:
        """Display status message in notebook."""
        if self.config.rich_output:
            try:
                from rich.console import Console
                from rich.panel import Panel

                console = Console()
                console.print(Panel(
                    f"[bold green]{message}[/bold green]\n"
                    f"Experiment: {self.experiment_design.experiment_name}\n"
                    f"ID: {self.experiment.experiment_id if self.experiment else 'N/A'}",
                    title="Experiment Status",
                ))
            except ImportError:
                print(f"[{message}] {self.experiment_design.experiment_name}")
        else:
            print(f"[{message}] {self.experiment_design.experiment_name}")

    def _display_summary(self) -> None:
        """Display experiment summary in notebook."""
        if not self.experiment:
            return

        summary = {
            "experiment_id": self.experiment.experiment_id,
            "name": self.experiment_design.experiment_name,
            "status": self.experiment.status.value if self.experiment.status else "unknown",
            "started_at": str(self.experiment.started_at) if self.experiment.started_at else None,
            "ended_at": str(self.experiment.ended_at) if self.experiment.ended_at else None,
        }

        self.display(summary, title="Experiment Summary")

    # Allow use as context manager as well
    def __enter__(self) -> "ExperimentNotebook":
        """Enter context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager."""
        if exc_type is not None:
            self.handle_exception(exc_val)
            self.end(ExperimentStatus.FAILED)
            return False
        self.end()
        return False
```

### ExperimentTUI

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_tui.py

class ExperimentTUI(ExperimentBase):
    """Experiment modality with interactive terminal UI.

    Provides a Textual-based TUI for experiment control with:
    - Status display
    - Log viewer
    - Action controls
    - Real-time updates

    Example:
        class MyExperiment(ExperimentTUI):
            experiment_design = ExperimentDesign(name="My Experiment")

            def run_experiment(self):
                # Your experiment logic
                pass

        if __name__ == "__main__":
            MyExperiment().run_tui()
    """

    config: ExperimentTUIConfig
    config_model = ExperimentTUIConfig

    def run_tui(self) -> Any:
        """Launch the TUI for this experiment.

        This starts the Textual application with experiment controls.

        Returns:
            Experiment results after TUI exits
        """
        try:
            from madsci.experiment_application.tui import ExperimentTUIApp
        except ImportError:
            raise ImportError(
                "TUI support requires textual. "
                "Install with: pip install madsci[tui]"
            )

        app = ExperimentTUIApp(experiment=self)
        result = app.run()
        return result

    def run(self) -> Any:
        """Alias for run_tui() for consistency."""
        return self.run_tui()
```

### ExperimentNode

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_node.py

class ExperimentNode(ExperimentBase):
    """Experiment modality that runs as a REST node.

    This modality exposes the experiment as a REST API, allowing
    it to be controlled by the workcell manager like any other node.

    Example:
        class MyExperiment(ExperimentNode):
            experiment_design = ExperimentDesign(name="My Experiment")

            def run_experiment(self, sample_id: str) -> dict:
                # Called via REST API
                result = self.workcell_client.run_workflow(
                    "process_sample",
                    parameters={"sample_id": sample_id}
                )
                return result

        if __name__ == "__main__":
            MyExperiment().start_server()
    """

    config: ExperimentNodeConfig
    config_model = ExperimentNodeConfig
    _rest_node: Optional[RestNode] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the experiment node."""
        super().__init__(*args, **kwargs)

        # Create RestNode for server functionality
        from madsci.node_module.rest_node_module import RestNode

        class _ExperimentRestNode(RestNode):
            """Internal RestNode for experiment server."""
            pass

        self._rest_node = _ExperimentRestNode()

        # Register run_experiment as an action
        self._register_experiment_action()

    def _register_experiment_action(self) -> None:
        """Register run_experiment as a node action."""
        if self._rest_node is None:
            return

        # Wrap run_experiment with experiment management
        def wrapped_run(*args, **kwargs):
            with self.manage_experiment():
                return self.run_experiment(*args, **kwargs)

        self._rest_node._add_action(
            func=wrapped_run,
            action_name="run_experiment",
            description="Run the experiment",
            blocking=False,
        )

    def start_server(self) -> None:
        """Start the REST server for this experiment.

        The server exposes run_experiment as an action that can be
        called by the workcell manager.
        """
        if self._rest_node is None:
            raise RuntimeError("REST node not initialized")

        self._rest_node.start_node()

    def run(self) -> None:
        """Alias for start_server() for consistency."""
        self.start_server()
```

---

## Migration Path

### Backward Compatibility

The existing `ExperimentApplication` class will be preserved but marked deprecated:

```python
# src/madsci_experiment_application/madsci/experiment_application/experiment_application.py

import warnings
from madsci.experiment_application.experiment_node import ExperimentNode

class ExperimentApplication(ExperimentNode):
    """Experiment application for running automated experiments.

    .. deprecated:: 0.7.0
        Use ExperimentScript, ExperimentNotebook, ExperimentTUI, or
        ExperimentNode depending on your use case. ExperimentApplication
        will be removed in v0.8.0.

    Migration guide:
        - For simple scripts: ExperimentScript
        - For Jupyter notebooks: ExperimentNotebook
        - For interactive terminal: ExperimentTUI
        - For server mode: ExperimentNode (current behavior)
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "ExperimentApplication is deprecated. Use ExperimentScript, "
            "ExperimentNotebook, ExperimentTUI, or ExperimentNode instead. "
            "See https://ad-sdl.github.io/MADSci/migration/experiment-modalities",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

    def start_app(self) -> None:
        """Start the application (preserved for backward compatibility)."""
        if hasattr(self.config, 'server_mode') and self.config.server_mode:
            self.start_server()
        else:
            self.run()
```

### Migration Examples

**Before (ExperimentApplication)**:
```python
class MyExperiment(ExperimentApplication):
    experiment_design = ExperimentDesign(name="My Experiment")
    config = ExperimentApplicationConfig(server_mode=False)

    def run_experiment(self):
        result = self.workcell_client.run_workflow("my_workflow")
        return result

if __name__ == "__main__":
    MyExperiment().start_app()
```

**After (ExperimentScript)**:
```python
class MyExperiment(ExperimentScript):
    experiment_design = ExperimentDesign(name="My Experiment")

    def run_experiment(self):
        result = self.workcell_client.run_workflow("my_workflow")
        return result

if __name__ == "__main__":
    MyExperiment().run()
```

**Before (Server mode)**:
```python
class MyExperiment(ExperimentApplication):
    experiment_design = ExperimentDesign(name="My Experiment")
    config = ExperimentApplicationConfig(server_mode=True, port=6000)

    def run_experiment(self, param: str):
        return {"result": param}

if __name__ == "__main__":
    MyExperiment().start_app()
```

**After (ExperimentNode)**:
```python
class MyExperiment(ExperimentNode):
    experiment_design = ExperimentDesign(name="My Experiment")
    config = ExperimentNodeConfig(server_port=6000)

    def run_experiment(self, param: str):
        return {"result": param}

if __name__ == "__main__":
    MyExperiment().start_server()
```

---

## Template Updates

### New Template Structure

```
bundled_templates/experiment/
├── script/
│   ├── template.yaml
│   └── {{experiment_name}}.py.j2
├── notebook/
│   ├── template.yaml
│   └── {{experiment_name}}.ipynb.j2
├── tui/
│   ├── template.yaml
│   └── {{experiment_name}}.py.j2
└── node/
    ├── template.yaml
    └── {{experiment_name}}.py.j2
```

### Updated `madsci new experiment` Command

```
madsci new experiment --name my_experiment --modality script
madsci new experiment --name my_experiment --modality notebook
madsci new experiment --name my_experiment --modality tui
madsci new experiment --name my_experiment --modality node
```

---

## Testing Strategy

### Unit Tests

1. **ExperimentBase tests**:
   - Lifecycle methods (start, end, pause, cancel)
   - Context manager behavior
   - Exception handling
   - Client initialization

2. **Modality-specific tests**:
   - ExperimentScript.run()
   - ExperimentNotebook.start()/end()
   - ExperimentTUI.run_tui() (mock Textual)
   - ExperimentNode.start_server() (mock FastAPI)

### Integration Tests

1. **With mock managers**: Test full lifecycle without real services
2. **With docker compose**: Test against real manager services

---

## Success Metrics

1. **Migration complete**: All example experiments updated to new modalities
2. **Tests passing**: All new modality tests pass
3. **Documentation updated**: Migration guide published
4. **Templates working**: `madsci new experiment` generates working code for all modalities
5. **Backward compatible**: Existing ExperimentApplication code continues to work (with deprecation warning)

---

## Timeline

- **Day 1**: Implement ExperimentBase and ExperimentScript
- **Day 2**: Implement ExperimentNotebook and ExperimentTUI
- **Day 3**: Implement ExperimentNode and deprecate ExperimentApplication
- **Day 4**: Update templates and write tests
- **Day 5**: Update documentation and examples

---

## Appendix: File Structure

```
src/madsci_experiment_application/
├── madsci/
│   └── experiment_application/
│       ├── __init__.py                    # Exports all modalities
│       ├── experiment_base.py             # ExperimentBase + configs
│       ├── experiment_script.py           # ExperimentScript
│       ├── experiment_notebook.py         # ExperimentNotebook
│       ├── experiment_tui.py              # ExperimentTUI
│       ├── experiment_node.py             # ExperimentNode
│       ├── experiment_application.py      # Deprecated wrapper
│       └── tui/                           # TUI screens (optional dep)
│           ├── __init__.py
│           └── app.py
└── tests/
    ├── test_experiment_base.py
    ├── test_experiment_script.py
    ├── test_experiment_notebook.py
    ├── test_experiment_tui.py
    └── test_experiment_node.py
```
