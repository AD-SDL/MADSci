# MADSci ID Registry Design Document

**Status**: Draft
**Date**: 2026-02-07
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for the MADSci ID Registry system. The registry provides reliable, persistent mapping between human-readable component names and their unique identifiers (ULIDs), with support for distributed operation and conflict resolution.

## Problem Statement

### Current State

Currently, component IDs are stored in definition YAML files:
- `node_definitions/liquidhandler_1.node.yaml` contains the `node_id`
- `managers/example_workcell.manager.yaml` contains the `manager_id`

**Problems with this approach:**
1. IDs are scattered across files, hard to manage
2. No conflict detection when two processes claim the same name
3. No way to detect stale/crashed processes
4. Mixing identity with configuration
5. Difficult to maintain consistency across distributed systems

### Requirements

1. **Reliable name-to-ID mapping**: Given a name, always get the same ID
2. **Crash recovery**: If a node crashes, restart with the same ID
3. **Conflict detection**: If two processes try to use the same name, detect and fail gracefully
4. **Cross-platform**: Work on Windows, macOS, Linux
5. **Docker-compatible**: Work inside and outside Docker containers
6. **Standalone mode**: Work without any services running (local development)
7. **Lab mode**: Work with lab server as source of truth (production)
8. **Persistence**: Survive restarts, system reboots

---

## Architecture

### Two-Tier Registry

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ID Resolution Flow                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Component Startup                                                           │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         IdentityResolver                                 ││
│  │                                                                          ││
│  │   1. Check Local Registry (fast, always available)                      ││
│  │   2. Check Lab Registry (if available, source of truth)                 ││
│  │   3. Generate new ID (if not found anywhere)                            ││
│  │   4. Acquire lock (prevent conflicts)                                   ││
│  │   5. Sync to Lab Registry (if available)                                ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────────────┐      ┌──────────────────────────┐             │
│  │     Local Registry       │      │     Lab Registry         │             │
│  │  ~/.madsci/registry.json │ ◄──► │  Lab Manager API         │             │
│  │                          │ sync │  /registry/*             │             │
│  │  - Always available      │      │  - Source of truth       │             │
│  │  - Fast lookups          │      │  - Distributed sync      │             │
│  │  - Heartbeat locks       │      │  - Cross-host aware      │             │
│  └──────────────────────────┘      └──────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Components

1. **Local Registry**: File-based registry on each machine (`~/.madsci/registry.json`)
2. **Lab Registry**: API endpoints on Lab Manager for distributed coordination
3. **Identity Resolver**: Client-side logic for resolving names to IDs
4. **Lock Manager**: Heartbeat-based locking for conflict prevention

---

## Local Registry

### File Location

| Platform | Path |
|----------|------|
| Linux | `~/.madsci/registry.json` |
| macOS | `~/.madsci/registry.json` |
| Windows | `%USERPROFILE%\.madsci\registry.json` |
| Docker | `/app/.madsci/registry.json` (mount from host) |

### File Format

```json
{
  "version": 1,
  "created_at": "2026-02-07T10:00:00Z",
  "updated_at": "2026-02-07T15:30:00Z",
  "entries": {
    "liquidhandler_1": {
      "id": "01JYFEHVSV20D60Z88RVERJ75N",
      "component_type": "node",
      "created_at": "2026-02-07T10:00:00Z",
      "last_seen": "2026-02-07T15:30:00Z",
      "metadata": {
        "module_name": "liquidhandler",
        "module_version": "0.0.1",
        "interface_variants": ["real", "fake"]
      },
      "lock": {
        "holder_pid": 12345,
        "holder_host": "lab-workstation-1",
        "holder_instance": "abc123",
        "acquired_at": "2026-02-07T15:30:00Z",
        "heartbeat_at": "2026-02-07T15:30:05Z",
        "expires_at": "2026-02-07T15:30:35Z"
      }
    },
    "liquidhandler_module": {
      "id": "01JYFEHVT120D60Z88RVERJ75M",
      "component_type": "module",
      "created_at": "2026-02-07T09:00:00Z",
      "last_seen": "2026-02-07T15:30:00Z",
      "metadata": {
        "module_name": "liquidhandler",
        "module_version": "1.2.0",
        "interface_variants": ["real", "fake", "sim"],
        "repository_url": "https://github.com/AD-SDL/liquidhandler_module"
      },
      "lock": null
    },
    "workcell_manager": {
      "id": "01JK706A23XYZFT4SA5M0VQT35H",
      "component_type": "manager",
      "created_at": "2026-02-05T08:00:00Z",
      "last_seen": "2026-02-07T15:30:00Z",
      "metadata": {
        "manager_type": "workcell_manager"
      },
      "lock": null
    }
  }
}
```

### Data Types

```python
# src/madsci_common/madsci/common/types/registry_types.py
from datetime import datetime
from typing import Optional, Literal
from pydantic import Field
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.utils import new_ulid_str

class RegistryLock(MadsciBaseModel):
    """Lock information for a registry entry."""
    holder_pid: int
    holder_host: str
    holder_instance: str = Field(default_factory=new_ulid_str)
    acquired_at: datetime
    heartbeat_at: datetime
    expires_at: datetime


class RegistryEntry(MadsciBaseModel):
    """A single entry in the registry."""
    id: str
    component_type: Literal["node", "module", "manager", "experiment", "workcell"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
    lock: Optional[RegistryLock] = None

    def is_locked(self) -> bool:
        """Check if entry is currently locked."""
        if self.lock is None:
            return False
        return datetime.utcnow() < self.lock.expires_at

    def is_locked_by_me(self, instance_id: str) -> bool:
        """Check if entry is locked by this instance."""
        if self.lock is None:
            return False
        return self.lock.holder_instance == instance_id


class LocalRegistry(MadsciBaseModel):
    """The local registry file structure."""
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    entries: dict[str, RegistryEntry] = Field(default_factory=dict)
```

---

## Lock Manager

### Locking Protocol

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Lock Acquisition Flow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Process A wants to claim "liquidhandler_1"                                  │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────┐                                                        │
│  │ Read registry   │                                                        │
│  │ file with lock  │  (file lock prevents concurrent reads/writes)         │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────┐                        │
│  │ Entry exists?                                   │                        │
│  └─────────────────────────────────────────────────┘                        │
│       │ NO                           │ YES                                   │
│       ▼                              ▼                                       │
│  ┌─────────────┐           ┌─────────────────────┐                          │
│  │ Create new  │           │ Entry locked?       │                          │
│  │ entry + ID  │           └─────────────────────┘                          │
│  │ + lock      │                │ NO          │ YES                          │
│  └─────────────┘                ▼             ▼                              │
│                          ┌───────────┐  ┌────────────────┐                  │
│                          │ Acquire   │  │ Lock expired?  │                  │
│                          │ lock      │  └────────────────┘                  │
│                          └───────────┘       │ NO      │ YES                 │
│                                              ▼         ▼                     │
│                                         ┌────────┐  ┌───────────┐           │
│                                         │ FAIL   │  │ Steal     │           │
│                                         │ with   │  │ lock      │           │
│                                         │ error  │  │ (log warn)│           │
│                                         └────────┘  └───────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Lock Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Lock TTL | 30 seconds | Lock expires if not renewed |
| Heartbeat interval | 10 seconds | How often to renew lock |
| Stale threshold | 60 seconds | Entry considered stale if not seen |
| File lock timeout | 5 seconds | Timeout for acquiring file lock |

### Implementation

```python
# src/madsci_common/madsci/common/registry/lock_manager.py
import os
import socket
import threading
import fcntl  # Unix only, need alternative for Windows
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from madsci.common.types.registry_types import RegistryLock, RegistryEntry
from madsci.common.utils import new_ulid_str

class LockManager:
    """Manages heartbeat-based locks for registry entries."""

    LOCK_TTL = timedelta(seconds=30)
    HEARTBEAT_INTERVAL = 10  # seconds

    def __init__(self, instance_id: str = None):
        self.instance_id = instance_id or new_ulid_str()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self._heartbeat_threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}

    def create_lock(self) -> RegistryLock:
        """Create a new lock for this instance."""
        now = datetime.utcnow()
        return RegistryLock(
            holder_pid=self.pid,
            holder_host=self.hostname,
            holder_instance=self.instance_id,
            acquired_at=now,
            heartbeat_at=now,
            expires_at=now + self.LOCK_TTL,
        )

    def can_acquire(self, entry: RegistryEntry) -> tuple[bool, str]:
        """Check if lock can be acquired on entry.

        Returns:
            (can_acquire, reason)
        """
        if entry.lock is None:
            return True, "No existing lock"

        if entry.is_locked_by_me(self.instance_id):
            return True, "Already locked by this instance"

        if not entry.is_locked():
            return True, f"Lock expired at {entry.lock.expires_at}"

        return False, (
            f"Locked by {entry.lock.holder_host} "
            f"(PID {entry.lock.holder_pid}) "
            f"until {entry.lock.expires_at}"
        )

    def acquire(self, entry: RegistryEntry) -> RegistryEntry:
        """Acquire lock on entry. Raises if cannot acquire."""
        can_acquire, reason = self.can_acquire(entry)

        if not can_acquire:
            raise RegistryLockError(
                f"Cannot acquire lock for '{entry.id}': {reason}"
            )

        entry.lock = self.create_lock()
        entry.last_seen = datetime.utcnow()
        return entry

    def refresh(self, entry: RegistryEntry) -> RegistryEntry:
        """Refresh lock heartbeat."""
        if not entry.is_locked_by_me(self.instance_id):
            raise RegistryLockError("Cannot refresh lock not owned by this instance")

        now = datetime.utcnow()
        entry.lock.heartbeat_at = now
        entry.lock.expires_at = now + self.LOCK_TTL
        entry.last_seen = now
        return entry

    def release(self, entry: RegistryEntry) -> RegistryEntry:
        """Release lock on entry."""
        if entry.lock and entry.is_locked_by_me(self.instance_id):
            entry.lock = None
        return entry

    def start_heartbeat(self, name: str, registry: "LocalRegistryManager"):
        """Start background heartbeat thread for an entry."""
        if name in self._heartbeat_threads:
            return  # Already running

        stop_event = threading.Event()
        self._stop_events[name] = stop_event

        def heartbeat_loop():
            while not stop_event.wait(self.HEARTBEAT_INTERVAL):
                try:
                    registry.refresh_lock(name)
                except Exception as e:
                    # Log but don't crash - will retry next interval
                    pass

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()
        self._heartbeat_threads[name] = thread

    def stop_heartbeat(self, name: str):
        """Stop heartbeat thread for an entry."""
        if name in self._stop_events:
            self._stop_events[name].set()
            del self._stop_events[name]
        if name in self._heartbeat_threads:
            del self._heartbeat_threads[name]

    def stop_all_heartbeats(self):
        """Stop all heartbeat threads."""
        for name in list(self._stop_events.keys()):
            self.stop_heartbeat(name)


class RegistryLockError(Exception):
    """Raised when lock cannot be acquired."""
    pass
```

---

## Local Registry Manager

```python
# src/madsci_common/madsci/common/registry/local_registry.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from filelock import FileLock  # Cross-platform file locking

from madsci.common.types.registry_types import LocalRegistry, RegistryEntry
from madsci.common.utils import new_ulid_str
from .lock_manager import LockManager, RegistryLockError


class LocalRegistryManager:
    """Manages the local registry file."""

    FILE_LOCK_TIMEOUT = 5  # seconds

    def __init__(
        self,
        registry_path: Path = None,
        lock_manager: LockManager = None,
    ):
        self.registry_path = registry_path or self._default_path()
        self.lock_manager = lock_manager or LockManager()
        self._file_lock = FileLock(str(self.registry_path) + ".lock")

    @staticmethod
    def _default_path() -> Path:
        """Get default registry path for this platform."""
        return Path.home() / ".madsci" / "registry.json"

    def _ensure_directory(self):
        """Ensure registry directory exists."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> LocalRegistry:
        """Read registry from file."""
        if not self.registry_path.exists():
            return LocalRegistry()

        with open(self.registry_path) as f:
            data = json.load(f)
        return LocalRegistry.model_validate(data)

    def _write(self, registry: LocalRegistry):
        """Write registry to file."""
        self._ensure_directory()
        registry.updated_at = datetime.utcnow()

        with open(self.registry_path, "w") as f:
            json.dump(registry.model_dump(mode="json"), f, indent=2, default=str)

    def resolve(
        self,
        name: str,
        component_type: str,
        metadata: dict = None,
        acquire_lock: bool = True,
    ) -> str:
        """Resolve a name to an ID, creating if necessary.

        Args:
            name: Component name
            component_type: Type of component (node, manager, etc.)
            metadata: Optional metadata to store
            acquire_lock: Whether to acquire a lock (default: True)

        Returns:
            The component ID (ULID)

        Raises:
            RegistryLockError: If lock cannot be acquired
        """
        with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
            registry = self._read()

            if name in registry.entries:
                entry = registry.entries[name]

                if acquire_lock:
                    entry = self.lock_manager.acquire(entry)

                entry.last_seen = datetime.utcnow()
                if metadata:
                    entry.metadata.update(metadata)

                registry.entries[name] = entry
                self._write(registry)

                if acquire_lock:
                    self.lock_manager.start_heartbeat(name, self)

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

            return entry.id

    def lookup(self, name: str) -> Optional[str]:
        """Look up an ID by name without acquiring lock.

        Returns:
            The component ID, or None if not found
        """
        with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
            registry = self._read()
            entry = registry.entries.get(name)
            return entry.id if entry else None

    def refresh_lock(self, name: str):
        """Refresh the lock for an entry."""
        with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
            registry = self._read()

            if name not in registry.entries:
                raise RegistryLockError(f"Entry '{name}' not found")

            entry = registry.entries[name]
            entry = self.lock_manager.refresh(entry)
            registry.entries[name] = entry
            self._write(registry)

    def release(self, name: str):
        """Release lock and stop heartbeat for an entry."""
        self.lock_manager.stop_heartbeat(name)

        with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
            registry = self._read()

            if name in registry.entries:
                entry = registry.entries[name]
                entry = self.lock_manager.release(entry)
                registry.entries[name] = entry
                self._write(registry)

    def list_entries(
        self,
        component_type: str = None,
        include_stale: bool = False,
    ) -> list[tuple[str, RegistryEntry]]:
        """List all entries in the registry.

        Args:
            component_type: Filter by type
            include_stale: Include entries with expired locks

        Returns:
            List of (name, entry) tuples
        """
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

    def clean_stale(
        self,
        older_than_days: int = 7,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove stale entries from registry.

        Args:
            older_than_days: Remove entries not seen in this many days
            dry_run: If True, only return what would be removed

        Returns:
            List of removed entry names
        """
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(days=older_than_days)

        with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
            registry = self._read()

            stale = [
                name for name, entry in registry.entries.items()
                if entry.last_seen < threshold and not entry.is_locked()
            ]

            if not dry_run:
                for name in stale:
                    del registry.entries[name]
                self._write(registry)

            return stale

    def export(self) -> dict:
        """Export registry as dictionary."""
        with self._file_lock.acquire(timeout=self.FILE_LOCK_TIMEOUT):
            registry = self._read()
            return registry.model_dump(mode="json")

    def import_entries(
        self,
        data: dict,
        merge: bool = True,
    ):
        """Import entries from dictionary.

        Args:
            data: Registry data to import
            merge: If True, merge with existing. If False, replace.
        """
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
```

---

## Lab Registry (API)

The Lab Manager provides registry API endpoints for distributed coordination.

### API Endpoints

```
GET    /registry/entries                 List all entries
GET    /registry/entries/{name}          Get entry by name
POST   /registry/entries/{name}          Create or update entry
DELETE /registry/entries/{name}          Delete entry
POST   /registry/entries/{name}/lock     Acquire lock
POST   /registry/entries/{name}/unlock   Release lock
POST   /registry/entries/{name}/heartbeat  Refresh lock
GET    /registry/resolve/{name}          Quick name-to-ID lookup
POST   /registry/sync                    Sync local registry to lab
```

### Implementation

```python
# src/madsci_squid/madsci/squid/registry_endpoints.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from madsci.common.types.registry_types import RegistryEntry, RegistryLock
from madsci.common.utils import new_ulid_str

router = APIRouter(prefix="/registry", tags=["registry"])


class CreateEntryRequest(BaseModel):
    component_type: str
    metadata: dict = {}
    acquire_lock: bool = False
    lock_holder_host: Optional[str] = None
    lock_holder_pid: Optional[int] = None
    lock_holder_instance: Optional[str] = None


class ResolveResponse(BaseModel):
    name: str
    id: str
    component_type: str
    is_new: bool


@router.get("/entries")
async def list_entries(
    component_type: Optional[str] = None,
    include_stale: bool = False,
) -> list[dict]:
    """List all registry entries."""
    # Implementation uses lab's registry storage
    pass


@router.get("/entries/{name}")
async def get_entry(name: str) -> RegistryEntry:
    """Get a specific registry entry."""
    pass


@router.post("/entries/{name}")
async def create_or_update_entry(
    name: str,
    request: CreateEntryRequest,
) -> RegistryEntry:
    """Create or update a registry entry."""
    pass


@router.delete("/entries/{name}")
async def delete_entry(name: str):
    """Delete a registry entry."""
    pass


@router.post("/entries/{name}/lock")
async def acquire_lock(
    name: str,
    holder_host: str,
    holder_pid: int,
    holder_instance: str,
) -> RegistryEntry:
    """Acquire lock on an entry."""
    pass


@router.post("/entries/{name}/unlock")
async def release_lock(
    name: str,
    holder_instance: str,
) -> RegistryEntry:
    """Release lock on an entry."""
    pass


@router.post("/entries/{name}/heartbeat")
async def refresh_heartbeat(
    name: str,
    holder_instance: str,
) -> RegistryEntry:
    """Refresh lock heartbeat."""
    pass


@router.get("/resolve/{name}")
async def resolve_name(name: str) -> ResolveResponse:
    """Quick name-to-ID lookup."""
    pass


@router.post("/sync")
async def sync_from_local(
    entries: dict[str, RegistryEntry],
) -> dict:
    """Sync local registry entries to lab registry.

    Returns dict of {name: "created" | "updated" | "conflict"}
    """
    pass
```

---

## Identity Resolver

The high-level interface that components use to get their identity.

```python
# src/madsci_common/madsci/common/registry/identity_resolver.py
from typing import Optional
from pydantic import AnyUrl

from .local_registry import LocalRegistryManager
from .lock_manager import LockManager, RegistryLockError


class IdentityResolver:
    """Resolves component names to IDs with distributed coordination.

    Usage:
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
        local_registry: LocalRegistryManager = None,
    ):
        self.lab_url = lab_url
        self.local_registry = local_registry or LocalRegistryManager()
        self._lab_client = None

    @property
    def lab_client(self):
        """Lazy-initialize lab client."""
        if self._lab_client is None and self.lab_url:
            from madsci.client import LabClient
            self._lab_client = LabClient(str(self.lab_url))
        return self._lab_client

    def resolve(
        self,
        name: str,
        component_type: str,
        metadata: dict = None,
    ) -> str:
        """Resolve a name to an ID.

        Resolution order:
        1. Check local registry
        2. If lab available, check lab registry
        3. If not found, generate new ID
        4. Acquire lock
        5. Sync to lab if available

        Args:
            name: Component name
            component_type: Type (node, manager, etc.)
            metadata: Optional metadata

        Returns:
            Component ID (ULID)

        Raises:
            RegistryLockError: If name is already locked by another process
        """
        # Try local registry first
        try:
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
                except Exception:
                    # Lab sync failure is non-fatal in standalone mode
                    pass

            return local_id

        except RegistryLockError:
            # Lock conflict - check if lab has different info
            if self.lab_client:
                return self._resolve_from_lab(name, component_type, metadata)
            raise

    def _resolve_from_lab(self, name: str, component_type: str, metadata: dict) -> str:
        """Resolve from lab registry (when local fails)."""
        # Query lab registry
        # If found, try to acquire lock there
        # Sync back to local
        pass

    def _sync_to_lab(self, name: str, id: str, component_type: str, metadata: dict):
        """Sync entry to lab registry."""
        pass

    def lookup(self, name: str) -> Optional[str]:
        """Look up ID without acquiring lock."""
        # Check local first
        local_id = self.local_registry.lookup(name)
        if local_id:
            return local_id

        # Check lab if available
        if self.lab_client:
            try:
                response = self.lab_client.get(f"/registry/resolve/{name}")
                return response.get("id")
            except Exception:
                pass

        return None

    def release(self, name: str):
        """Release lock on a name."""
        self.local_registry.release(name)

        # Also release on lab if available
        if self.lab_client:
            try:
                instance_id = self.local_registry.lock_manager.instance_id
                self.lab_client.post(
                    f"/registry/entries/{name}/unlock",
                    {"holder_instance": instance_id}
                )
            except Exception:
                pass

    def release_all(self):
        """Release all locks held by this resolver."""
        self.local_registry.lock_manager.stop_all_heartbeats()
```

---

## Integration with Components

### Node Integration

```python
# In AbstractNode.__init__
from madsci.common.registry import IdentityResolver

class AbstractNode:
    def __init__(self, ...):
        # Get identity from registry instead of definition file
        self.resolver = IdentityResolver(lab_url=self.config.lab_url)

        self.node_id = self.resolver.resolve(
            name=self.node_name,
            component_type="node",
            metadata={
                "module_name": self.module_name,
                "module_version": str(self.module_version),
            },
        )

    def shutdown(self):
        """Release identity on shutdown."""
        self.resolver.release(self.node_name)
```

### Manager Integration

```python
# In AbstractManagerBase.__init__
from madsci.common.registry import IdentityResolver

class AbstractManagerBase:
    def __init__(self, ...):
        self.resolver = IdentityResolver(lab_url=self.settings.lab_url)

        self.manager_id = self.resolver.resolve(
            name=self.manager_name,
            component_type="manager",
            metadata={
                "manager_type": self.manager_type,
            },
        )
```

---

## CLI Commands

See CLI design document for full command specifications.

```bash
# List all registered components
madsci registry list

# Resolve a name to ID
madsci registry resolve liquidhandler_1

# Rename a component
madsci registry rename old_name new_name

# Clean stale entries
madsci registry clean --older-than 7d

# Export registry
madsci registry export > registry-backup.json

# Import registry
madsci registry import registry-backup.json --merge
```

---

## Docker Considerations

### Volume Mounting

To share registry between host and containers:

```yaml
# compose.yaml
services:
  liquidhandler_1:
    volumes:
      - ~/.madsci:/app/.madsci  # Share registry
```

### Hostname in Locks

Inside Docker, `socket.gethostname()` returns the container ID. For better identification:

```python
# Use container name if available
hostname = os.environ.get("HOSTNAME", socket.gethostname())
container_name = os.environ.get("CONTAINER_NAME", hostname)
```

```yaml
# compose.yaml
services:
  liquidhandler_1:
    container_name: liquidhandler_1
    environment:
      - CONTAINER_NAME=liquidhandler_1
```

---

## Error Handling

### Lock Conflict

```python
try:
    node_id = resolver.resolve("liquidhandler_1", "node")
except RegistryLockError as e:
    print(f"Cannot start: {e}")
    print("Another instance may be running. Check with: madsci registry list")
    sys.exit(1)
```

### User-Friendly Error Message

```
✗ Cannot start liquidhandler_1

  This name is already in use by another process.

  Holder: lab-workstation-1 (PID 12345)
  Locked since: 2026-02-07 15:30:00
  Expires: 2026-02-07 15:30:30

  Possible causes:
    • Another instance is running
    • Previous instance crashed without releasing lock

  Solutions:
    • Wait for lock to expire (30 seconds)
    • Stop the other instance
    • Use 'madsci registry clean' to remove stale locks
```

---

## Migration from Definition Files

The migration tool will:
1. Scan for existing definition files
2. Extract IDs from them
3. Register in the new registry
4. Update component code to use resolver

See Migration Tool design document for details.

---

## Testing Strategy

```python
# tests/registry/test_local_registry.py
import tempfile
from pathlib import Path
from madsci.common.registry import LocalRegistryManager, LockManager

def test_resolve_creates_new_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = LocalRegistryManager(
            registry_path=Path(tmpdir) / "registry.json"
        )

        id1 = registry.resolve("test_node", "node")
        assert id1 is not None
        assert len(id1) == 26  # ULID length

def test_resolve_returns_same_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = LocalRegistryManager(
            registry_path=Path(tmpdir) / "registry.json"
        )

        id1 = registry.resolve("test_node", "node")
        id2 = registry.resolve("test_node", "node")
        assert id1 == id2

def test_lock_prevents_duplicate():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry1 = LocalRegistryManager(
            registry_path=Path(tmpdir) / "registry.json",
            lock_manager=LockManager(),
        )
        registry2 = LocalRegistryManager(
            registry_path=Path(tmpdir) / "registry.json",
            lock_manager=LockManager(),  # Different instance
        )

        # First resolver gets the lock
        id1 = registry1.resolve("test_node", "node")

        # Second resolver should fail
        with pytest.raises(RegistryLockError):
            registry2.resolve("test_node", "node")
```

---

## Dependencies

```toml
# Add to madsci_common/pyproject.toml
dependencies = [
    # ... existing ...
    "filelock>=3.12.0",  # Cross-platform file locking
]
```

---

## Design Decisions

The following decisions have been made based on review:

1. **Lab registry storage**: Use a **MongoDB collection** for the lab-level registry. This is consistent with how other managers store state (e.g., workcell state) and provides good query capabilities for the registry API.

2. **Lock TTL tuning**: **30 seconds is the default**, but make it configurable via settings. Some environments (slow networks, heavy loads) may need longer TTLs. Add a `REGISTRY_LOCK_TTL` environment variable.

3. **Multi-lab support**: **Not supported at this time.** The local registry (`~/.madsci/registry.json`) serves a single lab. Users running multiple labs should use separate user accounts or explicitly manage registry paths.

4. **Encryption**: **Not required at this time.** The registry contains component names and IDs, not secrets. If sensitive metadata needs to be stored later, encryption can be added.

5. **Audit log**: **Yes, log all lock acquisitions and releases.** This aids debugging of "component already locked" issues. Use the EventClient to log these as structured events with `event_type=EventType.REGISTRY_LOCK_ACQUIRED` / `REGISTRY_LOCK_RELEASED`.

---

## Rename Operation

**IMPORTANT**: The registry must support renaming components. This is needed when:
- Refactoring a lab (renaming nodes for clarity)
- Fixing typos in component names
- Standardizing naming conventions

### CLI Command

```bash
madsci registry rename <old_name> <new_name>
```

**Options:**
- `--force` - Rename even if the old name is currently locked (steal the lock)

**Behavior:**
1. Look up the entry for `old_name`
2. Verify `new_name` doesn't already exist (error if it does)
3. Create new entry with `new_name` pointing to the same ID
4. Delete the entry for `old_name`
5. Update the lab registry if connected

### Implementation

```python
# In LocalRegistryManager
def rename(self, old_name: str, new_name: str, force: bool = False) -> str:
    """Rename a registry entry.

    Args:
        old_name: Current component name
        new_name: New component name
        force: If True, steal lock if old_name is locked

    Returns:
        The component ID (unchanged)

    Raises:
        RegistryError: If old_name doesn't exist or new_name already exists
        RegistryLockError: If old_name is locked and force=False
    """
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

        return entry.id
```

### API Endpoint

```
POST /registry/entries/{old_name}/rename
Body: {"new_name": "new_component_name"}
```
