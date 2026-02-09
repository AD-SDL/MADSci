"""
Lock manager for MADSci ID Registry.

This module provides heartbeat-based locking for registry entries,
preventing multiple processes from claiming the same component name.
"""

import logging
import os
import socket
import threading
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from madsci.common.types.registry_types import RegistryEntry, RegistryLock
from madsci.common.utils import new_ulid_str

if TYPE_CHECKING:
    from madsci.common.registry.local_registry import LocalRegistryManager

logger = logging.getLogger(__name__)


class RegistryLockError(Exception):
    """Raised when a lock cannot be acquired.

    This typically means another process is already using the component name.
    """


class LockManager:
    """Manages heartbeat-based locks for registry entries.

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
    """

    LOCK_TTL: timedelta = timedelta(seconds=30)
    """Default lock time-to-live before expiration."""

    HEARTBEAT_INTERVAL: int = 10
    """Default interval between heartbeats in seconds."""

    def __init__(
        self,
        instance_id: Optional[str] = None,
        lock_ttl: Optional[timedelta] = None,
        heartbeat_interval: Optional[int] = None,
    ) -> None:
        """Initialize the lock manager.

        Args:
            instance_id: Unique identifier for this process instance.
                         Generated automatically if not provided.
            lock_ttl: Custom lock TTL. Defaults to LOCK_TTL.
            heartbeat_interval: Custom heartbeat interval. Defaults to HEARTBEAT_INTERVAL.
        """
        self.instance_id = instance_id or new_ulid_str()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.lock_ttl = lock_ttl or self.LOCK_TTL
        self.heartbeat_interval = heartbeat_interval or self.HEARTBEAT_INTERVAL
        self._heartbeat_threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}

    def create_lock(self) -> RegistryLock:
        """Create a new lock for this instance.

        Returns:
            A new RegistryLock with current process information.
        """
        now = datetime.utcnow()
        return RegistryLock(
            holder_pid=self.pid,
            holder_host=self.hostname,
            holder_instance=self.instance_id,
            acquired_at=now,
            heartbeat_at=now,
            expires_at=now + self.lock_ttl,
        )

    def can_acquire(self, entry: RegistryEntry) -> tuple[bool, str]:
        """Check if a lock can be acquired on an entry.

        Args:
            entry: The registry entry to check.

        Returns:
            A tuple of (can_acquire, reason) where reason explains why or why not.
        """
        if entry.lock is None:
            return True, "No existing lock"

        if entry.is_locked_by(self.instance_id):
            return True, "Already locked by this instance"

        if not entry.is_locked():
            return True, f"Lock expired at {entry.lock.expires_at}"

        return False, (
            f"Locked by {entry.lock.holder_host} "
            f"(PID {entry.lock.holder_pid}) "
            f"until {entry.lock.expires_at}"
        )

    def acquire(self, entry: RegistryEntry) -> RegistryEntry:
        """Acquire a lock on an entry.

        Args:
            entry: The registry entry to lock.

        Returns:
            The entry with an active lock.

        Raises:
            RegistryLockError: If the lock cannot be acquired.
        """
        can_acquire, reason = self.can_acquire(entry)

        if not can_acquire:
            raise RegistryLockError(f"Cannot acquire lock for '{entry.id}': {reason}")

        entry.lock = self.create_lock()
        entry.last_seen = datetime.utcnow()
        return entry

    def refresh(self, entry: RegistryEntry) -> RegistryEntry:
        """Refresh the lock heartbeat on an entry.

        Args:
            entry: The registry entry with the lock to refresh.

        Returns:
            The entry with an updated lock.

        Raises:
            RegistryLockError: If the lock is not owned by this instance.
        """
        if not entry.is_locked_by(self.instance_id):
            raise RegistryLockError("Cannot refresh lock not owned by this instance")

        if entry.lock is None:
            raise RegistryLockError("Cannot refresh: no lock exists")

        now = datetime.utcnow()
        entry.lock.heartbeat_at = now
        entry.lock.expires_at = now + self.lock_ttl
        entry.last_seen = now
        return entry

    def release(self, entry: RegistryEntry) -> RegistryEntry:
        """Release a lock on an entry.

        Args:
            entry: The registry entry with the lock to release.

        Returns:
            The entry with the lock removed.
        """
        if entry.lock and entry.is_locked_by(self.instance_id):
            entry.lock = None
        return entry

    def start_heartbeat(self, name: str, registry: "LocalRegistryManager") -> None:
        """Start a background heartbeat thread for an entry.

        This keeps the lock alive by periodically refreshing it.

        Args:
            name: The component name in the registry.
            registry: The registry manager to update.
        """
        if name in self._heartbeat_threads:
            return  # Already running

        stop_event = threading.Event()
        self._stop_events[name] = stop_event

        def heartbeat_loop() -> None:
            while not stop_event.wait(self.heartbeat_interval):
                try:
                    registry.refresh_lock(name)
                except Exception as e:
                    # Log but don't crash - will retry next interval
                    logger.warning("Failed to refresh lock", name=name, error=str(e))

        thread = threading.Thread(
            target=heartbeat_loop, daemon=True, name=f"heartbeat-{name}"
        )
        thread.start()
        self._heartbeat_threads[name] = thread
        logger.debug("Started heartbeat thread", name=name)

    def stop_heartbeat(self, name: str) -> None:
        """Stop the heartbeat thread for an entry.

        Args:
            name: The component name to stop heartbeating.
        """
        if name in self._stop_events:
            self._stop_events[name].set()
            del self._stop_events[name]
            logger.debug("Stopped heartbeat", name=name)
        if name in self._heartbeat_threads:
            # Wait briefly for thread to exit
            self._heartbeat_threads[name].join(timeout=1.0)
            del self._heartbeat_threads[name]

    def stop_all_heartbeats(self) -> None:
        """Stop all heartbeat threads.

        Call this during shutdown to clean up resources.
        """
        for name in list(self._stop_events.keys()):
            self.stop_heartbeat(name)
        logger.debug("Stopped all heartbeat threads")
