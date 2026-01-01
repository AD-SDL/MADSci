Module madsci.common.types.experiment_types
===========================================
Types for interacting with MADSci experiments and the Experiment Manager.

Classes
-------

`Experiment(**data: Any)`
:   A MADSci experiment.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `ended_at: datetime.datetime | None`
    :

    `experiment_design: madsci.common.types.experiment_types.ExperimentDesign | None`
    :

    `experiment_id: str`
    :

    `model_config`
    :

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo`
    :

    `run_description: str | None`
    :

    `run_name: str | None`
    :

    `started_at: datetime.datetime | None`
    :

    `status: madsci.common.types.experiment_types.ExperimentStatus`
    :

    ### Static methods

    `from_experiment_design(experiment_design: madsci.common.types.experiment_types.ExperimentDesign, run_name: str | None = None, run_description: str | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Create an experiment from an experiment design.

    `object_id_to_str(v: str | bson.objectid.ObjectId) ‑> str`
    :   Cast ObjectID to string.

`ExperimentDesign(**data: Any)`
:   A design for a MADSci experiment.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `experiment_description: str | None`
    :

    `experiment_name: str`
    :

    `model_config`
    :

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo`
    :

    `resource_conditions: list[madsci.common.types.condition_types.ResourceInLocationCondition | madsci.common.types.condition_types.NoResourceInLocationCondition | madsci.common.types.condition_types.ResourceFieldCheckCondition | madsci.common.types.condition_types.ResourceChildFieldCheckCondition]`
    :

    ### Methods

    `new_experiment(self, run_name: str | None = None, run_description: str | None = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Create a new experiment from this design.

`ExperimentManagerDefinition(**data: Any)`
:   Definition for an Experiment Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `manager_id: str`
    :

    `manager_type: Literal[<ManagerType.EXPERIMENT_MANAGER: 'experiment_manager'>]`
    :

    `model_config`
    :

    `name: str`
    :

    ### Instance variables

    `experiment_manager_id: str`
    :   Alias for manager_id for backward compatibility.

`ExperimentManagerHealth(**data: Any)`
:   Health status for Experiment Manager including database connectivity.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `db_connected: bool | None`
    :

    `model_config`
    :

    `total_experiments: int | None`
    :

`ExperimentManagerSettings(**values: Any)`
:   Settings for the MADSci Experiment Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `collection_name: str`
    :

    `database_name: str`
    :

    `manager_definition: str | pathlib.Path`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

`ExperimentRegistration(**data: Any)`
:   Experiment Run Registration request body

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `experiment_design: madsci.common.types.experiment_types.ExperimentDesign`
    :

    `model_config`
    :

    `run_description: str | None`
    :

    `run_name: str | None`
    :

`ExperimentStatus(*args, **kwds)`
:   Current status of an experiment run.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `CANCELLED`
    :   Experiment has been cancelled.

    `COMPLETED`
    :   Experiment run has completed.

    `FAILED`
    :   Experiment has failed.

    `IN_PROGRESS`
    :   Experiment is currently running.

    `PAUSED`
    :   Experiment is not currently running.

    `UNKNOWN`
    :   Experiment status is unknown.

`ExperimentalCampaign(**data: Any)`
:   A campaign consisting of one or more related experiments.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `campaign_description: str | None`
    :

    `campaign_id: str`
    :

    `campaign_name: str`
    :

    `created_at: datetime.datetime`
    :

    `ended_at: datetime.datetime | None`
    :

    `experiment_ids: list[str] | None`
    :

    `model_config`
    :

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo`
    :
