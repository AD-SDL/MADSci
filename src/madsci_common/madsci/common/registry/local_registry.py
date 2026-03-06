"""
Local registry manager for MADSci ID Registry.

This module provides the local file-based registry that stores component
name-to-ID mappings on each machine.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from filelock import FileLock, Timeout
from madsci.common.registry.lock_manager import LockManager, RegistryLockError
from madsci.common.types.registry_types import (
    ComponentType,
    LocalRegistry,
    RegistryEntry,
)
from madsci.common.utils import new_ulid_str

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS: float = 2.0
"""Interval in seconds between resolve() retry attempts on lock contention."""


class RegistryError(Exception):
    """General registry error."""


class LocalRegistryManager:
    """Manages the local registry file.

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
    """

    FILE_LOCK_TIMEOUT: int = 5
    """Timeout in seconds for acquiring file lock."""

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        lock_manager: Optional[LockManager] = None,
    ) -> None:
        """Initialize the local registry manager.

        Args:
            registry_path: Path to the registry file. When ``None`` the path
                is resolved via walk-up discovery (see ``_default_path``).
            lock_manager: Lock manager instance. Creates one if not provided.
        """
        self.registry_path = registry_path or self._default_path()
        self.lock_manager = lock_manager or LockManager()
        self._file_lock = FileLock(str(self.registry_path) + ".lock")

    @staticmethod
    def _default_path() -> Path:
        """Get the default registry path for this platform.

        Resolution order:
        1. ``MADSCI_REGISTRY_PATH`` environment variable (if set)
        2. Walk up from ``MADSCI_SETTINGS_DIR`` or CWD looking for a
           ``.madsci/`` sentinel directory (via ``sentry.find_madsci_dir``).
        3. Fall back to ``~/.madsci/registry.json``.

        Returns:
            Path to the registry JSON file.
        """
        env_path = os.environ.get("MADSCI_REGISTRY_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()

        from madsci.common.sentry import REGISTRY_FILE, find_madsci_dir  # noqa: PLC0415

        return find_madsci_dir(auto_create=True) / REGISTRY_FILE

    def _ensure_directory(self) -> None:
        """Ensure the registry directory exists."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> LocalRegistry:
        """Read the registry from file.

        Returns:
            The current registry contents, or an empty registry if file doesn't exist.
        """
        if not self.registry_path.exists():
            return LocalRegistry()

        with self.registry_path.open() as f:
            data = json.load(f)
        return LocalRegistry.model_validate(data)

    def _write(self, registry: LocalRegistry) -> None:
        """Write the registry to file.

        Args:
            registry: The registry to write.
        """
        self._ensure_directory()
        registry.updated_at = datetime.now(tz=timezone.utc)

        with self.registry_path.open("w") as f:
            json.dump(registry.model_dump(mode="json"), f, indent=2, default=str)

    def resolve(
        self,
        name: str,
        component_type: ComponentType,
        metadata: Optional[dict[str, Any]] = None,
        acquire_lock: bool = True,
        retry_timeout: Optional[float] = None,
    ) -> str:
        """Resolve a name to an ID, creating if necessary.

        This is the primary method for getting a component's ID. If the name
        doesn't exist, a new ULID is generated. If acquire_lock is True,
        a lock is acquired to prevent conflicts.

        Args:
            name: The component name to resolve.
            component_type: Type of component (node, manager, etc.).
            metadata: Optional metadata to store with the entry.
            acquire_lock: Whether to acquire a lock on the entry.
            retry_timeout: When set and a ``RegistryLockError`` occurs,
                retry every ``RETRY_INTERVAL_SECONDS`` until this many
                seconds have elapsed.  When ``None`` (default), fail
                immediately on lock contention.

        Returns:
            The component's ID (ULID).

        Raises:
            RegistryLockError: If the lock cannot be acquired (after retries,
                if retry_timeout is set).
            Timeout: If the file lock times out.
        """
        if retry_timeout is None:
            return self._resolve_once(name, component_type, metadata, acquire_lock)

        deadline = time.monotonic() + retry_timeout
        while True:
            try:
                return self._resolve_once(name, component_type, metadata, acquire_lock)
            except RegistryLockError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                logger.info(
                    "Registry lock contention for '%s', retrying (%.1fs remaining)",
                    name,
                    remaining,
                )
                time.sleep(min(RETRY_INTERVAL_SECONDS, remaining))

    def _resolve_once(
        self,
        name: str,
        component_type: ComponentType,
        metadata: Optional[dict[str, Any]],
        acquire_lock: bool,
    ) -> str:
        """Single attempt to resolve a name to an ID.

        See :meth:`resolve` for full documentation.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()

                if name in registry.entries:
                    entry = registry.entries[name]

                    if acquire_lock:
                        entry = self.lock_manager.acquire(entry)

                    entry.last_seen = datetime.now(tz=timezone.utc)
                    if metadata:
                        entry.metadata.update(metadata)

                    registry.entries[name] = entry
                    self._write(registry)

                    if acquire_lock:
                        self.lock_manager.start_heartbeat(name, self)

                    logger.debug(
                        "Resolved existing entry: name=%s entry_id=%s", name, entry.id
                    )
                    return entry.id

                # Create new entry
                entry = RegistryEntry(
                    id=new_ulid_str(),
                    component_type=component_type,
                    metadata=metadata or {},
                )

                if acquire_lock:
                    entry = self.lock_manager.acquire(entry)

                registry.entries[name] = entry
                self._write(registry)

                if acquire_lock:
                    self.lock_manager.start_heartbeat(name, self)

                logger.info(
                    "Created new registry entry: name=%s entry_id=%s", name, entry.id
                )
                return entry.id

        except Timeout as err:
            raise RegistryError(
                "Timeout acquiring file lock for registry. "
                "Another process may be holding the lock."
            ) from err

    def lookup(self, name: str) -> Optional[str]:
        """Look up an ID by name without acquiring a lock.

        Args:
            name: The component name to look up.

        Returns:
            The component's ID, or None if not found.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()
                entry = registry.entries.get(name)
                return entry.id if entry else None
        except Timeout:
            logger.warning("Timeout acquiring file lock for lookup")
            return None

    def get_entry(self, name: str) -> Optional[RegistryEntry]:
        """Get the full registry entry for a name.

        Args:
            name: The component name to look up.

        Returns:
            The registry entry, or None if not found.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()
                return registry.entries.get(name)
        except Timeout:
            logger.warning("Timeout acquiring file lock for get_entry")
            return None

    def refresh_lock(self, name: str) -> None:
        """Refresh the lock for an entry.

        This is called by the heartbeat thread to keep the lock alive.

        Args:
            name: The component name to refresh.

        Raises:
            RegistryLockError: If the entry doesn't exist or lock can't be refreshed.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()

                if name not in registry.entries:
                    raise RegistryLockError(f"Entry '{name}' not found")

                entry = registry.entries[name]
                entry = self.lock_manager.refresh(entry)
                registry.entries[name] = entry
                self._write(registry)
                logger.debug("Refreshed lock: name=%s", name)
        except Timeout as err:
            raise RegistryLockError("Timeout acquiring file lock for refresh") from err

    def release(self, name: str) -> None:
        """Release lock and stop heartbeat for an entry.

        Args:
            name: The component name to release.
        """
        self.lock_manager.stop_heartbeat(name)

        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()

                if name in registry.entries:
                    entry = registry.entries[name]
                    entry = self.lock_manager.release(entry)
                    registry.entries[name] = entry
                    self._write(registry)
                    logger.debug("Released lock: name=%s", name)
        except Timeout:
            logger.warning("Timeout releasing lock: name=%s", name)

    def rename(self, old_name: str, new_name: str, force: bool = False) -> str:
        """Rename a registry entry.

        Args:
            old_name: Current component name.
            new_name: New component name.
            force: If True, steal lock if old_name is locked.

        Returns:
            The component's ID (unchanged).

        Raises:
            RegistryError: If old_name doesn't exist or new_name already exists.
            RegistryLockError: If old_name is locked and force=False.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()

                if old_name not in registry.entries:
                    raise RegistryError(f"Entry '{old_name}' not found")

                if new_name in registry.entries:
                    raise RegistryError(f"Entry '{new_name}' already exists")

                entry = registry.entries[old_name]

                # Check lock
                if entry.is_locked() and not force:
                    raise RegistryLockError(
                        f"Cannot rename '{old_name}': currently locked by "
                        f"{entry.lock.holder_host} (PID {entry.lock.holder_pid})"
                    )

                # Rename
                entry.lock = None  # Clear lock on rename
                registry.entries[new_name] = entry
                del registry.entries[old_name]

                self._write(registry)
                logger.info(
                    "Renamed registry entry: old_name=%s new_name=%s",
                    old_name,
                    new_name,
                )

                return entry.id
        except Timeout as err:
            raise RegistryError("Timeout acquiring file lock for rename") from err

    def list_entries(
        self,
        component_type: Optional[ComponentType] = None,
        include_stale: bool = False,
    ) -> list[tuple[str, RegistryEntry]]:
        """List all entries in the registry.

        Args:
            component_type: Filter by type (node, manager, etc.).
            include_stale: Include entries with expired locks.

        Returns:
            List of (name, entry) tuples.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()

                results = []
                for name, entry in registry.entries.items():
                    if component_type and entry.component_type != component_type:
                        continue
                    if not include_stale and entry.lock and not entry.is_locked():
                        continue
                    results.append((name, entry))

                return results
        except Timeout:
            logger.warning("Timeout listing entries")
            return []

    def clean_stale(
        self,
        older_than_days: int = 7,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove stale entries from the registry.

        An entry is considered stale if it hasn't been seen in older_than_days
        and doesn't have an active lock.

        Args:
            older_than_days: Remove entries not seen in this many days.
            dry_run: If True, only return what would be removed.

        Returns:
            List of removed (or would-be-removed) entry names.
        """
        threshold = datetime.now(tz=timezone.utc) - timedelta(days=older_than_days)

        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()

                stale = [
                    name
                    for name, entry in registry.entries.items()
                    if entry.last_seen < threshold and not entry.is_locked()
                ]

                if not dry_run:
                    for name in stale:
                        del registry.entries[name]
                    self._write(registry)
                    logger.info("Cleaned stale entries: count=%d", len(stale))

                return stale
        except Timeout:
            logger.warning("Timeout cleaning stale entries")
            return []

    def export(self) -> dict[str, Any]:
        """Export the registry as a dictionary.

        Returns:
            The complete registry data.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                registry = self._read()
                return registry.model_dump(mode="json")
        except Timeout:
            logger.warning("Timeout exporting registry")
            return {}

    def import_entries(
        self,
        data: dict[str, Any],
        merge: bool = True,
    ) -> None:
        """Import entries from a dictionary.

        Args:
            data: Registry data to import.
            merge: If True, merge with existing. If False, replace.
        """
        try:
            with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
                imported = LocalRegistry.model_validate(data)

                if merge:
                    registry = self._read()
                    for name, entry in imported.entries.items():
                        if name not in registry.entries:
                            registry.entries[name] = entry
                else:
                    registry = imported

                self._write(registry)
                logger.info(
                    "Imported entries: count=%d merge=%s", len(imported.entries), merge
                )
        except Timeout as err:
            raise RegistryError("Timeout importing entries") from err
