"""
ID Registry for MADSci.

This module provides reliable, persistent mapping between human-readable
component names and their unique identifiers (ULIDs), with support for
distributed operation and conflict resolution.

The registry system has two tiers:
1. Local Registry: File-based registry on each machine (~/.madsci/registry.json)
2. Lab Registry: API endpoints on Lab Manager for distributed coordination

Example:
    from madsci.common.registry import IdentityResolver

    # Create resolver (optionally connected to lab)
    resolver = IdentityResolver(lab_url="http://localhost:8000")

    # Resolve a component name to ID (creates if new, locks to prevent conflicts)
    node_id = resolver.resolve(
        name="liquidhandler_1",
        component_type="node",
        metadata={"module_name": "liquidhandler"},
    )

    # When shutting down
    resolver.release("liquidhandler_1")
"""

from madsci.common.registry.identity_resolver import IdentityResolver
from madsci.common.registry.local_registry import LocalRegistryManager
from madsci.common.registry.lock_manager import LockManager, RegistryLockError

__all__ = [
    "IdentityResolver",
    "LocalRegistryManager",
    "LockManager",
    "RegistryLockError",
]
