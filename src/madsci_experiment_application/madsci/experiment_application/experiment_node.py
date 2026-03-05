"""ExperimentNode modality for server-mode experiments.

This module provides the ExperimentNode class, which runs experiments
as REST API servers that can be controlled by the workcell manager.
"""

from typing import Any, ClassVar, Optional, Union

from madsci.common.types.base_types import PathLike
from madsci.common.types.experiment_types import Experiment, ExperimentDesign
from madsci.experiment_application.experiment_base import (
    ExperimentBase,
    ExperimentBaseConfig,
)
from madsci.node_module.rest_node_module import RestNode
from pydantic import AnyUrl, Field


class ExperimentNodeConfig(ExperimentBaseConfig):
    """Configuration for node-based experiments (server mode).

    Extends ExperimentBaseConfig with REST server settings.
    """

    # Server settings
    server_host: str = Field(
        default="0.0.0.0",  # noqa: S104 - Binding to all interfaces is intentional for container deployments
        title="Server Host",
        description="Host to bind the REST server to.",
    )
    server_port: int = Field(
        default=6000,
        title="Server Port",
        description="Port to bind the REST server to.",
    )
    cors_enabled: bool = Field(
        default=True,
        title="CORS Enabled",
        description="Enable CORS for cross-origin requests.",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        title="CORS Origins",
        description="Allowed origins for CORS.",
    )

    # Node identity
    node_name: Optional[str] = Field(
        default=None,
        title="Node Name",
        description="Name for registering with workcell. Defaults to experiment name.",
    )


class ExperimentNode(ExperimentBase):
    """Experiment modality that runs as a REST node.

    This modality exposes the experiment as a REST API, allowing it to be
    controlled by the workcell manager like any other node. This is useful
    for experiments that need to be triggered remotely or integrated into
    automated workflows.

    The experiment's run_experiment() method is exposed as a node action
    that can be called via the REST API.

    Example:
        ```python
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentNode

        class MyExperiment(ExperimentNode):
            experiment_design = ExperimentDesign(
                experiment_name="Server Experiment"
            )

            def run_experiment(self, sample_id: str, temperature: float = 25.0):
                # Called via REST API: POST /actions/run_experiment
                result = self.workcell_client.run_workflow(
                    "process_sample",
                    parameters={"sample_id": sample_id, "temp": temperature}
                )
                return result

        if __name__ == "__main__":
            MyExperiment().start_server()
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: Node-specific configuration
    """

    config: ExperimentNodeConfig  # type: ignore[assignment]
    config_model: ClassVar[type[ExperimentNodeConfig]] = ExperimentNodeConfig
    _rest_node: Optional[RestNode] = None

    def __init__(
        self,
        experiment_design: Optional[Union[ExperimentDesign, PathLike]] = None,
        experiment: Optional[Experiment] = None,
        config: Optional[ExperimentNodeConfig] = None,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the experiment node.

        Args:
            experiment_design: Design for new experiments.
            experiment: Existing experiment to continue.
            config: Configuration settings.
            lab_server_url: Override for lab server URL.
            **kwargs: Additional configuration overrides.
        """
        super().__init__(
            experiment_design=experiment_design,
            experiment=experiment,
            config=config,
            lab_server_url=lab_server_url,
            **kwargs,
        )

        # Create the internal RestNode for server functionality
        self._setup_rest_node()

    def _setup_rest_node(self) -> None:
        """Set up the internal RestNode for server functionality."""
        # Create a RestNode subclass dynamically
        node_name = self.config.node_name or (
            self.experiment_design.experiment_name
            if self.experiment_design
            else "experiment_node"
        )

        # Import RestNodeConfig here to avoid circular imports
        from madsci.common.types.node_types import RestNodeConfig  # noqa: PLC0415

        # Create node config from our experiment config
        node_config = RestNodeConfig(
            node_name=node_name,
            host=self.config.server_host,
            port=self.config.server_port,
        )

        # Create the RestNode
        self._rest_node = RestNode(node_config=node_config)

        # Register run_experiment as an action
        self._register_experiment_action()

    def _register_experiment_action(self) -> None:
        """Register run_experiment as a node action."""
        if self._rest_node is None:
            return

        # Create a wrapper that handles experiment lifecycle
        def wrapped_run_experiment(*args: Any, **kwargs: Any) -> Any:
            """Wrapper that adds experiment lifecycle management."""
            with self.manage_experiment():
                return self.run_experiment(*args, **kwargs)

        # Copy the original function's signature for action discovery
        wrapped_run_experiment.__doc__ = self.run_experiment.__doc__
        wrapped_run_experiment.__annotations__ = getattr(
            self.run_experiment, "__annotations__", {}
        )

        self._rest_node._add_action(
            func=wrapped_run_experiment,
            action_name="run_experiment",
            description=(
                self.run_experiment.__doc__.split("\n")[0]
                if self.run_experiment.__doc__
                else "Run the experiment"
            ),
            blocking=False,
        )

    def start_server(self) -> None:
        """Start the REST server for this experiment.

        The server exposes run_experiment as an action that can be
        called by the workcell manager or any HTTP client.

        The server runs until interrupted (Ctrl+C) or shut down.
        """
        if self._rest_node is None:
            raise RuntimeError("REST node not initialized")

        # Log startup info
        self.logger.info(
            "Starting experiment node server",
            host=self.config.server_host,
            port=self.config.server_port,
            experiment_name=(
                self.experiment_design.experiment_name
                if self.experiment_design
                else "Unknown"
            ),
        )

        self._rest_node.start_node()

    def run(self) -> None:
        """Alias for start_server() for consistency with other modalities."""
        self.start_server()

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:
        """Override this method with your experiment logic.

        This method is exposed as a REST API action. When called via
        the API, the experiment lifecycle is automatically managed:
        - Experiment is started before run_experiment executes
        - Experiment is ended after run_experiment completes
        - Exceptions are logged and experiment marked as failed

        The method signature (parameters) will be exposed in the API,
        so clients can pass parameters as JSON in the request body.

        Args:
            *args: Positional arguments from API request.
            **kwargs: Keyword arguments from API request.

        Returns:
            Experiment results (will be serialized to JSON in response).

        Example:
            ```python
            def run_experiment(
                self,
                sample_id: str,
                temperature: float = 25.0,
                cycles: int = 1
            ) -> dict:
                results = []
                for i in range(cycles):
                    result = self.workcell_client.run_workflow(
                        "process_sample",
                        parameters={
                            "sample_id": sample_id,
                            "temperature": temperature,
                            "cycle": i
                        }
                    )
                    results.append(result)
                return {
                    "sample_id": sample_id,
                    "cycles_completed": cycles,
                    "results": results
                }
            ```
        """
        raise NotImplementedError(
            "Subclasses must implement run_experiment() with experiment logic"
        )
