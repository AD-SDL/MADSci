Module madsci.client.experiment_client
======================================
Client for the MADSci Experiment Manager.

Classes
-------

`ExperimentClient(experiment_server_url: str | pydantic.networks.AnyUrl | None = None, config: madsci.common.types.client_types.ExperimentClientConfig | None = None)`
:   Client for the MADSci Experiment Manager.

    Create a new Experiment Client.

    Args:
        experiment_server_url: The URL of the experiment server. If not provided, will use the URL from the current MADSci context.
        config: Client configuration for retry and timeout settings. If not provided, uses default ExperimentClientConfig.

    ### Class variables

    `experiment_server_url: pydantic.networks.AnyUrl`
    :

    ### Methods

    `cancel_experiment(self, experiment_id: str | ulid.ULID, timeout: float | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Cancel an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `continue_experiment(self, experiment_id: str | ulid.ULID, timeout: float | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Continue an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `end_experiment(self, experiment_id: str | ulid.ULID, status: madsci.common.types.experiment_types.ExperimentStatus | None = None, timeout: float | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   End an experiment by ID. Optionally, set the status.

        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_campaign(self, campaign_id: str, timeout: float | None = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Get an experimental campaign by ID.

        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_experiment(self, experiment_id: str | ulid.ULID, timeout: float | None = None) ‑> dict`
    :   Get an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_experiments(self, number: int = 10, timeout: float | None = None) ‑> list[madsci.common.types.experiment_types.Experiment]`
    :   Get a list of the latest experiments.

        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `pause_experiment(self, experiment_id: str | ulid.ULID, timeout: float | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Pause an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `register_campaign(self, campaign: madsci.common.types.experiment_types.ExperimentalCampaign, timeout: float | None = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Register a new experimental campaign.

        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `start_experiment(self, experiment_design: madsci.common.types.experiment_types.ExperimentDesign, run_name: str | None = None, run_description: str | None = None, timeout: float | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start an experiment based on an ExperimentDesign.

        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
