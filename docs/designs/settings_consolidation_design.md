# MADSci Settings Consolidation Design Document

**Status**: Draft
**Date**: 2026-02-07
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for consolidating MADSci's configuration system. Currently, configuration is split between "Definition" files (YAML) and "Settings" classes (Pydantic Settings). This document describes how to unify these into a single, coherent configuration system.

## Problem Statement

### Current State

Configuration is currently split across two parallel systems:

**Definition Files (YAML)**:
- `*.manager.yaml` - Manager definitions
- `*.node.yaml` - Node definitions
- `*.workflow.yaml` - Workflow definitions

**Settings Classes (Pydantic Settings)**:
- `*ManagerSettings` - Manager runtime configuration
- `NodeConfig` / `RestNodeConfig` - Node configuration

### Example of Current Confusion

```python
# Current: Two separate classes for one manager
class WorkcellManagerSettings(ManagerSettings):
    """Runtime configuration - from env vars."""
    server_url: AnyUrl = "http://localhost:8005"
    manager_definition: PathLike = "workcell.manager.yaml"  # Points to definition
    redis_host: str = "localhost"
    scheduler_update_interval: float = 5.0

class WorkcellManagerDefinition(ManagerDefinition):
    """Identity and structure - from YAML file."""
    name: str
    manager_id: str  # ID is in here!
    nodes: dict[str, AnyUrl]  # But so is structural config!
```

**Problems**:
1. Users must understand two parallel config systems
2. Unclear which config goes where
3. ID is in definition, but should be from registry
4. Structural config (nodes list) is in definition, but could be in settings
5. Definition files are hand-edited YAML, error-prone

### Goals

1. **Single source of truth**: One configuration system, not two
2. **ID from registry**: Component identity comes from the ID Registry
3. **Env-first configuration**: Everything configurable via environment variables
4. **Optional file config**: YAML/TOML files for convenience, not required
5. **Clear documentation**: Easy to understand what goes where

---

## New Architecture

### Design Principles

1. **Settings are the primary configuration mechanism**
2. **Definitions are deprecated and replaced by**:
   - ID Registry (for identity)
   - Settings (for structural config)
   - Templates (for scaffolding new components)
3. **Everything can be configured via environment variables**
4. **File-based config (YAML/TOML) is optional convenience**

### Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Configuration Priority                               │
│                         (highest to lowest)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. CLI Arguments                                                            │
│     └─ madsci start manager --port 8005                                     │
│                                                                              │
│  2. Environment Variables                                                    │
│     └─ WORKCELL_SERVER_PORT=8005                                            │
│                                                                              │
│  3. .env File (in working directory)                                        │
│     └─ WORKCELL_SERVER_PORT=8005                                            │
│                                                                              │
│  4. Settings File (YAML/TOML)                                               │
│     └─ ~/.madsci/config.yaml or ./madsci.yaml                               │
│                                                                              │
│  5. Default Values (in code)                                                │
│     └─ class WorkcellSettings: server_port: int = 8005                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Consolidated Settings Classes

### Base Settings

```python
# src/madsci_common/madsci/common/types/base_types.py
from pathlib import Path
from typing import Optional
from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MadsciBaseSettings(BaseSettings):
    """Base settings class for all MADSci components.

    Supports configuration from:
    - Environment variables (with prefix)
    - .env files
    - YAML/TOML config files
    - CLI arguments (via Click)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    @classmethod
    def from_file(cls, path: Path) -> "MadsciBaseSettings":
        """Load settings from YAML or TOML file."""
        import yaml
        import tomllib

        if path.suffix in (".yaml", ".yml"):
            with open(path) as f:
                data = yaml.safe_load(f)
        elif path.suffix == ".toml":
            with open(path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")

        return cls(**data)
```

### Manager Settings (Consolidated)

```python
# src/madsci_common/madsci/common/types/manager_types.py
from typing import Optional
from pydantic import AnyUrl, Field
from madsci.common.types.base_types import MadsciBaseSettings


class ManagerSettings(MadsciBaseSettings):
    """Base settings for all managers.

    Replaces ManagerDefinition + old ManagerSettings.
    """

    # Identity (resolved from registry by name)
    name: str = Field(
        description="Manager name (used for ID registry lookup)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description"
    )

    # Server configuration
    server_host: str = Field(
        default="0.0.0.0",
        description="Host to bind server to"
    )
    server_port: int = Field(
        description="Port to bind server to"
    )

    # Lab connection
    lab_url: Optional[AnyUrl] = Field(
        default=None,
        description="URL of lab manager (for registry sync)"
    )

    @property
    def server_url(self) -> str:
        """Compute server URL from host and port."""
        return f"http://{self.server_host}:{self.server_port}/"


class WorkcellManagerSettings(ManagerSettings):
    """Settings for Workcell Manager.

    Replaces WorkcellManagerDefinition + old WorkcellManagerSettings.
    """

    model_config = SettingsConfigDict(
        env_prefix="WORKCELL_",
    )

    # Identity
    name: str = "workcell_manager"
    server_port: int = 8005

    # Workcell structure (was in definition)
    nodes: dict[str, AnyUrl] = Field(
        default_factory=dict,
        description="Map of node names to URLs"
    )

    # Redis connection
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Scheduler configuration
    scheduler_type: str = "default"
    scheduler_update_interval: float = 5.0

    # Database
    mongo_db_url: AnyUrl = "mongodb://localhost:27017/"
    database_name: str = "madsci_workcell"


class EventManagerSettings(ManagerSettings):
    """Settings for Event Manager."""

    model_config = SettingsConfigDict(
        env_prefix="EVENT_",
    )

    name: str = "event_manager"
    server_port: int = 8001

    mongo_db_url: AnyUrl = "mongodb://localhost:27017/"
    database_name: str = "madsci_events"
    collection_name: str = "events"

    # Retention
    max_events: Optional[int] = None
    retention_days: Optional[int] = None


class ResourceManagerSettings(ManagerSettings):
    """Settings for Resource Manager."""

    model_config = SettingsConfigDict(
        env_prefix="RESOURCE_",
    )

    name: str = "resource_manager"
    server_port: int = 8003

    db_url: str = "postgresql://localhost:5432/madsci_resources"

    # Default templates (was in definition)
    default_templates: list[str] = Field(
        default_factory=list,
        description="Names of templates to create on startup"
    )


class LocationManagerSettings(ManagerSettings):
    """Settings for Location Manager."""

    model_config = SettingsConfigDict(
        env_prefix="LOCATION_",
    )

    name: str = "location_manager"
    server_port: int = 8006

    mongo_db_url: AnyUrl = "mongodb://localhost:27017/"
    database_name: str = "madsci_locations"

    # Initial locations (was in definition)
    locations: dict = Field(
        default_factory=dict,
        description="Initial location definitions"
    )


class LabManagerSettings(ManagerSettings):
    """Settings for Lab Manager (Squid)."""

    model_config = SettingsConfigDict(
        env_prefix="LAB_",
    )

    name: str = "lab_manager"
    server_port: int = 8000

    # Connected managers (was in definition)
    event_manager_url: Optional[AnyUrl] = "http://localhost:8001/"
    experiment_manager_url: Optional[AnyUrl] = "http://localhost:8002/"
    resource_manager_url: Optional[AnyUrl] = "http://localhost:8003/"
    data_manager_url: Optional[AnyUrl] = "http://localhost:8004/"
    workcell_manager_url: Optional[AnyUrl] = "http://localhost:8005/"
    location_manager_url: Optional[AnyUrl] = "http://localhost:8006/"

    # Dashboard
    dashboard_enabled: bool = True
    dashboard_dir: Optional[str] = None
```

### Node Settings (Consolidated)

```python
# src/madsci_common/madsci/common/types/node_types.py
from typing import Optional, Literal
from pydantic import AnyUrl, Field
from madsci.common.types.base_types import MadsciBaseSettings


class NodeSettings(MadsciBaseSettings):
    """Base settings for all nodes.

    Replaces NodeDefinition + NodeConfig.
    """

    model_config = SettingsConfigDict(
        env_prefix="NODE_",
    )

    # Identity (resolved from registry by name)
    name: str = Field(
        description="Node name (used for ID registry lookup)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description"
    )

    # Node type
    node_type: Literal["device", "compute", "human"] = "device"

    # Module info
    module_name: str = Field(
        description="Name of the node module"
    )
    module_version: str = "0.0.1"

    # Server configuration
    server_host: str = "0.0.0.0"
    server_port: int = 2000

    @property
    def server_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}/"

    # Lab connection
    lab_url: Optional[AnyUrl] = None
    workcell_url: Optional[AnyUrl] = None

    # Behavior
    simulate: bool = Field(
        default=False,
        description="Run in simulation mode"
    )


class RestNodeSettings(NodeSettings):
    """Settings for REST-based nodes."""

    # REST-specific settings
    cors_enabled: bool = True
    cors_origins: list[str] = ["*"]

    # Timeouts
    action_timeout: float = 300.0  # 5 minutes
    shutdown_timeout: float = 30.0
```

---

## Environment Variable Naming

### Convention

```
{PREFIX}_{FIELD_NAME}
```

| Component | Prefix | Example |
|-----------|--------|----------|
| Lab Manager | `LAB_` | `LAB_SERVER_PORT=8000` |
| Event Manager | `EVENT_` | `EVENT_MONGO_DB_URL=mongodb://...` |
| Experiment Manager | `EXPERIMENT_` | `EXPERIMENT_SERVER_PORT=8002` |
| Resource Manager | `RESOURCE_` | `RESOURCE_DB_URL=postgresql://...` |
| Data Manager | `DATA_` | `DATA_SERVER_PORT=8004` |
| Workcell Manager | `WORKCELL_` | `WORKCELL_NODES={"lh1":"http://..."}` |
| Location Manager | `LOCATION_` | `LOCATION_SERVER_PORT=8006` |
| Nodes | `NODE_` | `NODE_NAME=liquidhandler_1` |

### Nested Values

For dict/list fields, use JSON encoding:

```bash
# Dict field
WORKCELL_NODES='{"liquidhandler_1": "http://localhost:2000/"}'

# List field
RESOURCE_DEFAULT_TEMPLATES='["plate_96", "tube_rack"]'
```

Or use double-underscore for nested access:

```bash
# Nested dict
WORKCELL_NODES__LIQUIDHANDLER_1=http://localhost:2000/
```

---

## Configuration File Format

### YAML Format

```yaml
# ~/.madsci/config.yaml or ./madsci.yaml

# Lab-level settings
lab:
  name: "My Research Lab"
  description: "Automated chemistry synthesis lab"

# Manager settings
managers:
  workcell:
    nodes:
      liquidhandler_1: "http://localhost:2000/"
      liquidhandler_2: "http://localhost:2001/"
      robotarm_1: "http://localhost:2002/"
    redis_host: "localhost"
    scheduler_update_interval: 5.0

  event:
    mongo_db_url: "mongodb://localhost:27017/"
    retention_days: 30

  resource:
    db_url: "postgresql://localhost:5432/madsci_resources"
    default_templates:
      - plate_96
      - tube_rack

# Node settings (can also be in separate files)
nodes:
  liquidhandler_1:
    module_name: "liquidhandler"
    server_port: 2000
    simulate: false
```

### TOML Format

```toml
# madsci.toml

[lab]
name = "My Research Lab"
description = "Automated chemistry synthesis lab"

[managers.workcell]
redis_host = "localhost"
scheduler_update_interval = 5.0

[managers.workcell.nodes]
liquidhandler_1 = "http://localhost:2000/"
liquidhandler_2 = "http://localhost:2001/"

[managers.event]
mongo_db_url = "mongodb://localhost:27017/"
retention_days = 30

[nodes.liquidhandler_1]
module_name = "liquidhandler"
server_port = 2000
simulate = false
```

---

## Migration from Definitions

### Mapping Table

| Old (Definition) | New (Settings) |
|------------------|----------------|
| `manager_id` | From ID Registry |
| `name` | `name` |
| `description` | `description` |
| `nodes` (workcell) | `nodes` |
| `locations` (location) | `locations` |
| `default_templates` | `default_templates` |

### Example Migration

**Before (Definition File)**:
```yaml
# managers/example_workcell.manager.yaml
name: Example Workcell
manager_type: workcell_manager
manager_id: 01JK706A23XYZFT4SA5M0VQT35H
description: Workcell for the example lab
nodes:
  liquidhandler_1: http://localhost:2000/
  robotarm_1: http://localhost:2002/
```

**After (Environment Variables)**:
```bash
WORKCELL_NAME=example_workcell
WORKCELL_DESCRIPTION="Workcell for the example lab"
WORKCELL_NODES='{"liquidhandler_1": "http://localhost:2000/", "robotarm_1": "http://localhost:2002/"}'
# manager_id is resolved from registry by name
```

**After (Config File)**:
```yaml
# madsci.yaml
managers:
  workcell:
    name: example_workcell
    description: "Workcell for the example lab"
    nodes:
      liquidhandler_1: "http://localhost:2000/"
      robotarm_1: "http://localhost:2002/"
```

---

## Manager Initialization (Updated)

```python
# src/madsci_common/madsci/common/manager_base.py
from typing import Generic, TypeVar
from madsci.common.registry import IdentityResolver
from madsci.common.types.manager_types import ManagerSettings

SettingsT = TypeVar("SettingsT", bound=ManagerSettings)


class AbstractManagerBase(Generic[SettingsT]):
    """Base class for all managers.

    Uses consolidated Settings (no separate Definition).
    """

    SETTINGS_CLASS: type[SettingsT]  # Set by subclass

    def __init__(self, settings: SettingsT = None):
        # Load settings (from env, files, or provided)
        self.settings = settings or self.SETTINGS_CLASS()

        # Resolve identity from registry
        self.resolver = IdentityResolver(lab_url=self.settings.lab_url)
        self.manager_id = self.resolver.resolve(
            name=self.settings.name,
            component_type="manager",
            metadata={"manager_type": self.manager_type},
        )

        # Initialize server, etc.
        self._init_server()

    @property
    def manager_name(self) -> str:
        return self.settings.name

    @property
    def manager_type(self) -> str:
        """Override in subclass."""
        raise NotImplementedError


class WorkcellManager(AbstractManagerBase[WorkcellManagerSettings]):
    """Workcell Manager implementation."""

    SETTINGS_CLASS = WorkcellManagerSettings

    @property
    def manager_type(self) -> str:
        return "workcell_manager"

    def __init__(self, settings: WorkcellManagerSettings = None):
        super().__init__(settings)

        # Access structural config directly from settings
        self.nodes = self.settings.nodes
```

---

## Node Initialization (Updated)

```python
# src/madsci_node_module/madsci/node_module/abstract_node.py
from madsci.common.registry import IdentityResolver
from madsci.common.types.node_types import NodeSettings


class AbstractNode:
    """Base class for all nodes.

    Uses consolidated Settings (no separate Definition).
    """

    SETTINGS_CLASS: type[NodeSettings] = NodeSettings

    def __init__(self, settings: NodeSettings = None):
        # Load settings
        self.settings = settings or self.SETTINGS_CLASS()

        # Resolve identity from registry
        self.resolver = IdentityResolver(lab_url=self.settings.lab_url)
        self.node_id = self.resolver.resolve(
            name=self.settings.name,
            component_type="node",
            metadata={
                "module_name": self.settings.module_name,
                "module_version": self.settings.module_version,
                "node_type": self.settings.node_type,
            },
        )

    @property
    def node_name(self) -> str:
        return self.settings.name

    def shutdown(self):
        """Release identity on shutdown."""
        self.resolver.release(self.node_name)
```

---

## Deprecation Strategy

### Phase 1: Support Both (Current + New)

```python
class AbstractManagerBase:
    def __init__(self, settings=None, definition=None):
        if definition is not None:
            import warnings
            warnings.warn(
                "Definition files are deprecated. Use Settings instead. "
                "Run 'madsci migrate' to convert.",
                DeprecationWarning,
                stacklevel=2,
            )
            # Convert definition to settings
            settings = self._definition_to_settings(definition)

        self.settings = settings or self.SETTINGS_CLASS()
```

### Phase 2: Emit Warnings

When definition file is detected:
```
⚠ Deprecated: Loading configuration from managers/example_workcell.manager.yaml
  Definition files are deprecated and will be removed in v0.4.0.
  Run 'madsci migrate convert managers/example_workcell.manager.yaml' to convert.
```

### Phase 3: Remove Support

In v0.4.0 or later, remove definition file loading entirely.

---

## Docker Compose Updates

With settings consolidation, Docker Compose becomes simpler:

```yaml
# compose.yaml
services:
  workcell_manager:
    image: madsci:latest
    command: python -m madsci.workcell_manager.workcell_server
    environment:
      - WORKCELL_NAME=example_workcell
      - WORKCELL_SERVER_PORT=8005
      - WORKCELL_REDIS_HOST=redis
      - WORKCELL_MONGO_DB_URL=mongodb://mongodb:27017/
      - WORKCELL_NODES={"liquidhandler_1": "http://liquidhandler_1:2000/"}
    ports:
      - "8005:8005"
    depends_on:
      - redis
      - mongodb

  liquidhandler_1:
    image: madsci:latest
    command: python example_modules/liquidhandler.py
    environment:
      - NODE_NAME=liquidhandler_1
      - NODE_SERVER_PORT=2000
      - NODE_MODULE_NAME=liquidhandler
      - NODE_LAB_URL=http://lab_manager:8000/
    ports:
      - "2000:2000"
```

No more volume mounts for definition files!

---

## Benefits of Consolidation

| Before | After |
|--------|-------|
| Two config systems to learn | One unified system |
| Hand-edit YAML files | Environment variables or config files |
| ID in definition file | ID from registry (automatic) |
| Scattered configuration | Centralized in Settings |
| Hard to override in Docker | Easy with env vars |
| Different patterns for managers/nodes | Consistent pattern everywhere |

---

## Testing

```python
# tests/settings/test_consolidated_settings.py
import os
import pytest
from madsci.common.types.manager_types import WorkcellManagerSettings


class TestWorkcellSettings:
    def test_default_values(self):
        settings = WorkcellManagerSettings(name="test_workcell")
        assert settings.server_port == 8005
        assert settings.redis_host == "localhost"

    def test_from_env_vars(self, monkeypatch):
        monkeypatch.setenv("WORKCELL_NAME", "my_workcell")
        monkeypatch.setenv("WORKCELL_SERVER_PORT", "9005")
        monkeypatch.setenv("WORKCELL_REDIS_HOST", "redis.example.com")

        settings = WorkcellManagerSettings()
        assert settings.name == "my_workcell"
        assert settings.server_port == 9005
        assert settings.redis_host == "redis.example.com"

    def test_nodes_from_json_env(self, monkeypatch):
        monkeypatch.setenv("WORKCELL_NAME", "test")
        monkeypatch.setenv(
            "WORKCELL_NODES",
            '{"lh1": "http://localhost:2000/", "lh2": "http://localhost:2001/"}'
        )

        settings = WorkcellManagerSettings()
        assert "lh1" in settings.nodes
        assert settings.nodes["lh1"] == "http://localhost:2000/"
```

---

## Design Decisions

The following decisions have been made based on review:

**Important Note**: We will continue using **Pydantic Settings** as the foundation for all configuration management. The existing `MadsciBaseSettings` pattern is well-established and works well. This consolidation is about unifying Definition files INTO the Settings system, not replacing Settings.

1. **Config file location**: Support **both** locations with clear precedence:
   - `./madsci.yaml` or `./madsci.toml` (project-level, higher priority)
   - `~/.madsci/config.toml` (user-level defaults)
   - Environment variables override both

2. **Config file format**: Support **YAML and TOML**. Pydantic Settings already supports multiple sources. Default examples will use TOML for user config and YAML for project config (matching existing conventions).

3. **Secrets handling**: Use Pydantic Settings' built-in secrets file support (`secrets_dir` setting). No integration with external secret managers (Vault, etc.) at this time.

4. **Validation timing**: **Validate on load.** If configuration is invalid, fail fast with a clear error message before starting any operations. This prevents experiments from starting with invalid config and failing mid-run.

5. **Hot reload**: **Not supported at this time.** Settings are loaded once at startup. Changing configuration requires restarting the component. This keeps the implementation simple and avoids subtle bugs from mid-run config changes.

---

## Settings Export Capability

Based on feedback, the system should support exporting current settings/state from running components.

### Use Cases

1. **Backup**: Export current configuration for disaster recovery
2. **Replication**: Copy settings from one lab to another
3. **Debugging**: Inspect what settings a component is actually using
4. **Documentation**: Generate configuration examples from running systems

### CLI Commands

```bash
# Export settings from a running manager
madsci export settings --manager workcell > workcell-settings.toml

# Export settings from a running node
madsci export settings --node liquidhandler_1 > lh1-settings.toml

# Export all settings from a lab
madsci export settings --all > lab-settings.toml

# Export as different formats
madsci export settings --manager workcell --format yaml > workcell-settings.yaml
madsci export settings --manager workcell --format env > workcell.env
```

### API Endpoints

Each manager/node will expose an endpoint to export its settings:

```
GET /settings
    Returns: Current settings as JSON (excluding secrets)

GET /settings?format=toml
    Returns: Current settings as TOML

GET /settings?format=yaml
    Returns: Current settings as YAML

GET /settings?include_defaults=false
    Returns: Only non-default settings
```

### Implementation

```python
# Add to AbstractManagerBase
def get_settings_export(self, include_defaults: bool = True) -> dict:
    """Export current settings for backup/replication.

    Args:
        include_defaults: If True, include fields with default values

    Returns:
        Settings as a dictionary (secrets redacted)
    """
    data = self.settings.model_dump()

    # Redact sensitive fields
    sensitive_fields = ['password', 'secret', 'token', 'key', 'credential']
    for field in list(data.keys()):
        if any(s in field.lower() for s in sensitive_fields):
            data[field] = '***REDACTED***'

    if not include_defaults:
        # Only include fields that differ from defaults
        defaults = type(self.settings)().model_dump()
        data = {k: v for k, v in data.items() if data.get(k) != defaults.get(k)}

    return data

# Add endpoint
@router.get("/settings")
async def get_settings(
    format: str = "json",
    include_defaults: bool = True
) -> Response:
    """Export current settings."""
    data = manager.get_settings_export(include_defaults)

    if format == "toml":
        import tomli_w
        content = tomli_w.dumps(data)
        return Response(content, media_type="application/toml")
    elif format == "yaml":
        import yaml
        content = yaml.dump(data, default_flow_style=False)
        return Response(content, media_type="application/x-yaml")
    else:
        return data
```

### State Export (Future)

Beyond settings, future versions may support exporting runtime state:

```bash
# Export workcell state (queued workflows, node status, etc.)
madsci export state --manager workcell > workcell-state.json

# Export resource inventory
madsci export state --manager resource > resources.json
```

This is out of scope for the initial settings consolidation but should be considered in the design.
