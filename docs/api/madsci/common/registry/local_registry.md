Module madsci.common.registry.local_registry
============================================
Local registry manager for MADSci ID Registry.

This module provides the local file-based registry that stores component
name-to-ID mappings on each machine.

Classes
-------

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

`RegistryError(*args, **kwargs)`
:   General registry error.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException
