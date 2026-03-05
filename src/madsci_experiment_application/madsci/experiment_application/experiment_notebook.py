"""ExperimentNotebook modality for Jupyter notebook experiments.

This module provides the ExperimentNotebook class, designed for interactive
experiment execution in Jupyter notebooks with rich output and cell-by-cell
execution support.
"""

from typing import Any, ClassVar, Optional

from madsci.common.types.experiment_types import ExperimentStatus
from madsci.experiment_application.experiment_base import (
    ExperimentBase,
    ExperimentBaseConfig,
)
from pydantic import Field


class ExperimentNotebookConfig(ExperimentBaseConfig):
    """Configuration for notebook-based experiments.

    Extends ExperimentBaseConfig with notebook-specific display options.
    """

    rich_output: bool = Field(
        default=True,
        title="Rich Output",
        description="Use Rich library for formatted output in notebooks.",
    )
    auto_display_results: bool = Field(
        default=True,
        title="Auto Display Results",
        description="Automatically display results after workflow completion.",
    )


class ExperimentNotebook(ExperimentBase):
    """Experiment modality for Jupyter notebooks.

    Provides notebook-friendly features like:
    - Rich display of results
    - Cell-based execution (start/end in separate cells)
    - Interactive status updates
    - Context manager support for simple cases

    The recommended pattern for notebooks is:
    1. Create experiment instance in one cell
    2. Call start() to begin the experiment
    3. Execute experiment steps in subsequent cells
    4. Call end() to complete the experiment

    Example (cell-by-cell):
        ```python
        # Cell 1: Setup
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentNotebook

        class MyExperiment(ExperimentNotebook):
            experiment_design = ExperimentDesign(
                experiment_name="Notebook Experiment"
            )

        exp = MyExperiment(lab_server_url="http://localhost:8000/")

        # Cell 2: Start
        exp.start()

        # Cell 3: Run workflow
        result = exp.run_workflow("synthesis")

        # Cell 4: Display results
        exp.display(result, title="Synthesis Results")

        # Cell 5: End
        exp.end()
        ```

    Example (context manager):
        ```python
        # All in one cell
        with MyExperiment() as exp:
            result = exp.run_workflow("synthesis")
            exp.display(result)
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: Notebook-specific configuration
    """

    config: ExperimentNotebookConfig  # type: ignore[assignment]
    config_model: ClassVar[type[ExperimentNotebookConfig]] = ExperimentNotebookConfig
    _is_started: bool = False

    def start(
        self,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> "ExperimentNotebook":
        """Start the experiment for notebook use.

        Unlike the context manager pattern, this allows cell-by-cell
        execution in notebooks. Call end() when finished.

        Args:
            run_name: Optional name for this run.
            run_description: Optional description for this run.

        Returns:
            Self for method chaining.

        Example:
            exp = MyExperiment()
            exp.start(run_name="Run 1")  # Returns self
        """
        if self._is_started:
            self.logger.warning(
                "Experiment already started. Call end() before starting a new run."
            )
            return self

        self.start_experiment_run(run_name=run_name, run_description=run_description)
        self._is_started = True

        # Display startup info in notebook
        self._display_status("Experiment Started")

        return self

    def end(self, status: Optional[ExperimentStatus] = None) -> "ExperimentNotebook":
        """End the experiment.

        Args:
            status: Final status (defaults to COMPLETED).

        Returns:
            Self for method chaining.
        """
        if not self._is_started:
            self.logger.warning("Experiment not started. Call start() first.")
            return self

        self.end_experiment(status=status)
        self._is_started = False

        # Display summary in notebook
        self._display_summary()

        return self

    def run_workflow(
        self,
        workflow_name: str,
        parameters: Optional[dict[str, Any]] = None,
        display_result: bool = True,
    ) -> Any:
        """Run a workflow and optionally display results.

        Convenience method that wraps workcell_client.run_workflow()
        with notebook-friendly display.

        Args:
            workflow_name: Name of workflow to run.
            parameters: Workflow parameters.
            display_result: Whether to display result in notebook.

        Returns:
            Workflow result.

        Raises:
            RuntimeError: If experiment not started.

        Example:
            result = exp.run_workflow("synthesis", {"temperature": 25})
        """
        if not self._is_started:
            raise RuntimeError("Experiment not started. Call start() first.")

        result = self.workcell_client.run_workflow(
            workflow_name=workflow_name,
            parameters=parameters or {},
        )

        if display_result and self.config.auto_display_results:
            self.display(result, title=f"Workflow: {workflow_name}")

        return result

    def display(self, data: Any, title: Optional[str] = None) -> None:
        """Display data in notebook-friendly format.

        Uses Rich for formatting when available and enabled.

        Args:
            data: Data to display (dict, list, or any object).
            title: Optional title for the display panel.

        Example:
            exp.display({"yield": 0.95, "purity": 0.99}, title="Results")
        """
        if not self.config.rich_output:
            self._display_plain(data, title)
            return

        try:
            # Rich is an optional dependency - import locally
            from rich.console import Console  # noqa: PLC0415
            from rich.panel import Panel  # noqa: PLC0415
            from rich.pretty import Pretty  # noqa: PLC0415

            console = Console()
            content = Pretty(data)
            if title:
                console.print(Panel(content, title=title))
            else:
                console.print(content)
        except ImportError:
            # Fallback without Rich
            self._display_plain(data, title)

    def _display_plain(self, data: Any, title: Optional[str] = None) -> None:
        """Display data without Rich formatting."""
        if title:
            print(f"=== {title} ===")  # noqa: T201
        print(data)  # noqa: T201

    def _display_status(self, message: str) -> None:
        """Display status message in notebook."""
        experiment_name = (
            self.experiment_design.experiment_name
            if self.experiment_design
            else "Unknown"
        )
        experiment_id = self.experiment.experiment_id if self.experiment else "N/A"

        if self.config.rich_output:
            try:
                # Rich is an optional dependency - import locally
                from rich.console import Console  # noqa: PLC0415
                from rich.panel import Panel  # noqa: PLC0415

                console = Console()
                console.print(
                    Panel(
                        f"[bold green]{message}[/bold green]\n"
                        f"Experiment: {experiment_name}\n"
                        f"ID: {experiment_id}",
                        title="Experiment Status",
                    )
                )
                return
            except ImportError:
                pass

        # Fallback
        print(f"[{message}] {experiment_name} (ID: {experiment_id})")  # noqa: T201

    def _display_summary(self) -> None:
        """Display experiment summary in notebook."""
        if not self.experiment:
            return

        experiment_name = (
            self.experiment.experiment_design.experiment_name
            if self.experiment.experiment_design
            else "Unknown"
        )

        summary = {
            "experiment_id": self.experiment.experiment_id,
            "name": experiment_name,
            "status": (
                self.experiment.status.value if self.experiment.status else "unknown"
            ),
            "started_at": (
                str(self.experiment.started_at) if self.experiment.started_at else None
            ),
            "ended_at": (
                str(self.experiment.ended_at) if self.experiment.ended_at else None
            ),
        }

        self.display(summary, title="Experiment Summary")

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    def __enter__(self) -> "ExperimentNotebook":
        """Enter context manager - starts experiment."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> bool:
        """Exit context manager - ends experiment."""
        if exc_type is not None:
            self.handle_exception(exc_val)  # type: ignore[arg-type]
            self.end(ExperimentStatus.FAILED)
            return False
        self.end()
        return False

    # =========================================================================
    # Override run_experiment for notebook use
    # =========================================================================

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:
        """Not typically used in notebook modality.

        For notebooks, use the start()/end() pattern with run_workflow()
        calls in between. This method is provided for compatibility but
        notebooks typically don't use it directly.

        If you want to run a complete experiment in one cell, consider
        using ExperimentScript instead.
        """
        raise NotImplementedError(
            "ExperimentNotebook uses start()/run_workflow()/end() pattern. "
            "Use ExperimentScript for single-execution experiments."
        )
