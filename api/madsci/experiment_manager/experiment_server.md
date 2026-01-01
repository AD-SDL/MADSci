Module madsci.experiment_manager.experiment_server
==================================================
Experiment Manager implementation using the new AbstractManagerBase class.

Classes
-------

`ExperimentManager(settings: madsci.common.types.experiment_types.ExperimentManagerSettings | None = None, definition: madsci.common.types.experiment_types.ExperimentManagerDefinition | None = None, db_client: pymongo.synchronous.mongo_client.MongoClient | None = None, db_connection: pymongo.synchronous.database.Database | None = None, **kwargs: Any)`
:   Experiment Manager REST Server.

    Initialize the Experiment Manager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition for an Experiment Manager.

    `ENABLE_ROOT_DEFINITION_ENDPOINT: bool`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the MADSci Experiment Manager.

    ### Methods

    `cancel_experiment(self, experiment_id: str) ‑> madsci.common.types.experiment_types.Experiment`
    :   Cancel an experiment by ID.

    `continue_experiment(self, experiment_id: str) ‑> madsci.common.types.experiment_types.Experiment`
    :   Continue an experiment by ID.

    `end_experiment(self, experiment_id: str) ‑> madsci.common.types.experiment_types.Experiment`
    :   End an experiment by ID.

    `fail_experiment(self, experiment_id: str) ‑> madsci.common.types.experiment_types.Experiment`
    :   Fail an experiment by ID.

    `get_experiment(self, experiment_id: str) ‑> madsci.common.types.experiment_types.Experiment`
    :   Get an experiment by ID.

    `get_experiments(self, number: int = 10) ‑> list[madsci.common.types.experiment_types.Experiment]`
    :   Get the latest experiments.

    `get_health(self) ‑> madsci.common.types.experiment_types.ExperimentManagerHealth`
    :   Get the health status of the Experiment Manager.

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

    `pause_experiment(self, experiment_id: str) ‑> madsci.common.types.experiment_types.Experiment`
    :   Pause an experiment by ID.

    `start_experiment(self, experiment_request: madsci.common.types.experiment_types.ExperimentRegistration) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start a new experiment.
