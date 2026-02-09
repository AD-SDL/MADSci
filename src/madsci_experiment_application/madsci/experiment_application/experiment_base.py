"""Base class for all experiment modalities.

This module provides the ExperimentBase class, which contains the core
experiment lifecycle management functionality shared across all experiment
modalities (Script, Notebook, TUI, Node).

The key design principle is composition over inheritance: ExperimentBase
uses MadsciClientMixin for client management rather than inheriting from
RestNode, making it lighter weight for non-server use cases.
"""

import contextlib
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar, Generator, Optional, Union

from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.event_client import EventClient
from madsci.common.context import (
    event_client_context,
    set_current_madsci_context,
)
from madsci.common.exceptions import ExperimentCancelledError, ExperimentFailedError
from madsci.common.types.base_types import MadsciBaseSettings, PathLike
from madsci.common.types.event_types import EventType
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from pydantic import AnyUrl, Field


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
    This is intentionally simpler than the full RestNodeConfig used by
    the legacy ExperimentApplication.
    """

    # Lab connection
    lab_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Lab Server URL",
        description="URL of the lab server for context and service discovery.",
    )

    # Manager URLs (can be auto-discovered from lab_server_url)
    event_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Event Manager URL",
        description="URL of the event manager for logging.",
    )
    experiment_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Experiment Manager URL",
        description="URL of the experiment manager.",
    )
    workcell_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Workcell Manager URL",
        description="URL of the workcell manager for workflow execution.",
    )
    data_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Data Manager URL",
        description="URL of the data manager for data storage.",
    )
    resource_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Resource Manager URL",
        description="URL of the resource manager for inventory tracking.",
    )
    location_server_url: Optional[AnyUrl] = Field(
        default=None,
        title="Location Manager URL",
        description="URL of the location manager.",
    )


class ExperimentBase(MadsciClientMixin):
    """Base class for all experiment modalities.

    Provides core experiment lifecycle management using composition rather
    than inheritance from RestNode. All manager clients are available via
    the MadsciClientMixin.

    This is the foundation class that ExperimentScript, ExperimentNotebook,
    ExperimentTUI, and ExperimentNode all inherit from.

    Subclasses should:
    1. Set `experiment_design` class attribute or pass in __init__
    2. Override `run_experiment()` with experiment logic
    3. Use `manage_experiment()` context manager for automatic lifecycle

    Example:
        class MyExperiment(ExperimentBase):
            experiment_design = ExperimentDesign(
                experiment_name="My Experiment",
                experiment_description="A simple experiment"
            )

            def run_experiment(self):
                with self.manage_experiment():
                    result = self.workcell_client.run_workflow("my_workflow")
                    return result

    Attributes:
        experiment_design: The design template for this experiment
        experiment: The current experiment instance (set after start_experiment_run)
        config: Configuration settings for this experiment

    Client Properties (inherited from MadsciClientMixin):
        event_client: EventClient for logging
        experiment_client: ExperimentClient for experiment management
        workcell_client: WorkcellClient for workflow execution
        data_client: DataClient for data storage
        resource_client: ResourceClient for inventory
        location_client: LocationClient for locations
        lab_client: LabClient for lab configuration
    """

    # Client requirements for MadsciClientMixin
    # All clients are optional - they'll be initialized on first access
    OPTIONAL_CLIENTS: ClassVar[list[str]] = [
        "experiment",
        "workcell",
        "location",
        "lab",
        "event",
        "resource",
        "data",
    ]

    # Class attributes that can be set by subclasses
    experiment_design: Optional[Union[ExperimentDesign, PathLike]] = None
    """The design template for this experiment."""

    experiment: Optional[Experiment] = None
    """The current experiment instance (populated after start_experiment_run)."""

    config: ExperimentBaseConfig = None  # type: ignore[assignment]
    """Configuration for this experiment."""

    config_model: ClassVar[type[ExperimentBaseConfig]] = ExperimentBaseConfig
    """The Pydantic model class for configuration."""

    def __init__(
        self,
        experiment_design: Optional[Union[ExperimentDesign, PathLike]] = None,
        experiment: Optional[Experiment] = None,
        config: Optional[ExperimentBaseConfig] = None,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the experiment base.

        Args:
            experiment_design: Design for new experiments. Can be an ExperimentDesign
                instance or a path to a YAML file.
            experiment: Existing experiment to continue (optional).
            config: Configuration settings. If not provided, will be created
                from config_model with any kwargs as overrides.
            lab_server_url: Override for lab server URL. Takes precedence over
                config.lab_server_url.
            **kwargs: Additional configuration overrides passed to config_model.
        """
        # Initialize config
        self.config = config if config is not None else self.config_model(**kwargs)

        # Setup server URLs from config and overrides
        self._configure_server_urls(lab_server_url)

        # Setup experiment design
        self.experiment_design = experiment_design or self.experiment_design
        if isinstance(self.experiment_design, (str, Path)):
            self.experiment_design = ExperimentDesign.from_yaml(self.experiment_design)

        self.experiment = experiment

        # Setup lab context and clients
        self._setup_lab_context()
        self.setup_clients()

    def _configure_server_urls(
        self, lab_server_url: Optional[Union[str, AnyUrl]]
    ) -> None:
        """Configure server URLs from config and overrides.

        Args:
            lab_server_url: Optional override for lab server URL.
        """
        # Set lab_server_url with override taking precedence
        if lab_server_url:
            self.lab_server_url = str(lab_server_url)
        elif self.config.lab_server_url:
            self.lab_server_url = str(self.config.lab_server_url)

        # Copy server URLs from config to instance attributes for MadsciClientMixin
        url_mappings = [
            ("event_server_url", self.config.event_server_url),
            ("experiment_server_url", self.config.experiment_server_url),
            ("workcell_server_url", self.config.workcell_server_url),
            ("data_server_url", self.config.data_server_url),
            ("resource_server_url", self.config.resource_server_url),
            ("location_server_url", self.config.location_server_url),
        ]
        for attr_name, url in url_mappings:
            if url:
                setattr(self, attr_name, str(url))

    def _setup_lab_context(self) -> None:
        """Setup lab context if lab_server_url is available."""
        if hasattr(self, "lab_server_url") and self.lab_server_url:
            with contextlib.suppress(Exception):
                # Lab server may not be available, continue without context
                set_current_madsci_context(self.lab_client.get_lab_context())

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
        the created Experiment object. This sets self.experiment to the
        newly created experiment.

        Args:
            run_name: Optional name for this specific run.
            run_description: Optional description for this run.

        Returns:
            The created Experiment object.

        Raises:
            ValueError: If experiment_design is not set.
            TypeError: If experiment_design is not an ExperimentDesign instance.
        """
        if self.experiment_design is None:
            raise ValueError(
                "experiment_design is required to start a new experiment run"
            )

        if not isinstance(self.experiment_design, ExperimentDesign):
            raise TypeError(
                "experiment_design must be an ExperimentDesign instance "
                "(or a path/string that can be loaded to one)"
            )

        self.experiment = self.experiment_client.start_experiment(
            experiment_design=self.experiment_design,
            run_name=run_name,
            run_description=run_description,
        )

        experiment_name = (
            self.experiment.experiment_design.experiment_name
            if self.experiment.experiment_design
            else "Unknown"
        )
        self.logger.info(
            "Experiment run started",
            event_type=EventType.EXPERIMENT_START,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=experiment_name,
        )

        return self.experiment

    def end_experiment(
        self, status: Optional[ExperimentStatus] = None
    ) -> Optional[Experiment]:
        """End the current experiment run.

        Args:
            status: Final status for the experiment. Defaults to COMPLETED.

        Returns:
            The updated Experiment object, or None if no experiment is active.
        """
        if self.experiment is None:
            self.logger.warning("No active experiment to end")
            return None

        experiment_id = self.experiment.experiment_id
        updated_experiment: Experiment = self.experiment_client.end_experiment(
            experiment_id=experiment_id,
            status=status,
        )
        self.experiment = updated_experiment

        # Determine appropriate event type based on status
        if status == ExperimentStatus.FAILED:
            event_type = EventType.EXPERIMENT_FAILED
        elif status == ExperimentStatus.CANCELLED:
            event_type = EventType.EXPERIMENT_CANCELLED
        else:
            event_type = EventType.EXPERIMENT_COMPLETE

        experiment_name = (
            updated_experiment.experiment_design.experiment_name
            if updated_experiment.experiment_design
            else "Unknown"
        )
        self.logger.info(
            "Experiment run ended",
            event_type=event_type,
            experiment_id=updated_experiment.experiment_id,
            run_name=updated_experiment.run_name,
            experiment_name=experiment_name,
            status=str(status) if status else "completed",
        )

        return self.experiment

    def pause_experiment(self) -> Optional[Experiment]:
        """Pause the current experiment.

        Returns:
            The updated Experiment object, or None if no experiment is active.
        """
        if self.experiment is None:
            self.logger.warning("No active experiment to pause")
            return None

        self.experiment = self.experiment_client.pause_experiment(
            experiment_id=self.experiment.experiment_id
        )

        experiment_name = (
            self.experiment.experiment_design.experiment_name
            if self.experiment.experiment_design
            else "Unknown"
        )

        self.logger.info(
            "Experiment run paused",
            event_type=EventType.EXPERIMENT_PAUSE,
            experiment_id=self.experiment.experiment_id,
            run_name=self.experiment.run_name,
            experiment_name=experiment_name,
        )

        return self.experiment

    def cancel_experiment(self) -> Optional[Experiment]:
        """Cancel the current experiment.

        Returns:
            The updated Experiment object, or None if no experiment is active.
        """
        if self.experiment is None:
            self.logger.warning("No active experiment to cancel")
            return None

        experiment_id = self.experiment.experiment_id
        updated_experiment: Experiment = self.experiment_client.cancel_experiment(
            experiment_id=experiment_id
        )
        self.experiment = updated_experiment

        experiment_name = (
            updated_experiment.experiment_design.experiment_name
            if updated_experiment.experiment_design
            else "Unknown"
        )
        self.logger.info(
            "Experiment run cancelled",
            event_type=EventType.EXPERIMENT_CANCELLED,
            experiment_id=updated_experiment.experiment_id,
            run_name=updated_experiment.run_name,
            experiment_name=experiment_name,
        )

        return self.experiment

    def fail_experiment(self) -> Optional[Experiment]:
        """Mark the current experiment as failed.

        Returns:
            The updated Experiment object, or None if no experiment is active.
        """
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

        Automatically starts the experiment run on entry and ends it on exit.
        Exceptions are caught, logged, and the experiment is marked as failed.

        This is the recommended way to run experiments as it ensures proper
        lifecycle management and context propagation for logging.

        Args:
            run_name: Optional name for this run.
            run_description: Optional description for this run.

        Yields:
            Self, for method chaining within the context.

        Example:
            with self.manage_experiment(run_name="Run 1") as exp:
                result = exp.workcell_client.run_workflow("synthesis")
                # Experiment automatically ends on exit
        """
        self.start_experiment_run(run_name=run_name, run_description=run_description)

        # Build context for hierarchical logging
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

        This method is called when an exception occurs within
        manage_experiment(). Override this method for custom exception
        handling behavior.

        The default implementation logs the error and marks the experiment
        as failed.

        Args:
            exception: The exception that occurred.
        """
        self.logger.error(
            "Experiment run raised exception",
            event_type=EventType.EXPERIMENT_FAILED,
            experiment_id=self.experiment.experiment_id if self.experiment else None,
            run_name=self.experiment.run_name if self.experiment else None,
            experiment_name=(
                self.experiment.experiment_design.experiment_name
                if self.experiment and self.experiment.experiment_design
                else None
            ),
            error=str(exception),
        )
        self.end_experiment(ExperimentStatus.FAILED)

    # =========================================================================
    # Status Checking
    # =========================================================================

    def check_experiment_status(self) -> None:
        """Check current experiment status and handle state changes.

        This method polls the experiment manager for the current status
        and handles various states:
        - PAUSED: Waits until resumed
        - CANCELLED: Raises ExperimentCancelledError
        - FAILED: Raises ExperimentFailedError

        Call this periodically in long-running experiments to respond
        to external status changes (e.g., user cancellation via UI).

        Raises:
            ExperimentCancelledError: If the experiment was cancelled externally.
            ExperimentFailedError: If the experiment failed externally.
        """
        if self.experiment is None:
            return

        experiment_id = self.experiment.experiment_id
        # Note: get_experiment is incorrectly typed as returning dict in client,
        # but it actually returns Experiment. Using cast to fix type inference.
        _raw_exp = self.experiment_client.get_experiment(experiment_id=experiment_id)
        current_experiment: Experiment = (
            _raw_exp
            if isinstance(_raw_exp, Experiment)
            else Experiment.model_validate(_raw_exp)
        )
        self.experiment = current_experiment

        def _get_experiment_name() -> str:
            """Get experiment name safely."""
            if current_experiment.experiment_design:
                return current_experiment.experiment_design.experiment_name
            return "Unknown"

        # Handle paused state - wait for resume
        if current_experiment.status == ExperimentStatus.PAUSED:
            self.logger.warning(
                "Experiment run paused; waiting for resume",
                event_type=EventType.EXPERIMENT_PAUSE,
                experiment_id=current_experiment.experiment_id,
                experiment_name=_get_experiment_name(),
            )
            while True:
                time.sleep(5)
                _raw_exp = self.experiment_client.get_experiment(
                    experiment_id=experiment_id
                )
                current_experiment = (
                    _raw_exp
                    if isinstance(_raw_exp, Experiment)
                    else Experiment.model_validate(_raw_exp)
                )
                self.experiment = current_experiment
                if current_experiment.status != ExperimentStatus.PAUSED:
                    break

        # Handle terminal states
        if current_experiment.status == ExperimentStatus.CANCELLED:
            exc = ExperimentCancelledError(
                "Experiment manager reports that the experiment has been cancelled."
            )
            self.logger.error(
                "Experiment run cancelled externally",
                event_type=EventType.EXPERIMENT_CANCELLED,
                experiment_id=current_experiment.experiment_id,
                experiment_name=_get_experiment_name(),
            )
            raise exc

        if current_experiment.status == ExperimentStatus.FAILED:
            exc = ExperimentFailedError(
                "Experiment manager reports that the experiment has failed."
            )
            self.logger.error(
                "Experiment run failed externally",
                event_type=EventType.EXPERIMENT_FAILED,
                experiment_id=current_experiment.experiment_id,
                experiment_name=_get_experiment_name(),
            )
            raise exc

    # =========================================================================
    # Convenience Properties
    # =========================================================================

    @property
    def logger(self) -> EventClient:
        """Alias for event_client for logging convenience.

        Returns:
            The EventClient instance for logging.
        """
        return self.event_client

    @property
    def is_running(self) -> bool:
        """Check if an experiment is currently running.

        Returns:
            True if an experiment is active and in progress.
        """
        return (
            self.experiment is not None
            and self.experiment.status == ExperimentStatus.IN_PROGRESS
        )

    # =========================================================================
    # Class Methods
    # =========================================================================

    @classmethod
    def start_new(
        cls,
        experiment_design: Optional[ExperimentDesign] = None,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        **kwargs: Any,
    ) -> "ExperimentBase":
        """Create a new experiment instance and start a run.

        Convenience class method that creates an instance and immediately
        starts an experiment run.

        Args:
            experiment_design: The experiment design to use.
            lab_server_url: URL of the lab server.
            **kwargs: Additional arguments passed to __init__.

        Returns:
            A new ExperimentBase instance with an active experiment run.
        """
        instance = cls(
            experiment_design=experiment_design,
            lab_server_url=lab_server_url,
            **kwargs,
        )
        instance.start_experiment_run()
        return instance

    @classmethod
    def continue_experiment(
        cls,
        experiment: Experiment,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        **kwargs: Any,
    ) -> "ExperimentBase":
        """Create an instance to continue an existing experiment.

        Args:
            experiment: The existing Experiment to continue.
            lab_server_url: URL of the lab server.
            **kwargs: Additional arguments passed to __init__.

        Returns:
            A new ExperimentBase instance attached to the existing experiment.
        """
        instance = cls(
            experiment=experiment,
            experiment_design=experiment.experiment_design,
            lab_server_url=lab_server_url,
            **kwargs,
        )
        instance.experiment_client.continue_experiment(
            experiment_id=experiment.experiment_id
        )
        return instance

    # =========================================================================
    # Abstract Methods (for subclasses to implement)
    # =========================================================================

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:
        """Override this method with experiment logic.

        This method should contain the core experiment implementation.
        It will be called by modality-specific entry points.

        Args:
            *args: Positional arguments (modality-specific).
            **kwargs: Keyword arguments (modality-specific).

        Returns:
            Experiment results (format depends on experiment).

        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement run_experiment() with experiment logic"
        )
