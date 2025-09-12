/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

/**
 * The status of the experiment.
 */
export type ExperimentStatus = "in_progress" | "paused" | "completed" | "failed" | "cancelled" | "unknown";
/**
 * The check (is_greater_than, is_less_than or is_equal_to etc.) to evaluate the field by
 */
export type OperatorTypeEnum =
  | "is_greater_than"
  | "is_less_than"
  | "is_equal_to"
  | "is_greater_than_or_equal_to"
  | "is_less_than_or_equal_to";
/**
 * The check (is_greater_than, is_less_than or is_equal_to etc.) to evaluate the field by
 */
export type OperatorTypeEnum1 =
  | "is_greater_than"
  | "is_less_than"
  | "is_equal_to"
  | "is_greater_than_or_equal_to"
  | "is_less_than_or_equal_to";
/**
 * The type of the manager, used by other components or managers to find matching managers.
 */
export type ManagerType =
  | "workcell_manager"
  | "resource_manager"
  | "event_manager"
  | "auth_manager"
  | "data_manager"
  | "transfer_manager"
  | "experiment_manager"
  | "lab_manager";

/**
 * A MADSci experiment.
 */
export interface Experiment {
  /**
   * The ID of the experiment.
   */
  _id?: string;
  status?: ExperimentStatus;
  /**
   * The design of the experiment.
   */
  experiment_design?: ExperimentDesign | null;
  ownership_info?: OwnershipInfo1;
  /**
   * A name for this specific experiment run.
   */
  run_name?: string | null;
  /**
   * A description of the experiment run.
   */
  run_description?: string | null;
  /**
   * The time the experiment was started.
   */
  started_at?: string | null;
  /**
   * The time the experiment was ended.
   */
  ended_at?: string | null;
}
/**
 * A design for a MADSci experiment.
 */
export interface ExperimentDesign {
  /**
   * The name of the experiment.
   */
  experiment_name: string;
  /**
   * A description of the experiment.
   */
  experiment_description?: string | null;
  /**
   * The starting layout of resources required for the experiment.
   */
  resource_conditions?: (
    | ResourceInLocationCondition
    | NoResourceInLocationCondition
    | ResourceFieldCheckCondition
    | ResourceChildFieldCheckCondition
  )[];
  ownership_info?: OwnershipInfo;
  /**
   * Information for starting the experiment in server mode
   */
  node_config?: RestNodeConfig | null;
}
/**
 * A condition that checks if a resource is present
 */
export interface ResourceInLocationCondition {
  /**
   * The type of condition to check
   */
  condition_type?: "resource_present";
  /**
   * Name of the Condition
   */
  condition_name?: string;
  /**
   * The ID of the location to check for a resource in
   */
  location_id?: string | null;
  /**
   * The name of the location to check for a resource in
   */
  location_name?: string | null;
  /**
   * The key to check in the location's container resource
   */
  key?: string | number | [unknown, unknown] | [unknown, unknown, unknown];
  /**
   * Check that the resource in this location is of a certain class
   */
  resource_class?: string | null;
  [k: string]: unknown;
}
/**
 * A condition that checks if a resource is present
 */
export interface NoResourceInLocationCondition {
  /**
   * The type of condition to check
   */
  condition_type?: "no_resource_present";
  /**
   * Name of the Condition
   */
  condition_name?: string;
  /**
   * The ID of the location to check for a resource in
   */
  location_id?: string | null;
  /**
   * The name of the location to check for a resource in
   */
  location_name: string;
  /**
   * The key to check in the location's container resource
   */
  key?: string | number | [unknown, unknown] | [unknown, unknown, unknown];
  [k: string]: unknown;
}
/**
 * A condition that checks if a resource is present
 */
export interface ResourceFieldCheckCondition {
  /**
   * The type of condition to check
   */
  condition_type?: "resource_field_check";
  /**
   * Name of the Condition
   */
  condition_name?: string;
  /**
   * The id of the resource to check a quality of
   */
  resource_id?: string | null;
  /**
   * The name of the resource to check a quality of
   */
  resource_name?: string | null;
  /**
   * The field to evaluate against the operator
   */
  field: string;
  operator: OperatorTypeEnum;
  /**
   * the target value for the field
   */
  target_value: {
    [k: string]: unknown;
  };
  [k: string]: unknown;
}
/**
 * A condition that checks if a resource is present
 */
export interface ResourceChildFieldCheckCondition {
  /**
   * The type of condition to check
   */
  condition_type?: "resource_child_field_check";
  /**
   * Name of the Condition
   */
  condition_name?: string;
  /**
   * The id of the resource to check a quality of
   */
  resource_id?: string | null;
  /**
   * The name of the resource to check a quality of
   */
  resource_name?: string | null;
  /**
   * The field to evaluate against the operator
   */
  field: string;
  operator: OperatorTypeEnum1;
  /**
   * The key to check in the container resource
   */
  key?: string | number | [unknown, unknown] | [unknown, unknown, unknown];
  /**
   * the target value for the field
   */
  target_value: {
    [k: string]: unknown;
  };
  [k: string]: unknown;
}
/**
 * Information about the users, campaigns, etc. that this design is owned by.
 */
export interface OwnershipInfo {
  [k: string]: unknown;
}
/**
 * Default Configuration for a MADSci Node that communicates over REST.
 */
export interface RestNodeConfig {
  /**
   * Path to the node definition file to use. If set, the node will load the definition from this file on startup. Otherwise, a default configuration will be created.
   */
  node_definition?: string | null;
  /**
   * Path to export the generated node info file. If not set, will use the node name and the node_definition's path.
   */
  node_info_path?: string | null;
  /**
   * Whether to update the node definition and info files on startup. If set to False, the node will not update the files even if they are out of date.
   */
  update_node_files?: boolean;
  /**
   * The interval in seconds at which the node should update its status.
   */
  status_update_interval?: number | null;
  /**
   * The interval in seconds at which the node should update its state.
   */
  state_update_interval?: number | null;
  /**
   * Server for the Lab URL
   */
  lab_server_url?: string | null;
  /**
   * The URL used to communicate with the node. This is the base URL for the REST API.
   */
  node_url?: string;
  /**
   * Configuration for the Uvicorn server that runs the REST API.
   */
  uvicorn_kwargs?: {
    [k: string]: unknown;
  };
}
/**
 * Information about the ownership of the experiment.
 */
export interface OwnershipInfo1 {
  [k: string]: unknown;
}
/**
 * Definition for an Experiment Manager.
 */
export interface ExperimentManagerDefinition {
  /**
   * The name of this experiment manager instance.
   */
  name?: string;
  /**
   * A description of the manager.
   */
  description?: string | null;
  /**
   * The type of the event manager
   */
  manager_type?: "experiment_manager";
  /**
   * The ID of the experiment manager.
   */
  experiment_manager_id?: string;
  [k: string]: unknown;
}
/**
 * Settings for the MADSci Experiment Manager.
 */
export interface ExperimentManagerSettings {
  /**
   * The URL of the experiment manager server.
   */
  experiment_server_url?: string;
  /**
   * Path to the experiment manager definition file to use.
   */
  experiment_manager_definition?: string;
  /**
   * The URL of the database for the experiment manager.
   */
  db_url?: string;
}
/**
 * Experiment Run Registration request body
 */
export interface ExperimentRegistration {
  experiment_design: ExperimentDesign;
  run_name?: string | null;
  run_description?: string | null;
}
/**
 * A campaign consisting of one or more related experiments.
 */
export interface ExperimentalCampaign {
  /**
   * The ID of the campaign.
   */
  campaign_id?: string;
  /**
   * The name of the campaign.
   */
  campaign_name: string;
  /**
   * A description of the campaign.
   */
  campaign_description?: string | null;
  /**
   * The IDs of the experiments in the campaign. (Convenience field)
   */
  experiment_ids: string[] | null;
  ownership_info?: OwnershipInfo2;
  /**
   * The time the campaign was registered.
   */
  created_at?: string;
  /**
   * The time the campaign was ended.
   */
  ended_at?: string | null;
}
/**
 * Information about the ownership of the campaign.
 */
export interface OwnershipInfo2 {
  [k: string]: unknown;
}
/**
 * Parent class for all MADSci data models.
 */
export interface MadsciBaseModel {}
/**
 * Base class for all MADSci settings.
 */
export interface MadsciBaseSettings {}
/**
 * Definition for a MADSci Manager.
 */
export interface ManagerDefinition {
  /**
   * The name of this manager instance.
   */
  name: string;
  /**
   * A description of the manager.
   */
  description?: string | null;
  manager_type: ManagerType;
  [k: string]: unknown;
}
export interface OwnershipInfo3 {
  [k: string]: unknown;
}
