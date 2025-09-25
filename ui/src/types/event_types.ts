/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

/**
 * The type of the event.
 */
export type EventType =
  | "unknown"
  | "log"
  | "log_debug"
  | "info"
  | "log_warning"
  | "log_error"
  | "log_critical"
  | "test"
  | "lab_create"
  | "lab_start"
  | "lab_stop"
  | "node_create"
  | "node_start"
  | "node_stop"
  | "node_config_update"
  | "node_status_update"
  | "node_error"
  | "workcell_create"
  | "workcell_start"
  | "workcell_stop"
  | "workcell_config_update"
  | "workcell_status_update"
  | "workflow_create"
  | "workflow_start"
  | "workflow_complete"
  | "workflow_abort"
  | "experiment_create"
  | "experiment_start"
  | "experiment_complete"
  | "experiment_failed"
  | "experiment_stop"
  | "experiment_pause"
  | "experiment_continued"
  | "campaign_create"
  | "campaign_start"
  | "campaign_complete"
  | "campaign_abort"
  | "action_status_change";
/**
 * The log level of the event. Defaults to NOTSET. See https://docs.python.org/3/library/logging.html#logging-levels
 */
export type EventLogLevel = 0 | 10 | 20 | 30 | 40 | 50;
/**
 * The log level of an event.
 */
export type EventLogLevel1 = 0 | 10 | 20 | 30 | 40 | 50;
/**
 * The log level of an event.
 */
export type EventLogLevel2 = 0 | 10 | 20 | 30 | 40 | 50;
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
 * Configuration for sending emails.
 */
export interface EmailAlertsConfig {
  /**
   * The SMTP server address used for sending emails.
   */
  smtp_server?: string;
  /**
   * The port number used by the SMTP server.
   */
  smtp_port?: number;
  /**
   * The username for authenticating with the SMTP server.
   */
  smtp_username?: string | null;
  /**
   * The password for authenticating with the SMTP server.
   */
  smtp_password?: string | null;
  /**
   * Whether to use TLS for the SMTP connection.
   */
  use_tls?: boolean;
  /**
   * The default sender email address.
   */
  sender?: string;
  /**
   * The default importance level of the email. Options are: High, Normal, Low.
   */
  default_importance?: string;
  /**
   * The default email addresses to send alerts to.
   */
  email_addresses?: string[];
}
/**
 * An event in the MADSci system.
 */
export interface Event {
  /**
   * The ID of the event.
   */
  _id?: string;
  event_type?: EventType;
  log_level?: EventLogLevel;
  /**
   * Forces firing an alert about this event. Defaults to False.
   */
  alert?: boolean;
  /**
   * The timestamp of the event.
   */
  event_timestamp?: string;
  source?: OwnershipInfo;
  /**
   * The data associated with the event.
   */
  event_data?: {
    [k: string]: unknown;
  };
}
/**
 * Information about the source of the event.
 */
export interface OwnershipInfo {
  [k: string]: unknown;
}
/**
 * Configuration for an Event Client.
 */
export interface EventClientConfig {
  /**
   * The name of the event client.
   */
  name?: string | null;
  /**
   * The URL of the event server.
   */
  event_server_url?: string | null;
  /**
   * The log level of the event client.
   */
  log_level?: number | EventLogLevel1;
  source?: OwnershipInfo1;
  /**
   * The directory to store logs in.
   */
  log_dir?: string;
}
/**
 * Information about the source of the event client.
 */
export interface OwnershipInfo1 {
  [k: string]: unknown;
}
/**
 * Definition for a Squid Event Manager
 */
export interface EventManagerDefinition {
  /**
   * The name of this manager instance.
   */
  name?: string;
  /**
   * A description of the manager.
   */
  description?: string | null;
  /**
   * The type of the event manager
   */
  manager_type?: "event_manager";
  /**
   * The ID of the event manager.
   */
  event_manager_id?: string;
  [k: string]: unknown;
}
/**
 * Handles settings and configuration for the Event Manager.
 */
export interface EventManagerSettings {
  /**
   * The URL of the Event Manager server.
   */
  event_server_url?: string | null;
  /**
   * Path to the event manager definition file to use.
   */
  event_manager_definition?: string;
  /**
   * The URL of the database used by the Event Manager.
   */
  db_url?: string;
  /**
   * The name of the MongoDB collection where events are stored.
   */
  collection_name?: string;
  alert_level?: EventLogLevel2;
  /**
   * The configuration for sending email alerts.
   */
  email_alerts?: EmailAlertsConfig | null;
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
export interface OwnershipInfo2 {
  [k: string]: unknown;
}
