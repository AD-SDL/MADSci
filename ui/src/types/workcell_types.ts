/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

/**
 * The type of thing this node provides an interface for.
 */
export type NodeType =
  | "device"
  | "compute"
  | "resource_manager"
  | "event_manager"
  | "workcell_manager"
  | "data_manager"
  | "transfer_manager";
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
}
/**
 * A location in the lab.
 */
export interface Location {
  /**
   * The name of the location.
   */
  location_name: string;
  /**
   * The ID of the location.
   */
  location_id?: string;
  /**
   * A description of the location.
   */
  description?: string | null;
  /**
   * A dictionary of different representations of the location. Allows creating an association between a specific key (like a node name or id) and a relevant representation of the location (like joint angles, a specific actuator, etc).
   */
  lookup?: {
    [k: string]: unknown;
  };
  /**
   * Definition of the Resource to be associated with this location (if any) on location initialization.
   */
  resource_definition?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * The reservation for the location.
   */
  reservation?: LocationReservation | null;
  /**
   * The ID of an existing Resource associated with the location, if any.
   */
  resource_id?: string | null;
}
/**
 * Definition for a MADSci Resource.
 */
export interface ResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the resource.
   */
  base_type?: "resource";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo {
  [k: string]: unknown;
}
/**
 * Definition for a MADSci Custom Resource Attribute.
 */
export interface CustomResourceAttributeDefinition {
  /**
   * The name of the attribute.
   */
  attribute_name: string;
  /**
   * A description of the attribute.
   */
  attribute_description?: string | null;
  /**
   * Whether the attribute is optional.
   */
  optional?: boolean;
  /**
   * The default value of the attribute.
   */
  default_value?: {
    [k: string]: unknown;
  };
  [k: string]: unknown;
}
/**
 * Definition for an asset resource.
 */
export interface AssetResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the asset.
   */
  base_type?: "asset";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo1;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo1 {
  [k: string]: unknown;
}
/**
 * Definition for a container resource.
 */
export interface ContainerResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the container.
   */
  base_type?: "container";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo2;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the container. If None, use the type's default_children.
   */
  default_children?:
    | ResourceDefinition[]
    | {
        [k: string]: ResourceDefinition;
      }
    | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo2 {
  [k: string]: unknown;
}
/**
 * Definition for a collection resource. Collections are used for resources that have a number of children, each with a unique key, which can be randomly accessed.
 */
export interface CollectionResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the collection.
   */
  base_type?: "collection";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo3;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the collection. If None, use the type's default_children.
   */
  default_children?:
    | ResourceDefinition[]
    | {
        [k: string]: ResourceDefinition;
      }
    | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * The keys for the collection. Can be an integer (converted to 1-based range) or explicit list.
   */
  keys?: number | string[] | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo3 {
  [k: string]: unknown;
}
/**
 * Definition for a row resource. Rows are 1D collections of resources. They are treated as single collections (i.e. Collection[Resource]).
 */
export interface RowResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the row.
   */
  base_type?: "row";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo4;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the collection. If None, use the type's default_children.
   */
  default_children?: {
    [k: string]: ResourceDefinition;
  } | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * Whether to populate every empty key with a default child
   */
  fill?: boolean;
  /**
   * The number of columns in the row.
   */
  columns: number;
  /**
   * Whether the numeric index of the object start at 0 or 1
   */
  is_one_indexed?: boolean;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo4 {
  [k: string]: unknown;
}
/**
 * Definition for a grid resource. Grids are 2D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Resource]]).
 */
export interface GridResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the grid.
   */
  base_type?: "grid";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo5;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the collection. If None, use the type's default_children.
   */
  default_children?: {
    [k: string]: {
      [k: string]: ResourceDefinition;
    };
  } | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * Whether to populate every empty key with a default child
   */
  fill?: boolean;
  /**
   * The number of columns in the row.
   */
  columns: number;
  /**
   * Whether the numeric index of the object start at 0 or 1
   */
  is_one_indexed?: boolean;
  /**
   * The number of rows in the grid. If None, use the type's rows.
   */
  rows?: number;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo5 {
  [k: string]: unknown;
}
/**
 * Definition for a voxel grid resource. Voxel grids are 3D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Collection[Resource]]]).
 */
export interface VoxelGridResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the voxel grid.
   */
  base_type?: "voxel_grid";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo6;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the collection. If None, use the type's default_children.
   */
  default_children?: {
    [k: string]: {
      [k: string]: {
        [k: string]: ResourceDefinition;
      };
    };
  } | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * Whether to populate every empty key with a default child
   */
  fill?: boolean;
  /**
   * The number of columns in the row.
   */
  columns: number;
  /**
   * Whether the numeric index of the object start at 0 or 1
   */
  is_one_indexed?: boolean;
  /**
   * The number of rows in the grid. If None, use the type's rows.
   */
  rows?: number;
  /**
   * The number of layers in the voxel grid. If None, use the type's layers.
   */
  layers: number;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo6 {
  [k: string]: unknown;
}
/**
 * Definition for a stack resource.
 */
export interface StackResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the stack.
   */
  base_type?: "stack";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo7;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the container. If None, use the type's default_children.
   */
  default_children?:
    | ResourceDefinition[]
    | {
        [k: string]: ResourceDefinition;
      }
    | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * The number of children to create by default. If None, use the type's default_child_quantity.
   */
  default_child_quantity?: number | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo7 {
  [k: string]: unknown;
}
/**
 * Definition for a queue resource.
 */
export interface QueueResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the queue.
   */
  base_type?: "queue";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo8;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the container. If None, uses the type's default_capacity.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the container. If None, use the type's default_children.
   */
  default_children?:
    | ResourceDefinition[]
    | {
        [k: string]: ResourceDefinition;
      }
    | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * The number of children to create by default. If None, use the type's default_child_quantity.
   */
  default_child_quantity?: number | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo8 {
  [k: string]: unknown;
}
/**
 * Definition for a pool resource. Pool resources are collections of consumables with no structure (used for wells, reservoirs, etc.).
 */
export interface PoolResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the pool.
   */
  base_type?: "pool";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo9;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The default capacity of the pool as a whole.
   */
  capacity?: number | null;
  /**
   * The default children to create when initializing the container. If None, use the type's default_children.
   */
  default_children?:
    | ResourceDefinition[]
    | {
        [k: string]: ResourceDefinition;
      }
    | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * The unit used to measure the quantity of the pool.
   */
  unit?: string | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo9 {
  [k: string]: unknown;
}
/**
 * Definition for a slot resource.
 */
export interface SlotResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the slot.
   */
  base_type?: "slot";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo10;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The capacity of the slot.
   */
  capacity?: 1;
  /**
   * The default children to create when initializing the container. If None, use the type's default_children.
   */
  default_children?:
    | ResourceDefinition[]
    | {
        [k: string]: ResourceDefinition;
      }
    | null;
  /**
   * Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.
   */
  default_child_template?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
  /**
   * The number of children to create by default. If None, use the type's default_child_quantity.
   */
  default_child_quantity?: number | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo10 {
  [k: string]: unknown;
}
/**
 * Definition for a consumable resource.
 */
export interface ConsumableResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the consumable.
   */
  base_type?: "consumable";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo11;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The unit used to measure the quantity of the consumable.
   */
  unit?: string | null;
  /**
   * The initial quantity of the consumable.
   */
  quantity?: number;
  /**
   * The initial capacity of the consumable.
   */
  capacity?: number | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo11 {
  [k: string]: unknown;
}
/**
 * Definition for a discrete consumable resource.
 */
export interface DiscreteConsumableResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the consumable.
   */
  base_type?: "discrete_consumable";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo12;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The unit used to measure the quantity of the consumable.
   */
  unit?: string | null;
  /**
   * The initial quantity of the consumable.
   */
  quantity?: number;
  /**
   * The initial capacity of the consumable.
   */
  capacity?: number | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo12 {
  [k: string]: unknown;
}
/**
 * Definition for a continuous consumable resource.
 */
export interface ContinuousConsumableResourceDefinition {
  /**
   * The name of the resource.
   */
  resource_name?: string;
  /**
   * A prefix to append the key of the object to for machine instanciated resources
   */
  resource_name_prefix?: string | null;
  /**
   * The class of the resource. Must match a class defined in the resource manager.
   */
  resource_class?: string;
  /**
   * The base type of the continuous consumable.
   */
  base_type?: "continuous_consumable";
  /**
   * A description of the resource.
   */
  resource_description?: string | null;
  owner?: OwnershipInfo13;
  /**
   * Custom attributes used by resources of this type.
   */
  custom_attributes?: CustomResourceAttributeDefinition[] | null;
  /**
   * The unit used to measure the quantity of the consumable.
   */
  unit?: string | null;
  /**
   * The initial quantity of the consumable.
   */
  quantity?: number;
  /**
   * The initial capacity of the consumable.
   */
  capacity?: number | null;
  [k: string]: unknown;
}
/**
 * The owner of this resource
 */
export interface OwnershipInfo13 {
  [k: string]: unknown;
}
/**
 * Reservation of a MADSci Location.
 */
export interface LocationReservation {
  owned_by: OwnershipInfo14;
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
export interface OwnershipInfo14 {
  [k: string]: unknown;
}
/**
 * The Definition of a Location in a setup.
 */
export interface LocationDefinition {
  /**
   * The name of the location.
   */
  location_name: string;
  /**
   * The ID of the location.
   */
  location_id?: string;
  /**
   * A description of the location.
   */
  description?: string | null;
  /**
   * A dictionary of different representations of the location. Allows creating an association between a specific key (like a node name or id) and a relevant representation of the location (like joint angles, a specific actuator, etc).
   */
  lookup?: {
    [k: string]: unknown;
  };
  /**
   * Definition of the Resource to be associated with this location (if any) on location initialization.
   */
  resource_definition?:
    | (
        | ResourceDefinition
        | AssetResourceDefinition
        | ContainerResourceDefinition
        | CollectionResourceDefinition
        | RowResourceDefinition
        | GridResourceDefinition
        | VoxelGridResourceDefinition
        | StackResourceDefinition
        | QueueResourceDefinition
        | PoolResourceDefinition
        | SlotResourceDefinition
        | ConsumableResourceDefinition
        | DiscreteConsumableResourceDefinition
        | ContinuousConsumableResourceDefinition
      )
    | null;
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
 * A runtime representation of a MADSci Node used in a Workcell.
 */
export interface Node {
  /**
   * The URL used to communicate with the node.
   */
  node_url: string;
  /**
   * The status of the node. Set to None if the node does not support status reporting or the status is unknown (e.g. if it hasn't reported/responded to status requests).
   */
  status?: NodeStatus | null;
  /**
   * Information about the node, provided by the node itself.
   */
  info?: NodeInfo | null;
  /**
   * Detailed nodes specific state information
   */
  state?: {
    [k: string]: unknown;
  } | null;
  /**
   * Information about the current reservation of the node, if any
   */
  reservation?: NodeReservation | null;
}
/**
 * Status of a MADSci Node.
 */
export interface NodeStatus {
  /**
   * Whether the node is currently at capacity, i.e. running the maximum number of actions allowed.
   */
  busy?: boolean;
  /**
   * The IDs of the actions that the node is currently running.
   */
  running_actions?: string[];
  /**
   * Whether the node is paused.
   */
  paused?: boolean;
  /**
   * Whether the node is locked, preventing it from accepting any actions.
   */
  locked?: boolean;
  /**
   * Whether the node has been stopped (e.g. due to a safety stop).
   */
  stopped?: boolean;
  /**
   * Whether the node is in an errored state.
   */
  errored?: boolean;
  /**
   * A list of errors that the node has encountered.
   */
  errors?: Error[];
  /**
   * Whether the node is currently initializing.
   */
  initializing?: boolean;
  /**
   * Set of configuration parameters that the node is waiting for.
   */
  waiting_for_config?: string[];
  /**
   * The current configuration values of the node.
   */
  config_values?: {
    [k: string]: unknown;
  };
  /**
   * Whether the node is ready to accept actions.
   */
  ready: boolean;
  /**
   * A description of the node's status.
   */
  description: string;
  [k: string]: unknown;
}
/**
 * Information about a MADSci Node.
 */
export interface NodeInfo {
  /**
   * The name of the node.
   */
  node_name: string;
  /**
   * The ID of the node.
   */
  node_id?: string;
  /**
   * A description of the node.
   */
  node_description?: string | null;
  node_type?: NodeType;
  /**
   * The name of the node module.
   */
  module_name: string;
  /**
   * The version of the node module.
   */
  module_version?: string;
  /**
   * Explicitly override the capabilities of the node.
   */
  capabilities?: NodeCapabilities | null;
  /**
   * The URL used to communicate with the node.
   */
  node_url?: string | null;
  /**
   * The actions that the node supports.
   */
  actions?: {
    [k: string]: ActionDefinition;
  };
  config?: unknown;
  /**
   * JSON Schema for the configuration of the node.
   */
  config_schema?: {
    [k: string]: unknown;
  } | null;
  [k: string]: unknown;
}
export interface NodeCapabilities {
  [k: string]: unknown;
}
/**
 * Definition of an action.
 */
export interface ActionDefinition {
  /**
   * The name of the action.
   */
  name: string;
  /**
   * A description of the action.
   */
  description: string;
  /**
   * The arguments of the action.
   */
  args?:
    | {
        [k: string]: ArgumentDefinition;
      }
    | ArgumentDefinition[];
  /**
   * The location arguments of the action.
   */
  locations?:
    | {
        [k: string]: LocationArgumentDefinition;
      }
    | LocationArgumentDefinition[];
  /**
   * The file arguments of the action.
   */
  files?:
    | {
        [k: string]: FileArgumentDefinition;
      }
    | FileArgumentDefinition[];
  /**
   * The results of the action.
   */
  results?:
    | {
        [k: string]: ActionResultDefinition;
      }
    | ActionResultDefinition[];
  /**
   * Whether the action is blocking.
   */
  blocking?: boolean;
  /**
   * Whether the action is asynchronous, and will return a 'running' status immediately rather than waiting for the action to complete before returning. This should be used for long-running actions (e.g. actions that take more than a few seconds to complete).
   */
  asynchronous?: boolean;
  [k: string]: unknown;
}
/**
 * Defines an argument for a node action
 */
export interface ArgumentDefinition {
  /**
   * The name of the argument.
   */
  name: string;
  /**
   * A description of the argument.
   */
  description: string;
  /**
   * Any type information about the argument
   */
  argument_type: string;
  /**
   * Whether the argument is required.
   */
  required: boolean;
  default?: unknown;
  [k: string]: unknown;
}
/**
 * Location Argument Definition for use in NodeInfo
 */
export interface LocationArgumentDefinition {
  /**
   * The name of the argument.
   */
  name: string;
  /**
   * A description of the argument.
   */
  description: string;
  /**
   * The type of the location argument.
   */
  argument_type?: "location";
  /**
   * Whether the argument is required.
   */
  required: boolean;
  default?: unknown;
  [k: string]: unknown;
}
/**
 * Defines a file for a node action
 */
export interface FileArgumentDefinition {
  /**
   * The name of the argument.
   */
  name: string;
  /**
   * A description of the argument.
   */
  description: string;
  /**
   * The type of the file argument.
   */
  argument_type?: "file";
  /**
   * Whether the argument is required.
   */
  required: boolean;
  default?: unknown;
  [k: string]: unknown;
}
/**
 * Defines a result for a node action
 */
export interface ActionResultDefinition {
  /**
   * The label of the result.
   */
  result_label: string;
  /**
   * A description of the result.
   */
  description?: string;
  /**
   * The type of the result.
   */
  result_type: string;
  [k: string]: unknown;
}
/**
 * Reservation of a MADSci Node.
 */
export interface NodeReservation {
  owned_by: OwnershipInfo15;
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
export interface OwnershipInfo15 {
  [k: string]: unknown;
}
/**
 * Definition of a MADSci Workcell.
 */
export interface WorkcellDefinition {
  /**
   * The name of the workcell.
   */
  workcell_name: string;
  /**
   * The type of manager
   */
  manager_type?: "workcell_manager";
  /**
   * The ID of the workcell.
   */
  workcell_id?: string;
  /**
   * A description of the workcell.
   */
  description?: string | null;
  /**
   * The URL for each node in the workcell.
   */
  nodes?: {
    [k: string]: string;
  };
  /**
   * The Locations used in the workcell.
   */
  locations?: LocationDefinition[];
  [k: string]: unknown;
}
/**
 * Settings for the MADSci Workcell Manager.
 */
export interface WorkcellManagerSettings {
  /**
   * The URL of the workcell manager server.
   */
  workcell_server_url?: string;
  /**
   * Path to the workcell definition file to use.
   */
  workcell_definition?: string;
  /**
   * Directory used to store workcell-related files in. Defaults to ~/.madsci/workcells. Workcell-related filess will be stored in a sub-folder with the workcell name.
   */
  workcells_directory?: string | null;
  /**
   * The hostname for the redis server .
   */
  redis_host?: string;
  /**
   * The port for the redis server.
   */
  redis_port?: number;
  /**
   * The password for the redis server.
   */
  redis_password?: string | null;
  /**
   * The interval at which the scheduler runs, in seconds. Must be >= node_update_interval
   */
  scheduler_update_interval?: number;
  /**
   * The interval at which the workcell queries its node's states, in seconds.Must be <= scheduler_update_interval
   */
  node_update_interval?: number;
  /**
   * How long the Workcell engine should sleep on startup
   */
  cold_start_delay?: number;
  /**
   * Scheduler module that contains a Scheduler class that inherits from AbstractScheduler to use
   */
  scheduler?: string;
  /**
   * The URL for the mongo database.
   */
  mongo_url?: string | null;
  /**
   * Number of times to retry getting an action result
   */
  get_action_result_retries?: number;
}
/**
 * Represents the live state of a MADSci workcell.
 */
export interface WorkcellState {
  status?: WorkcellStatus;
  /**
   * The queue of workflows in non-terminal states.
   */
  workflow_queue?: Workflow[];
  workcell_definition: WorkcellDefinition1;
  /**
   * The nodes in the workcell.
   */
  nodes?: {
    [k: string]: Node;
  };
  /**
   * The locations in the workcell.
   */
  locations?: {
    [k: string]: Location;
  };
}
/**
 * The status of the workcell.
 */
export interface WorkcellStatus {
  /**
   * Whether the workcell is paused.
   */
  paused?: boolean;
  /**
   * Whether the workcell is in an error state.
   */
  errored?: boolean;
  /**
   * A list of errors the workcell has encountered.
   */
  errors?: Error[];
  /**
   * Whether the workcell is initializing.
   */
  initializing?: boolean;
  /**
   * Whether the workcell is shutting down.
   */
  shutdown?: boolean;
  /**
   * Whether the workcell is locked.
   */
  locked?: boolean;
  /**
   * Whether the workcell is in a good state.
   */
  ok: boolean;
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
  ownership_info?: OwnershipInfo16;
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
  [k: string]: unknown;
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
  [k: string]: unknown;
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
  ownership_info?: OwnershipInfo16 | null;
  data_type: DataPointTypeEnum;
  _id?: string;
  data_timestamp?: string;
  [k: string]: unknown;
}
export interface OwnershipInfo16 {
  [k: string]: unknown;
}
/**
 * Scheduler information
 */
export interface SchedulerMetadata {
  ready_to_run?: boolean;
  priority?: number;
  reasons?: string[];
  [k: string]: unknown;
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
  [k: string]: unknown;
}
/**
 * The definition of the workcell.
 */
export interface WorkcellDefinition1 {
  /**
   * The name of the workcell.
   */
  workcell_name: string;
  /**
   * The type of manager
   */
  manager_type?: "workcell_manager";
  /**
   * The ID of the workcell.
   */
  workcell_id?: string;
  /**
   * A description of the workcell.
   */
  description?: string | null;
  /**
   * The URL for each node in the workcell.
   */
  nodes?: {
    [k: string]: string;
  };
  /**
   * The Locations used in the workcell.
   */
  locations?: LocationDefinition[];
  [k: string]: unknown;
}
/**
 * Represents the status of a MADSci workcell.
 */
export interface WorkcellStatus1 {
  /**
   * Whether the workcell is paused.
   */
  paused?: boolean;
  /**
   * Whether the workcell is in an error state.
   */
  errored?: boolean;
  /**
   * A list of errors the workcell has encountered.
   */
  errors?: Error[];
  /**
   * Whether the workcell is initializing.
   */
  initializing?: boolean;
  /**
   * Whether the workcell is shutting down.
   */
  shutdown?: boolean;
  /**
   * Whether the workcell is locked.
   */
  locked?: boolean;
  /**
   * Whether the workcell is in a good state.
   */
  ok: boolean;
}
