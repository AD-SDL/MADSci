Module madsci.client.experiment_client
======================================
Client for the MADSci Experiment Manager.

Classes
-------

`ExperimentClient(experiment_server_url: Optional[Union[str, AnyUrl]] = None, config: Optional[ExperimentClientConfig] = None)`
:   Client for the MADSci Experiment Manager.
    
    Create a new Experiment Client.
    
    Args:
        experiment_server_url: The URL of the experiment server. If not provided, will use the URL from the current MADSci context.
        config: Client configuration for retry and timeout settings. If not provided, uses default ExperimentClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `experiment_server_url: AnyUrl`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `async_cancel_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Cancel an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_continue_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Continue an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_end_experiment(self, experiment_id: Union[str, ULID], status: Optional[ExperimentStatus] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   End an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_campaign(self, campaign_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Get an experimental campaign by ID asynchronously.
        
        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> dict`
    :   Get an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_experiments(self, number: int = 10, timeout: Optional[float] = None) ‑> list[madsci.common.types.experiment_types.Experiment]`
    :   Get a list of the latest experiments asynchronously.
        
        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_pause_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Pause an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_register_campaign(self, campaign: ExperimentalCampaign, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Register a new experimental campaign asynchronously.
        
        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_start_experiment(self, experiment_design: ExperimentDesign, run_name: Optional[str] = None, run_description: Optional[str] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start an experiment based on an ExperimentDesign asynchronously.
        
        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `cancel_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Cancel an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `continue_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Continue an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `end_experiment(self, experiment_id: Union[str, ULID], status: Optional[ExperimentStatus] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   End an experiment by ID. Optionally, set the status.
        
        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_campaign(self, campaign_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Get an experimental campaign by ID.
        
        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> dict`
    :   Get an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_experiments(self, number: int = 10, timeout: Optional[float] = None) ‑> list[madsci.common.types.experiment_types.Experiment]`
    :   Get a list of the latest experiments.
        
        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `pause_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Pause an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `register_campaign(self, campaign: ExperimentalCampaign, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Register a new experimental campaign.
        
        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `start_experiment(self, experiment_design: ExperimentDesign, run_name: Optional[str] = None, run_description: Optional[str] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start an experiment based on an ExperimentDesign.
        
        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.