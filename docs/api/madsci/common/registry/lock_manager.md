Module madsci.common.registry.lock_manager
==========================================
Lock manager for MADSci ID Registry.

This module provides heartbeat-based locking for registry entries,
preventing multiple processes from claiming the same component name.

Classes
-------

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
