# Migrating from Definition Files to Settings-Based Configuration

**Status**: Active deprecation (v0.7.0+)
**Removal target**: v0.8.0

## Overview

MADSci is transitioning from definition file-based configuration (YAML files
that are auto-written on startup) to explicit settings-based configuration
managed through environment variables, settings files, and CLI commands.

This guide explains what changed, why, and how to migrate.

## What Changed

### Before (v0.6.x and earlier)

- Managers auto-wrote `*.manager.yaml` definition files on every startup
- Nodes auto-wrote `*.node.yaml` and `*.info.yaml` files on every startup
- Configuration was a mix of definition files, environment variables, and code
- Secrets could end up in auto-written files without user awareness
- The "source of truth" was unclear (definition file vs. environment variable?)

### After (v0.7.0+)

- **Managers no longer auto-write definition files** on startup. They still
  *read* existing definition files (with a deprecation warning), but the
  auto-write behavior has been removed.
- **Nodes default to `update_node_files=False`**. If you explicitly set
  `update_node_files=True`, a deprecation warning is emitted.
- **New `madsci config` CLI commands** provide explicit configuration
  management:
  - `madsci config export <manager_type>` -- export settings with redacted secrets
  - `madsci config export --include-secrets` -- export with actual secret values
  - `madsci config create manager <type>` -- generate a new config file
  - `madsci config create node <type>` -- generate a new node config file
- **Secret classification** via `json_schema_extra={"secret": True}` metadata
  on fields that contain credentials.
- **`model_dump_safe()`** method on all models for safe serialization.

## Deprecation Timeline

| Version | Change |
|---------|--------|
| **v0.7.0** (current) | Definition files deprecated. Auto-writing removed for managers. `update_node_files` defaults to `False`. Deprecation warnings emitted. `madsci config` CLI available. |
| **v0.8.0** (planned) | Definition file loading removed. `NodeDefinition` class removed. All configuration via settings/env vars. `_update_node_info_and_definition()` removed. |

## Migration Steps

### Step 1: Identify your definition files

Run the migration scanner to find all definition files:

```bash
madsci migrate scan
```

This will list all `*.manager.yaml`, `*.node.yaml`, and `*.workflow.yaml`
files in your lab directory.

### Step 2: Export current settings

For each manager, export its current settings:

```bash
# Export all manager settings
madsci config export --all

# Or export specific managers
madsci config export event
madsci config export resource
```

### Step 3: Convert to environment variables

The exported settings can be converted to environment variables. Each
manager uses a prefix:

| Manager | Env Prefix |
|---------|-----------|
| Lab | `SQUID_` |
| Event | `EVENT_` |
| Experiment | `EXPERIMENT_` |
| Resource | `RESOURCE_` |
| Data | `DATA_` |
| Workcell | `WORKCELL_` |
| Location | `LOCATION_` |

For example, if your `event.manager.yaml` had:
```yaml
mongo_db_url: mongodb://myhost:27017
database_name: my_events
```

Set environment variables:
```bash
EVENT_MONGO_DB_URL=mongodb://myhost:27017
EVENT_DATABASE_NAME=my_events
```

### Step 4: Update node configurations

If your nodes use `update_node_files=True`, remove that setting or
set it to `False`:

```bash
# In your node's .env or environment:
NODE_UPDATE_NODE_FILES=false
```

Use the new identity settings instead of definition files:

```bash
NODE_NODE_NAME=my_instrument
NODE_MODULE_NAME=my_instrument_module
NODE_MODULE_VERSION=1.0.0
NODE_NODE_TYPE=device
```

### Step 5: Test the migration

1. Remove or rename your definition files
2. Start your lab with the new environment variables
3. Verify everything works:

```bash
madsci doctor
madsci status
```

### Step 6: Clean up

Once everything is working without definition files:

1. Remove old `*.manager.yaml` files from version control
2. Remove old `*.node.yaml` and `*.info.yaml` files
3. Add `*.manager.yaml`, `*.node.yaml`, `*.info.yaml` to `.gitignore`

## FAQ

### Can I keep using definition files?

Yes, during v0.7.x. Existing definition files will still be loaded
(with deprecation warnings). However, they will stop being loaded
in v0.8.0.

### What about secrets in definition files?

Secrets should be moved to environment variables. The new
`madsci config export` command redacts secrets by default, so
exported config files are safe to commit to version control.

### How do I export my node's info?

Use the node's `/info` REST endpoint:

```bash
curl http://localhost:2000/info
```

The info is now generated at runtime from the node's configuration
and action decorators, without needing a file on disk.

### What if I have custom definition fields?

If your definition class has extra fields beyond what `ManagerDefinition`
or `NodeDefinition` provides, you should move those to your settings
class. The `model_config = ConfigDict(extra="allow")` on
`ManagerDefinition` allowed arbitrary extra fields, but settings classes
provide proper validation and documentation.
