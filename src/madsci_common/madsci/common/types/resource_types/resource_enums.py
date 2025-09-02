"""Enums for MADSci Resource Types."""

from enum import Enum


class AssetTypeEnum(str, Enum):
    """Type for a MADSci Asset."""

    container = "container"
    asset = "asset"


class ConsumableTypeEnum(str, Enum):
    """Type for a MADSci Consumable."""

    consumable = "consumable"
    discrete_consumable = "discrete_consumable"
    continuous_consumable = "continuous_consumable"


class ContainerTypeEnum(str, Enum):
    """Type for a MADSci Container."""

    container = "container"
    slot = "slot"
    stack = "stack"
    queue = "queue"
    collection = "collection"
    row = "row"
    grid = "grid"
    voxel_grid = "voxel_grid"
    pool = "pool"


class ResourceTypeEnum(str, Enum):
    """Enum for all resource base types."""

    """Resource Base Types"""
    resource = "resource"

    """Asset Resource Base Types"""
    asset = "asset"
    container = "container"

    """Consumable Resource Base Types"""
    consumable = "consumable"
    discrete_consumable = "discrete_consumable"
    continuous_consumable = "continuous_consumable"

    """Container Resource Base Types"""
    slot = "slot"
    stack = "stack"
    queue = "queue"
    collection = "collection"
    row = "row"
    grid = "grid"
    voxel_grid = "voxel_grid"
    pool = "pool"
