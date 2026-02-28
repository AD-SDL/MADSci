Module madsci.experiment_application.experiment_node
====================================================
ExperimentNode modality for server-mode experiments.

This module provides the ExperimentNode class, which runs experiments
as REST API servers that can be controlled by the workcell manager.

Classes
-------

`ExperimentNode(experiment_design: madsci.common.types.experiment_types.ExperimentDesign | str | pathlib.Path | None = None, experiment: madsci.common.types.experiment_types.Experiment | None = None, config: madsci.experiment_application.experiment_node.ExperimentNodeConfig | None = None, lab_server_url: str | pydantic.networks.AnyUrl | None = None, **kwargs: Any)`
:   Experiment modality that runs as a REST node.

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

    Initialize the experiment node.

    Args:
        experiment_design: Design for new experiments.
        experiment: Existing experiment to continue.
        config: Configuration settings.
        lab_server_url: Override for lab server URL.
        **kwargs: Additional configuration overrides.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBase
    * madsci.client.client_mixin.MadsciClientMixin

    ### Methods

    `run(self) ‑> None`
    :   Alias for start_server() for consistency with other modalities.

    `run_experiment(self, *args: Any, **kwargs: Any) ‑> Any`
    :   Override this method with your experiment logic.

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

    `start_server(self) ‑> None`
    :   Start the REST server for this experiment.

        The server exposes run_experiment as an action that can be
        called by the workcell manager or any HTTP client.

        The server runs until interrupted (Ctrl+C) or shut down.

`ExperimentNodeConfig(**kwargs: Any)`
:   Configuration for node-based experiments (server mode).

    Extends ExperimentBaseConfig with REST server settings.

    Initialize settings with walk-up file discovery.

    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.experiment_application.experiment_base.ExperimentBaseConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `cors_enabled: bool`
    :

    `cors_origins: list[str]`
    :

    `node_name: str | None`
    :

    `server_host: str`
    :

    `server_port: int`
    :
