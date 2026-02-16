"""
ID Registry types for MADSci.

This module defines the types used by the ID Registry system for reliable,
persistent mapping between human-readable component names and their unique
identifiers (ULIDs).
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.utils import new_ulid_str
from pydantic import Field

ComponentType = Literal["node", "module", "manager", "experiment", "workcell"]
"""Valid component types for registry entries."""


class RegistryLock(MadsciBaseModel):
    """Lock information for a registry entry.

    Locks prevent multiple processes from claiming the same component name.
    They use a heartbeat mechanism to detect stale locks from crashed processes.
    """

    holder_pid: int = Field(description="Process ID of the lock holder")
    holder_host: str = Field(description="Hostname of the lock holder")
    holder_instance: str = Field(
        default_factory=new_ulid_str,
        description="Unique instance ID for this process",
    )
    acquired_at: datetime = Field(description="When the lock was acquired")
    heartbeat_at: datetime = Field(description="Last heartbeat timestamp")
    expires_at: datetime = Field(description="When the lock expires if not renewed")


class RegistryEntry(MadsciBaseModel):
    """A single entry in the registry.

    Each entry maps a human-readable component name to a unique ULID,
    with optional lock information for conflict prevention.
    """

    id: str = Field(description="Unique identifier (ULID) for this component")
    component_type: ComponentType = Field(
        description="Type of component (node, module, manager, etc.)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="When this entry was created",
    )
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Last time this component was active",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the component",
    )
    lock: Optional[RegistryLock] = Field(
        default=None,
        description="Lock information if component is currently active",
    )
    workcell_id: Optional[str] = Field(
        default=None,
        description="ID of the workcell this component belongs to (for multi-workcell labs)",
    )

    def is_locked(self) -> bool:
        """Check if entry is currently locked (lock exists and not expired)."""
        if self.lock is None:
            return False
        return datetime.now(tz=timezone.utc) < self.lock.expires_at

    def is_locked_by(self, instance_id: str) -> bool:
        """Check if entry is locked by a specific instance.

        Args:
            instance_id: The instance ID to check

        Returns:
            True if the entry is locked by this instance
        """
        if self.lock is None:
            return False
        return self.lock.holder_instance == instance_id


class LocalRegistry(MadsciBaseModel):
    """The local registry file structure.

    This represents the contents of ~/.madsci/registry.json,
    the local cache of component identities.
    """

    version: int = Field(default=1, description="Registry file format version")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="When this registry was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="When this registry was last updated",
    )
    entries: dict[str, RegistryEntry] = Field(
        default_factory=dict,
        description="Map of component names to their registry entries",
    )


class RegistryResolveResult(MadsciBaseModel):
    """Result from resolving a name in the registry."""

    name: str = Field(description="Component name that was resolved")
    id: str = Field(description="Resolved component ID (ULID)")
    component_type: ComponentType = Field(description="Type of component")
    is_new: bool = Field(
        default=False,
        description="Whether a new ID was generated (vs found existing)",
    )
    source: str = Field(
        default="local",
        description="Where the ID was resolved from (local, lab, new)",
    )
