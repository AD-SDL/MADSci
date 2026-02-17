Module madsci.common.registry.identity_resolver
===============================================
Identity resolver for MADSci ID Registry.

This module provides the high-level interface for resolving component names
to IDs, with support for both local and lab-level registries.

Classes
-------

`IdentityResolver(lab_url: pydantic.networks.AnyUrl | None = None, local_registry: madsci.common.registry.local_registry.LocalRegistryManager | None = None)`
:   Resolves component names to IDs with distributed coordination.

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

    Initialize the identity resolver.

    Args:
        lab_url: URL of the lab manager for distributed coordination.
                 If not provided, operates in standalone mode.
        local_registry: Local registry manager instance. Creates one if not provided.

    ### Instance variables

    `lab_client: Any | None`
    :   Lazy-initialize lab client.

        Returns:
            LabClient instance if lab_url is configured, None otherwise.

    ### Methods

    `lookup(self, name: str) ‑> str | None`
    :   Look up an ID without acquiring a lock.

        Args:
            name: Component name to look up.

        Returns:
            The component's ID, or None if not found.

    `release(self, name: str) ‑> None`
    :   Release a lock on a name.

        This should be called during component shutdown.

        Args:
            name: Component name to release.

    `release_all(self) ‑> None`
    :   Release all locks held by this resolver.

        Call this during shutdown to clean up all resources.

    `resolve(self, name: str, component_type: Literal['node', 'module', 'manager', 'experiment', 'workcell'], metadata: dict[str, typing.Any] | None = None) ‑> str`
    :   Resolve a name to an ID.

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

    `resolve_with_info(self, name: str, component_type: Literal['node', 'module', 'manager', 'experiment', 'workcell'], metadata: dict[str, typing.Any] | None = None) ‑> madsci.common.types.registry_types.RegistryResolveResult`
    :   Resolve a name and return detailed information.

        Like resolve(), but returns additional information about where
        the ID came from.

        Args:
            name: Component name.
            component_type: Type of component.
            metadata: Optional metadata.

        Returns:
            RegistryResolveResult with ID and source information.
