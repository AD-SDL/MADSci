Module madsci.common.registry
=============================
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

Sub-modules
-----------
* madsci.common.registry.identity_resolver
* madsci.common.registry.local_registry
* madsci.common.registry.lock_manager

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

`LocalRegistryManager(registry_path: pathlib.Path | None = None, lock_manager: madsci.common.registry.lock_manager.LockManager | None = None)`
:   Manages the local registry file.

    The local registry provides persistent name-to-ID mapping for components.
    By default the registry file is discovered via walk-up from the current
    working directory (or ``MADSCI_SETTINGS_DIR``), stopping at the first
    ``.madsci/`` sentinel directory found, then falling back to
    ``~/.madsci/registry.json``.  The path can also be overridden explicitly
    via the ``MADSCI_REGISTRY_PATH`` environment variable or the
    ``registry_path`` constructor argument.

    Attributes:
        FILE_LOCK_TIMEOUT: Timeout for acquiring file lock (default: 5 seconds)

    Example:
        registry = LocalRegistryManager()

        # Resolve a name to an ID (creates if not found)
        node_id = registry.resolve("my_node", "node")

        # Look up without acquiring lock
        node_id = registry.lookup("my_node")

        # Release lock when done
        registry.release("my_node")

    Initialize the local registry manager.

    Args:
        registry_path: Path to the registry file. When ``None`` the path
            is resolved via walk-up discovery (see ``_default_path``).
        lock_manager: Lock manager instance. Creates one if not provided.

    ### Class variables

    `FILE_LOCK_TIMEOUT: int`
    :   Timeout in seconds for acquiring file lock.

    ### Methods

    `clean_stale(self, older_than_days: int = 7, dry_run: bool = False) ‑> list[str]`
    :   Remove stale entries from the registry.

        An entry is considered stale if it hasn't been seen in older_than_days
        and doesn't have an active lock.

        Args:
            older_than_days: Remove entries not seen in this many days.
            dry_run: If True, only return what would be removed.

        Returns:
            List of removed (or would-be-removed) entry names.

    `export(self) ‑> dict[str, typing.Any]`
    :   Export the registry as a dictionary.

        Returns:
            The complete registry data.

    `get_entry(self, name: str) ‑> madsci.common.types.registry_types.RegistryEntry | None`
    :   Get the full registry entry for a name.

        Args:
            name: The component name to look up.

        Returns:
            The registry entry, or None if not found.

    `import_entries(self, data: dict[str, typing.Any], merge: bool = True) ‑> None`
    :   Import entries from a dictionary.

        Args:
            data: Registry data to import.
            merge: If True, merge with existing. If False, replace.

    `list_entries(self, component_type: Literal['node', 'module', 'manager', 'experiment', 'workcell'] | None = None, include_stale: bool = False) ‑> list[tuple[str, madsci.common.types.registry_types.RegistryEntry]]`
    :   List all entries in the registry.

        Args:
            component_type: Filter by type (node, manager, etc.).
            include_stale: Include entries with expired locks.

        Returns:
            List of (name, entry) tuples.

    `lookup(self, name: str) ‑> str | None`
    :   Look up an ID by name without acquiring a lock.

        Args:
            name: The component name to look up.

        Returns:
            The component's ID, or None if not found.

    `refresh_lock(self, name: str) ‑> None`
    :   Refresh the lock for an entry.

        This is called by the heartbeat thread to keep the lock alive.

        Args:
            name: The component name to refresh.

        Raises:
            RegistryLockError: If the entry doesn't exist or lock can't be refreshed.

    `release(self, name: str) ‑> None`
    :   Release lock and stop heartbeat for an entry.

        Args:
            name: The component name to release.

    `rename(self, old_name: str, new_name: str, force: bool = False) ‑> str`
    :   Rename a registry entry.

        Args:
            old_name: Current component name.
            new_name: New component name.
            force: If True, steal lock if old_name is locked.

        Returns:
            The component's ID (unchanged).

        Raises:
            RegistryError: If old_name doesn't exist or new_name already exists.
            RegistryLockError: If old_name is locked and force=False.

    `resolve(self, name: str, component_type: Literal['node', 'module', 'manager', 'experiment', 'workcell'], metadata: dict[str, typing.Any] | None = None, acquire_lock: bool = True) ‑> str`
    :   Resolve a name to an ID, creating if necessary.

        This is the primary method for getting a component's ID. If the name
        doesn't exist, a new ULID is generated. If acquire_lock is True,
        a lock is acquired to prevent conflicts.

        Args:
            name: The component name to resolve.
            component_type: Type of component (node, manager, etc.).
            metadata: Optional metadata to store with the entry.
            acquire_lock: Whether to acquire a lock on the entry.

        Returns:
            The component's ID (ULID).

        Raises:
            RegistryLockError: If the lock cannot be acquired.
            Timeout: If the file lock times out.

`LockManager(instance_id: str | None = None, lock_ttl: datetime.timedelta | None = None, heartbeat_interval: int | None = None)`
:   Manages heartbeat-based locks for registry entries.

    This class handles lock acquisition, refresh, and release for registry entries.
    It uses a heartbeat mechanism to detect stale locks from crashed processes.

    Note:
        This implementation uses the cross-platform `filelock` library for file
        locking. Do NOT use `fcntl` directly as it is Unix-only.

    Attributes:
        LOCK_TTL: How long a lock is valid before it expires (default: 30 seconds)
        HEARTBEAT_INTERVAL: How often to refresh locks (default: 10 seconds)

    Example:
        lock_manager = LockManager()
        entry = RegistryEntry(id="...", component_type="node")

        # Acquire lock
        entry = lock_manager.acquire(entry)

        # Start background heartbeat
        lock_manager.start_heartbeat("my_node", registry_manager)

        # When done
        lock_manager.stop_heartbeat("my_node")
        entry = lock_manager.release(entry)

    Initialize the lock manager.

    Args:
        instance_id: Unique identifier for this process instance.
                     Generated automatically if not provided.
        lock_ttl: Custom lock TTL. Defaults to LOCK_TTL.
        heartbeat_interval: Custom heartbeat interval. Defaults to HEARTBEAT_INTERVAL.

    ### Class variables

    `HEARTBEAT_INTERVAL: int`
    :   Default interval between heartbeats in seconds.

    `LOCK_TTL: datetime.timedelta`
    :   Default lock time-to-live before expiration.

    ### Methods

    `acquire(self, entry: madsci.common.types.registry_types.RegistryEntry) ‑> madsci.common.types.registry_types.RegistryEntry`
    :   Acquire a lock on an entry.

        Args:
            entry: The registry entry to lock.

        Returns:
            The entry with an active lock.

        Raises:
            RegistryLockError: If the lock cannot be acquired.

    `can_acquire(self, entry: madsci.common.types.registry_types.RegistryEntry) ‑> tuple[bool, str]`
    :   Check if a lock can be acquired on an entry.

        Args:
            entry: The registry entry to check.

        Returns:
            A tuple of (can_acquire, reason) where reason explains why or why not.

    `create_lock(self) ‑> madsci.common.types.registry_types.RegistryLock`
    :   Create a new lock for this instance.

        Returns:
            A new RegistryLock with current process information.

    `refresh(self, entry: madsci.common.types.registry_types.RegistryEntry) ‑> madsci.common.types.registry_types.RegistryEntry`
    :   Refresh the lock heartbeat on an entry.

        Args:
            entry: The registry entry with the lock to refresh.

        Returns:
            The entry with an updated lock.

        Raises:
            RegistryLockError: If the lock is not owned by this instance.

    `release(self, entry: madsci.common.types.registry_types.RegistryEntry) ‑> madsci.common.types.registry_types.RegistryEntry`
    :   Release a lock on an entry.

        Args:
            entry: The registry entry with the lock to release.

        Returns:
            The entry with the lock removed.

    `start_heartbeat(self, name: str, registry: LocalRegistryManager)`
    :   Start a background heartbeat thread for an entry.

        This keeps the lock alive by periodically refreshing it.

        Args:
            name: The component name in the registry.
            registry: The registry manager to update.

    `stop_all_heartbeats(self) ‑> None`
    :   Stop all heartbeat threads.

        Call this during shutdown to clean up resources.

    `stop_heartbeat(self, name: str) ‑> None`
    :   Stop the heartbeat thread for an entry.

        Args:
            name: The component name to stop heartbeating.

`RegistryLockError(*args, **kwargs)`
:   Raised when a lock cannot be acquired.

    This typically means another process is already using the component name.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException
