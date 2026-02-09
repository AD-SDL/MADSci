"""
Identity resolver for MADSci ID Registry.

This module provides the high-level interface for resolving component names
to IDs, with support for both local and lab-level registries.
"""

import logging
from typing import Any, Optional

from madsci.common.registry.local_registry import LocalRegistryManager
from madsci.common.registry.lock_manager import RegistryLockError
from madsci.common.types.registry_types import ComponentType, RegistryResolveResult
from pydantic import AnyUrl

logger = logging.getLogger(__name__)


class IdentityResolver:
    """Resolves component names to IDs with distributed coordination.

    This is the primary interface for components to get their identity. It
    supports both standalone mode (local registry only) and lab mode (with
    a central lab registry for distributed coordination).

    Resolution order:
        1. Check local registry
        2. If lab available, check lab registry
        3. If not found, generate new ID
        4. Acquire lock
        5. Sync to lab if available

    Example:
        resolver = IdentityResolver(lab_url="http://localhost:8000")

        # Get ID for a node (creates if new, locks to prevent conflicts)
        node_id = resolver.resolve(
            name="liquidhandler_1",
            component_type="node",
            metadata={"module_name": "liquidhandler"},
        )

        # When shutting down
        resolver.release("liquidhandler_1")
    """

    def __init__(
        self,
        lab_url: Optional[AnyUrl] = None,
        local_registry: Optional[LocalRegistryManager] = None,
    ) -> None:
        """Initialize the identity resolver.

        Args:
            lab_url: URL of the lab manager for distributed coordination.
                     If not provided, operates in standalone mode.
            local_registry: Local registry manager instance. Creates one if not provided.
        """
        self.lab_url = lab_url
        self.local_registry = local_registry or LocalRegistryManager()
        self._lab_client: Optional[Any] = None

    @property
    def lab_client(self) -> Optional[Any]:
        """Lazy-initialize lab client.

        Returns:
            LabClient instance if lab_url is configured, None otherwise.
        """
        if self._lab_client is None and self.lab_url:
            try:
                from madsci.client import LabClient  # noqa: PLC0415

                self._lab_client = LabClient(str(self.lab_url))
            except ImportError:
                logger.warning(
                    "madsci.client not available, lab registry sync disabled"
                )
                self._lab_client = None
        return self._lab_client

    def resolve(
        self,
        name: str,
        component_type: ComponentType,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Resolve a name to an ID.

        This is the primary method for components to get their identity.
        It will create a new ID if the name doesn't exist, and acquire a
        lock to prevent conflicts.

        Args:
            name: Component name (e.g., "liquidhandler_1").
            component_type: Type of component (node, manager, etc.).
            metadata: Optional metadata to store with the entry.

        Returns:
            The component's ID (ULID).

        Raises:
            RegistryLockError: If the name is already locked by another process.
        """
        try:
            # Try local registry first
            local_id = self.local_registry.resolve(
                name=name,
                component_type=component_type,
                metadata=metadata,
                acquire_lock=True,
            )

            # Sync to lab if available
            if self.lab_client:
                try:
                    self._sync_to_lab(name, local_id, component_type, metadata)
                except Exception as e:
                    # Lab sync failure is non-fatal in standalone mode
                    logger.warning("Failed to sync to lab registry", error=str(e))

            return local_id

        except RegistryLockError:
            # Lock conflict - check if lab has different info
            if self.lab_client:
                try:
                    return self._resolve_from_lab(name, component_type, metadata)
                except Exception as e:
                    logger.warning("Failed to resolve from lab", error=str(e))
            raise

    def resolve_with_info(
        self,
        name: str,
        component_type: ComponentType,
        metadata: Optional[dict[str, Any]] = None,
    ) -> RegistryResolveResult:
        """Resolve a name and return detailed information.

        Like resolve(), but returns additional information about where
        the ID came from.

        Args:
            name: Component name.
            component_type: Type of component.
            metadata: Optional metadata.

        Returns:
            RegistryResolveResult with ID and source information.
        """
        # Check if the name exists before resolving
        existing_id = self.local_registry.lookup(name)
        is_new = existing_id is None

        resolved_id = self.resolve(name, component_type, metadata)

        return RegistryResolveResult(
            name=name,
            id=resolved_id,
            component_type=component_type,
            is_new=is_new,
            source="local",
        )

    def _resolve_from_lab(
        self,
        name: str,
        component_type: ComponentType,
        metadata: Optional[dict[str, Any]],
    ) -> str:
        """Resolve from lab registry when local fails.

        Args:
            name: Component name.
            component_type: Type of component.
            metadata: Optional metadata.

        Returns:
            The component's ID from the lab registry.

        Raises:
            RegistryLockError: If the lab registry also has a conflict.
        """
        if not self.lab_client:
            raise RegistryLockError("No lab client available")

        # Query lab registry
        try:
            response = self.lab_client.get(f"/registry/resolve/{name}")
            if response and "id" in response:
                lab_id = response["id"]

                # Try to acquire lock on lab registry
                self.lab_client.post(
                    f"/registry/entries/{name}/lock",
                    {
                        "holder_host": self.local_registry.lock_manager.hostname,
                        "holder_pid": self.local_registry.lock_manager.pid,
                        "holder_instance": self.local_registry.lock_manager.instance_id,
                    },
                )

                # Sync back to local
                self.local_registry.import_entries(
                    {
                        "entries": {
                            name: {
                                "id": lab_id,
                                "component_type": component_type,
                                "metadata": metadata or {},
                            }
                        }
                    },
                    merge=True,
                )

                return lab_id
        except Exception as e:
            raise RegistryLockError(f"Failed to resolve from lab: {e}") from e

        raise RegistryLockError(f"Name '{name}' not found in lab registry")

    def _sync_to_lab(
        self,
        name: str,
        component_id: str,  # noqa: ARG002
        component_type: ComponentType,
        metadata: Optional[dict[str, Any]],
    ) -> None:
        """Sync an entry to the lab registry.

        Args:
            name: Component name.
            component_id: Component ID.
            component_type: Type of component.
            metadata: Optional metadata.
        """
        if not self.lab_client:
            return

        try:
            self.lab_client.post(
                f"/registry/entries/{name}",
                {
                    "component_type": component_type,
                    "metadata": metadata or {},
                    "acquire_lock": True,
                    "lock_holder_host": self.local_registry.lock_manager.hostname,
                    "lock_holder_pid": self.local_registry.lock_manager.pid,
                    "lock_holder_instance": self.local_registry.lock_manager.instance_id,
                },
            )
            logger.debug("Synced to lab registry", name=name)
        except Exception as e:
            logger.warning("Failed to sync to lab", name=name, error=str(e))

    def lookup(self, name: str) -> Optional[str]:
        """Look up an ID without acquiring a lock.

        Args:
            name: Component name to look up.

        Returns:
            The component's ID, or None if not found.
        """
        # Check local first
        local_id = self.local_registry.lookup(name)
        if local_id:
            return local_id

        # Check lab if available
        if self.lab_client:
            try:
                response = self.lab_client.get(f"/registry/resolve/{name}")
                if response and "id" in response:
                    return response["id"]
            except Exception as e:
                logger.debug("Failed to lookup from lab", error=str(e))

        return None

    def release(self, name: str) -> None:
        """Release a lock on a name.

        This should be called during component shutdown.

        Args:
            name: Component name to release.
        """
        self.local_registry.release(name)

        # Also release on lab if available
        if self.lab_client:
            try:
                instance_id = self.local_registry.lock_manager.instance_id
                self.lab_client.post(
                    f"/registry/entries/{name}/unlock",
                    {"holder_instance": instance_id},
                )
                logger.debug("Released from lab registry", name=name)
            except Exception as e:
                logger.debug("Failed to release from lab", name=name, error=str(e))

    def release_all(self) -> None:
        """Release all locks held by this resolver.

        Call this during shutdown to clean up all resources.
        """
        self.local_registry.lock_manager.stop_all_heartbeats()
        logger.debug("Released all locks")
