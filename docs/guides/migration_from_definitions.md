# Migrating from Definition Files to Settings-Based Configuration

**Status**: Hard deprecation in v0.7.0 — definition files are no longer supported.

## Overview

As of v0.7.0, MADSci has fully transitioned from definition file-based
configuration (YAML files that were auto-written on startup) to explicit
settings-based configuration managed through environment variables, settings
files, and CLI commands.

**Definition files (`*.manager.yaml`, `*.node.yaml`, `*.info.yaml`) are no
longer loaded or recognized.** You must migrate to the new settings-based
configuration using the `madsci migrate` tool before upgrading to v0.7.0.

This guide explains what changed, why, and how to migrate.

## What Changed

### Before (v0.6.x and earlier)

- Managers auto-wrote `*.manager.yaml` definition files on every startup
- Nodes auto-wrote `*.node.yaml` and `*.info.yaml` files on every startup
- Configuration was a mix of definition files, environment variables, and code
- Secrets could end up in auto-written files without user awareness
- The "source of truth" was unclear (definition file vs. environment variable?)

### After (v0.7.0)

- **Definition files are no longer supported.** Managers and nodes do not read
  or write definition files. Any remaining definition files are ignored.
- **`NodeDefinition` class has been removed.** Use `NodeConfig` directly.
- **`_update_node_info_and_definition()` has been removed.** Node info is
  generated at runtime from configuration and action decorators.
- **`update_node_files` setting has been removed.** Nodes no longer write
  files to disk.
- **All configuration is via settings, environment variables, and `.env` files.**
- **New `madsci config` CLI commands** provide explicit configuration
  management:
  - `madsci config export <manager_type>` -- export settings with redacted secrets
  - `madsci config export --include-secrets` -- export with actual secret values
  - `madsci config create manager <type>` -- generate a new config file
  - `madsci config create node <type>` -- generate a new node config file
- **Secret classification** via `json_schema_extra={"secret": True}` metadata
  on fields that contain credentials.
- **`model_dump_safe()`** method on all models for safe serialization.

## Migration Steps

**You must complete these steps before upgrading to v0.7.0.** The `madsci
migrate` tool automates most of the process.

### Step 1: Identify your definition files

Run the migration scanner to find all definition files:

```bash
madsci migrate scan
```

This will list all `*.manager.yaml`, `*.node.yaml`, and `*.workflow.yaml`
files in your lab directory.

### Step 2: Preview the migration

See what changes will be made without modifying any files:

```bash
madsci migrate convert /path/to/your/lab --dry-run
```

### Step 3: Apply the migration

```bash
madsci migrate convert /path/to/your/lab --apply
```

This will:
- Create backups of all definition files (`.yaml.bak`)
- Register all component IDs in the local registry
- Generate environment variable files (`.env.<manager_type>`)
- Mark the original definition files as migrated

### Step 4: Export current settings

For each manager, export its current settings to verify correctness:

```bash
# Export all manager settings
madsci config export --all

# Or export specific managers
madsci config export event
madsci config export resource
```

### Step 5: Convert to environment variables

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
document_db_url: mongodb://myhost:27017
database_name: my_events
```

Set environment variables:
```bash
EVENT_DOCUMENT_DB_URL=mongodb://myhost:27017
EVENT_DATABASE_NAME=my_events
```

### Step 6: Update node configurations

Remove any `update_node_files` setting from your node configuration (the
setting no longer exists).

Use the new identity settings instead of definition files:

```bash
NODE_NODE_NAME=my_instrument
NODE_MODULE_NAME=my_instrument_module
NODE_MODULE_VERSION=1.0.0
NODE_NODE_TYPE=device
```

### Step 7: Test the migration

1. Remove or rename your definition files
2. Start your lab with the new environment variables
3. Verify everything works:

```bash
madsci doctor
madsci status
```

### Step 8: Finalize

Once everything is working, finalize the migration to clean up old files:

```bash
madsci migrate finalize /path/to/your/lab --apply
```

This removes the deprecated definition files (backups are preserved).

Alternatively, clean up manually:

1. Remove old `*.manager.yaml` files from version control
2. Remove old `*.node.yaml` and `*.info.yaml` files
3. Add `*.manager.yaml`, `*.node.yaml`, `*.info.yaml` to `.gitignore`

## Rollback

If something goes wrong during migration:

```bash
madsci migrate rollback /path/to/your/lab
```

This restores all files from their `.bak` backups.

## FAQ

### Can I keep using definition files?

No. Definition file support has been removed in v0.7.0. You must migrate to
settings-based configuration using the `madsci migrate` tool.

### What about secrets in definition files?

Secrets should be moved to environment variables or `.env` files. The
`madsci config export` command redacts secrets by default, so exported
config files are safe to commit to version control.

### How do I export my node's info?

Use the node's `/info` REST endpoint:

```bash
curl http://localhost:2000/info
```

The info is now generated at runtime from the node's configuration
and action decorators, without needing a file on disk.

### What if I have custom definition fields?

If your definition class had extra fields beyond what `ManagerDefinition`
or `NodeDefinition` provided, you should move those to your settings
class. Settings classes provide proper validation and documentation
instead of the permissive `extra="allow"` that definition classes used.
