/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

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
 * The status of the step.
 */
export type ActionStatus =
  | "not_started"
  | "not_ready"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "paused"
  | "unknown";
/**
 * The status of the step.
 */
export type ActionStatus1 =
  | "not_started"
  | "not_ready"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "paused"
  | "unknown";
/**
 * Enumeration for the types of data points.
 *
 * Attributes:
 *     FILE: Represents a data point that contains a file.
 *     DATA_VALUE: Represents a data point that contains a JSON serializable value.
 */
export type DataPointTypeEnum = "file" | "data_value" | "object_storage";

/**
 * Parent class for all MADSci data models.
 */
export interface MadsciBaseModel {}
export interface OwnershipInfo {
  [k: string]: unknown;
}
/**
 * Scheduler information
 */
export interface SchedulerMetadata {
  ready_to_run?: boolean;
  priority?: number;
  reasons?: string[];
}
/**
 * A runtime representation of a step in a workflow.
 */
export interface Step {
  /**
   * The name of the step.
   */
  name: string;
  /**
   * A description of the step.
   */
  description?: string | null;
  /**
   * The action to perform in the step.
   */
  action: string;
  /**
   * Name of the node to run on
   */
  node: string;
  /**
   * Arguments for the step action.
   */
  args?: {
    [k: string]: unknown;
  };
  /**
   * Files to be used in the step. Key is the name of the file argument, value is the path to the file.
   */
  files?: {
    [k: string]: string | null;
  };
  /**
   * Locations to be used in the step. Key is the name of the argument, value is the name of the location, or a Location object.
   */
  locations?: {
    [k: string]: string | LocationArgument | null;
  };
  /**
   * Conditions for running the step
   */
  conditions?: (
    | ResourceInLocationCondition
    | NoResourceInLocationCondition
    | ResourceFieldCheckCondition
    | ResourceChildFieldCheckCondition
  )[];
  /**
   * Data labels for the results of the step. Maps from the names of the outputs of the action to the names of the data labels.
   */
  data_labels?: {
    [k: string]: string;
  };
  /**
   * The ID of the step.
   */
  step_id?: string;
  status?: ActionStatus;
  /**
   * The result of the latest action run.
   */
  result?: ActionResult | null;
  /**
   * The history of the results of the step.
   */
  history?: ActionResult[];
  start_time?: string | null;
  end_time?: string | null;
  duration?: string | null;
}
/**
 * Location Argument to be used by MADSCI nodes.
 */
export interface LocationArgument {
  location: unknown;
  resource_id?: string | null;
  location_name?: string | null;
  reservation?: LocationReservation | null;
  [k: string]: unknown;
}
/**
 * Reservation of a MADSci Location.
 */
export interface LocationReservation {
  owned_by: OwnershipInfo1;
  /**
   * When the reservation was created.
   */
  created: string;
  /**
   * When the reservation starts.
   */
  start: string;
  /**
   * When the reservation ends.
   */
  end: string;
  [k: string]: unknown;
}
/**
 * Who has ownership of the reservation.
 */
export interface OwnershipInfo1 {
  [k: string]: unknown;
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
 * Result of an action.
 */
export interface ActionResult {
  /**
   * The ID of the action.
   */
  action_id?: string;
  status: ActionStatus1;
  /**
   * An error message(s) if the step failed.
   */
  errors?: Error[];
  /**
   * The data generated by the step.
   */
  data?: {
    [k: string]: unknown;
  };
  /**
   * A dictionary of files produced by the step.
   */
  files?: {
    [k: string]: string;
  };
  /**
   * A dictionary of datapoints sent to the data manager by the step.
   */
  datapoints?: {
    [k: string]: DataPoint;
  };
  /**
   * The time the history was updated.
   */
  history_created_at?: string | null;
  [k: string]: unknown;
}
/**
 * A MADSci Error
 */
export interface Error {
  /**
   * The error message.
   */
  message?: string | null;
  /**
   * The timestamp of when the error was logged.
   */
  logged_at?: string;
  /**
   * The type of error.
   */
  error_type?: string | null;
  [k: string]: unknown;
}
/**
 * An object to contain and locate data created during experiments.
 *
 * Attributes:
 *     label: The label of this data point.
 *     step_id: The step that generated the data point.
 *     workflow_id: The workflow that generated the data point.
 *     experiment_id: The experiment that generated the data point.
 *     campaign_id: The campaign of the data point.
 *     data_type: The type of the data point, inherited from class.
 *     datapoint_id: The specific ID for this data point.
 *     data_timestamp: The time the data point was created.
 */
export interface DataPoint {
  label: string;
  ownership_info?: OwnershipInfo | null;
  data_type: DataPointTypeEnum;
  _id?: string;
  data_timestamp?: string;
  [k: string]: unknown;
}
/**
 * A definition of a step in a workflow.
 */
export interface StepDefinition {
  /**
   * The name of the step.
   */
  name: string;
  /**
   * A description of the step.
   */
  description?: string | null;
  /**
   * The action to perform in the step.
   */
  action: string;
  /**
   * Name of the node to run on
   */
  node: string;
  /**
   * Arguments for the step action.
   */
  args?: {
    [k: string]: unknown;
  };
  /**
   * Files to be used in the step. Key is the name of the file argument, value is the path to the file.
   */
  files?: {
    [k: string]: string | null;
  };
  /**
   * Locations to be used in the step. Key is the name of the argument, value is the name of the location, or a Location object.
   */
  locations?: {
    [k: string]: string | LocationArgument | null;
  };
  /**
   * Conditions for running the step
   */
  conditions?: (
    | ResourceInLocationCondition
    | NoResourceInLocationCondition
    | ResourceFieldCheckCondition
    | ResourceChildFieldCheckCondition
  )[];
  /**
   * Data labels for the results of the step. Maps from the names of the outputs of the action to the names of the data labels.
   */
  data_labels?: {
    [k: string]: string;
  };
}
/**
 * Container for a workflow run
 */
export interface Workflow {
  name: string;
  workflow_metadata?: WorkflowMetadata;
  parameters?: WorkflowParameter[] | null;
  steps?: Step[];
  scheduler_metadata?: SchedulerMetadata;
  label?: string | null;
  workflow_id?: string;
  parameter_values?: {
    [k: string]: unknown;
  };
  ownership_info?: OwnershipInfo;
  status?: WorkflowStatus;
  step_index?: number;
  simulate?: boolean;
  submitted_time?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  duration?: string | null;
  step_definitions?: StepDefinition[];
}
/**
 * Metadata container
 */
export interface WorkflowMetadata {
  author?: string | null;
  description?: string | null;
  version?: number | string;
  [k: string]: unknown;
}
/**
 * container for a workflow parameter
 */
export interface WorkflowParameter {
  name: string;
  default?: unknown;
}
/**
 * Representation of the status of a Workflow
 */
export interface WorkflowStatus {
  current_step_index?: number;
  paused?: boolean;
  completed?: boolean;
  failed?: boolean;
  cancelled?: boolean;
  running?: boolean;
  has_started?: boolean;
  /**
   * Whether or not the workflow is queued
   */
  queued: boolean;
  /**
   * Whether or not the workflow is actively being scheduled
   */
  active: boolean;
  /**
   * Whether or not the workflow is in a terminal state
   */
  terminal: boolean;
  /**
   * Whether or not the workflow has started
   */
  started: boolean;
  /**
   * Whether or not the workflow is ok (i.e. not failed or cancelled)
   */
  ok: boolean;
  /**
   * Description of the workflow's status
   */
  description: string;
}
/**
 * Grand container that pulls all info of a workflow together
 */
export interface WorkflowDefinition {
  name: string;
  workflow_metadata?: WorkflowMetadata;
  parameters?: WorkflowParameter[] | null;
  steps?: StepDefinition[];
}
