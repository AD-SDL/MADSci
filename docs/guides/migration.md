# Migration Guide: Definition Files to Settings + Registry

## Overview

MADSci is transitioning from YAML definition files (`*.manager.yaml`, `*.node.yaml`) to a settings-based configuration system backed by environment variables and a local ID registry.

**Timeline**:
- **v0.7.x (current)**: Definition files are deprecated but still work. New registry and settings-based configuration are available.
- **v0.8.0 (planned)**: Definition files will no longer be auto-loaded. Managers will require explicit configuration via settings/environment variables.

## Why Migrate?

Definition files have several limitations:
- **Not 12-factor compliant**: Configuration should come from the environment, not checked-in YAML files.
- **ID management is fragile**: Manager IDs are embedded in YAML and can be lost or duplicated.
- **Hard to manage at scale**: Each manager requires a separate YAML file, making distributed deployments harder to configure.

The new system provides:
- **Environment variable configuration**: All structural config can be set via env vars or `.env` files.
- **Stable ID registry**: Component IDs are tracked in `~/.madsci/registry.json`, surviving file changes.
- **Backward compatibility**: Definition files still work during the transition period.

## Quick Start

### 1. Scan Your Project

```bash
madsci migrate scan /path/to/your/lab
```

This finds all definition files and shows their migration status.

### 2. Preview the Migration

```bash
madsci migrate convert /path/to/your/lab --dry-run
```

This shows what changes would be made without modifying any files.

### 3. Apply the Migration

```bash
madsci migrate convert /path/to/your/lab --apply
```

This will:
- Create backups of all definition files (`.yaml.bak`)
- Register all component IDs in the local registry
- Generate environment variable files (`.env.<manager_type>`)
- Add deprecation markers to the original files

### 4. Verify the Migration

```bash
madsci migrate status /path/to/your/lab
```

Check that all files show as "migrated".

### 5. Finalize (Optional)

Once you've verified everything works:

```bash
madsci migrate finalize /path/to/your/lab --apply
```

This removes the deprecated definition files (backups are preserved).

## Rollback

If something goes wrong:

```bash
madsci migrate rollback /path/to/your/lab
```

This restores all files from their `.bak` backups.

## Using the ID Registry

After migration, your component IDs are stored in the registry:

```bash
# List all registered components
madsci registry list

# Look up a specific component
madsci registry resolve "Example Workcell"

# Export the registry
madsci registry export --output registry-backup.json

# Import a registry
madsci registry import registry-backup.json
```

### Registry Resolution in Managers

Managers can optionally resolve their identity from the registry at startup. Enable this with:

```bash
# In your .env file
WORKCELL_ENABLE_REGISTRY_RESOLUTION=true
WORKCELL_MANAGER_NAME="Example Workcell"
```

When enabled, the manager will:
1. Look up its ID in the registry by name
2. If found, use the registered ID (ensuring consistency across restarts)
3. If not found, generate a new ID and register it
4. Fall back to the definition file ID if resolution fails

## Configuration Equivalents

### Before (Definition YAML)

```yaml
# example_workcell.manager.yaml
name: Example Workcell
manager_type: workcell_manager
manager_id: 01JK7069DXAKAMWE0PDX6EY1PC
description: An example workcell
nodes:
  liquidhandler_1: http://localhost:2000/
  robotarm_1: http://localhost:2002/
```

### After (Environment Variables)

```bash
# .env
WORKCELL_MANAGER_NAME="Example Workcell"
WORKCELL_MANAGER_DESCRIPTION="An example workcell"
WORKCELL_ENABLE_REGISTRY_RESOLUTION=true
WORKCELL_NODES='{"liquidhandler_1": "http://localhost:2000/", "robotarm_1": "http://localhost:2002/"}'

# Manager ID is now in ~/.madsci/registry.json
```

### Structural Config Settings

Some definition fields can now be set as environment variables:

| Manager | Definition Field | Settings Equivalent |
|---------|-----------------|-------------------|
| Workcell | `nodes` | `WORKCELL_NODES` (JSON dict) |
| Location | `locations` | `LOCATION_LOCATIONS_FILE` (path to YAML) |
| Location | `transfer_capabilities` | `LOCATION_TRANSFER_CAPABILITIES_FILE` (path to YAML) |
| Resource | `default_templates` | `RESOURCE_DEFAULT_TEMPLATES_FILE` (path to YAML) |

## Backward Compatibility

During the transition:
- Definition files still work and are loaded if present
- Settings values override definition values when both exist
- The registry is additive (existing IDs are preserved)
- Deprecation warnings are emitted when definition files are loaded

## Troubleshooting

### "No manager configuration found"
Ensure either a definition file exists at the configured path, or provide configuration via environment variables.

### "Registry lock conflict"
Another process may be using the same component name. Check with `madsci registry list` and use `madsci registry clean` to remove stale entries.

### "Migration failed for file X"
Check the error details with `madsci migrate status --verbose`. Common issues:
- File permissions preventing backup creation
- Invalid YAML in the definition file
- Missing required fields
