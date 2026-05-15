# CLI Reference

Complete reference for the MADSci command-line interface.

## Global Options

```
madsci [OPTIONS] COMMAND [ARGS]...
```

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--lab-url URL` | `LAB_SERVER_URL` | Lab manager URL (default: `http://localhost:8000/`) |
| `-v, --verbose` | | Increase verbosity (repeatable: `-vv`, `-vvv`) |
| `-q, --quiet` | | Suppress non-essential output |
| `--no-color` | `NO_COLOR` | Disable colored output |
| `--json` | | Output in JSON format (where applicable) |
| `--yaml` | | Output in YAML format (where applicable) |
| `--version` | | Show version and exit |

---

## Setup Commands

### `madsci init`

Initialize a new MADSci lab interactively. Creates directory structure, configuration files, and optionally sets up Docker Compose.

```bash
madsci init my_lab
madsci init .                    # Initialize in current directory
```

### `madsci new`

Create new MADSci components from templates. This is a command group with subcommands for each component type.

```bash
madsci new list                             # List all 33 templates
madsci new list --category module           # Filter by category
madsci new module                           # Interactive module creation
madsci new module --name my_pipette --template module/device
madsci new interface --type fake            # Add fake interface to module
madsci new experiment --modality script     # Create experiment
madsci new workflow                         # Create workflow
madsci new lab --template standard          # Create full lab
madsci new node --name my_device            # Create standalone node
```

**Alias**: `n`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List available templates (filterable by `--category`, `--tag`) |
| `module` | Create a node module (`--template`: basic, device, instrument, liquid_handler, camera, robot_arm) |
| `interface` | Add interface to existing module (`--type`: fake, sim, mock) |
| `node` | Create standalone REST node server |
| `experiment` | Create experiment (`--modality`: script, notebook, tui, node) |
| `workflow` | Create workflow (`--template`: basic, multi_step) |
| `lab` | Create lab configuration (`--template`: minimal, standard, distributed) |

All subcommands support `--name`, `--no-interactive`, and template-specific options.

### `madsci add`

Add components to an existing MADSci module project. Each subcommand adds a specific component using templates.

```bash
madsci add docs --name my_module             # Add documentation scaffolding
madsci add drivers --name my_module          # Add driver stubs
madsci add notebooks --name my_module        # Add Jupyter notebook templates
madsci add gitignore                         # Add a .gitignore file
madsci add compose --name my_module          # Add Docker Compose configuration
madsci add dev-tools                         # Add development tool configs
madsci add agent-config                      # Add AI agent configuration files
madsci add all --name my_module              # Add all optional components
madsci add docs -d ./my_module --on-conflict overwrite
```

#### Group-Level Options

| Option | Description |
|--------|-------------|
| `--name, -n` | Name of the module project |
| `--description` | Description of the module project |
| `--dir, -d` | Target directory (default: `.`) |
| `--on-conflict` | Conflict resolution strategy: `skip`, `overwrite`, or `backup` (default: `skip`) |
| `--no-interactive` | Disable interactive prompts |

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `docs` | Add documentation scaffolding to the project |
| `drivers` | Add driver stubs to the project |
| `notebooks` | Add Jupyter notebook templates to the project |
| `gitignore` | Add a `.gitignore` file to the project |
| `compose` | Add Docker Compose configuration to the project |
| `dev-tools` | Add development tool configurations to the project |
| `agent-config` | Add AI agent configuration files to the project |
| `all` | Add all optional components to the project |

---

## Operations Commands

### `madsci start`

Start MADSci lab services.

```bash
madsci start                    # Start all services (Docker, foreground)
madsci start -d                 # Start in background
madsci start --build            # Rebuild images first
madsci start --mode local       # Start without Docker (pure Python)
madsci start --services workcell_manager --services lab_manager
madsci start --config path/to/compose.yaml
madsci start -d --no-wait       # Skip health polling after starting
madsci start -d --wait-timeout 120  # Custom health poll timeout
```

| Option | Description |
|--------|-------------|
| `-d, --detach` | Run services in the background |
| `--build` | Build images before starting |
| `--services` | Start only specific services (repeatable) |
| `--config PATH` | Path to Docker Compose file |
| `--mode [docker\|local]` | Run mode (default: docker) |
| `--wait/--no-wait` | Wait for services to become healthy (default: wait when `-d`) |
| `--wait-timeout INT` | Timeout for health polling in seconds (default: 60) |
| `--settings-dir PATH` | Settings directory for walk-up config file discovery (sets `MADSCI_SETTINGS_DIR` for child processes) |

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `start manager <name>` | Start a single manager (lab, event, experiment, resource, data, workcell, location) |
| `start node <path>` | Start a node module from a Python file |

```bash
madsci start manager event       # Start event manager (foreground)
madsci start manager event -d    # Start in background
madsci start node ./my_node.py   # Start node (foreground)
madsci start node ./my_node.py -d --name lh  # Background with custom name
madsci start --settings-dir /opt/lab manager event  # With settings directory
madsci start node ./node.py --settings-dir ./nodes/arm  # Node with settings dir
```

### `madsci stop`

Stop MADSci lab services via Docker Compose. Also supports stopping individual background managers and nodes.

```bash
madsci stop                     # Stop all services
madsci stop --remove            # Stop and remove images
madsci stop --volumes           # Stop and remove volumes (data loss!)
madsci stop manager event       # Stop a background manager
madsci stop node my_node        # Stop a background node
```

| Option | Description |
|--------|-------------|
| `--remove` | Remove locally-built images after stopping |
| `--volumes` | Remove named volumes (requires confirmation) |
| `--config PATH` | Path to Docker Compose file |

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `stop manager <name>` | Stop a background manager process |
| `stop node <name>` | Stop a background node process |

### `madsci status`

Show status of MADSci services.

```bash
madsci status                   # Show all services
madsci status lab_manager       # Show specific service
madsci status --watch           # Continuously update (every 5s)
madsci status --watch --interval 2
madsci status --json            # Output as JSON
```

**Alias**: `s`

| Option | Description |
|--------|-------------|
| `--watch, -w` | Continuously update status |
| `--interval FLOAT` | Watch interval in seconds (default: 5) |
| `--json` | Output as JSON |
| `--timeout FLOAT` | Request timeout in seconds (default: 5) |

### `madsci doctor`

Run diagnostic checks on the MADSci environment.

```bash
madsci doctor                   # Run all checks
madsci doctor --check python    # Check Python environment
madsci doctor --check docker    # Check Docker availability
madsci doctor --check ports     # Check port availability
```

**Alias**: `doc`

---

## Development Commands

### `madsci run`

Run workflows or experiments.

> **Deprecation notice**: `madsci run workflow` is deprecated in favor of `madsci workflow submit`. `madsci run experiment` is deprecated in favor of `madsci experiment run`.

```bash
madsci run workflow path/to/workflow.yaml
madsci run experiment path/to/experiment.py
```

### `madsci validate`

Validate MADSci configuration and definition files.

```bash
madsci validate path/to/config.yaml
madsci validate path/to/workcell.yaml
```

**Alias**: `val`

### `madsci config`

Manage MADSci configuration files. Exports use prefixed keys by default (e.g., `event_server_url`) for compatibility with the shared `settings.yaml` format.

```bash
madsci config export event                # Export Event Manager settings (prefixed keys)
madsci config export --all                # Export all manager settings
madsci config export event --format json  # Export as JSON
madsci config export event --settings-dir /opt/lab  # Export from specific lab dir
madsci config create manager event        # Create Event Manager settings file
madsci config create manager event -o my-event.yaml  # Custom output path
```

**Alias**: `cfg`

---

## Data Commands

### `madsci logs`

View and filter event logs.

```bash
madsci logs                     # View recent logs
madsci logs --tail 50           # Last 50 entries
madsci logs --follow            # Follow in real time
madsci logs --level ERROR       # Filter by level
madsci logs --level WARNING
madsci logs --grep "workflow"   # Filter by pattern
madsci logs --since 1h          # Logs from last hour
madsci logs --since 30m
```

**Alias**: `l`

| Option | Description |
|--------|-------------|
| `--tail N` | Number of recent entries to show |
| `--follow, -f` | Follow logs in real time |
| `--level LEVEL` | Filter by log level (DEBUG, INFO, WARNING, ERROR) |
| `--grep PATTERN` | Filter by text pattern |
| `--since DURATION` | Show logs since duration (e.g., 1h, 30m, 2d) |

### `madsci backup`

Create database backups.

```bash
madsci backup create --db-url postgresql://localhost/resources
madsci backup create --db-url mongodb://localhost:27017/events
madsci backup list
madsci backup restore <backup_path>
```

---

## Manager Interaction Commands

### `madsci workflow`

Manage and monitor workflows.

```bash
madsci workflow list                    # List active workflows
madsci workflow show <id>               # Show workflow details
madsci workflow submit ./wf.yaml        # Submit a workflow
madsci workflow pause <id>              # Pause a running workflow
madsci workflow resume <id>             # Resume a paused workflow
madsci workflow cancel <id>             # Cancel a workflow
madsci workflow retry <id>              # Retry a failed workflow
madsci workflow resubmit <id>           # Resubmit a workflow
```

**Alias**: `wf`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List workflows (filterable by `--active`, `--archived`, `--queued`, `--all`, `--limit`) |
| `show` | Show workflow details (`--steps` to include steps, `--follow` to watch progress) |
| `submit` | Submit a workflow (`--parameters`, `--no-wait`, `--name`) |
| `pause` | Pause a running workflow |
| `resume` | Resume a paused workflow |
| `cancel` | Cancel a workflow |
| `retry` | Retry a failed workflow |
| `resubmit` | Resubmit a workflow |

### `madsci resource`

Manage laboratory resources and inventory.

```bash
madsci resource list                     # List resources
madsci resource get <id>                 # Show resource details
madsci resource create --template <t>    # Create from template
madsci resource delete <id>              # Soft-delete a resource
madsci resource restore <id>            # Restore deleted resource
madsci resource tree <id>               # Show resource hierarchy
madsci resource lock <id>                # Acquire a lock
madsci resource unlock <id>              # Release a lock
madsci resource quantity set <id> <val>  # Set quantity
madsci resource quantity adjust <id> <d> # Adjust quantity
madsci resource template list            # List templates
madsci resource history <id>             # Show change history
```

**Alias**: `res`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List resources (filterable by `--type`, `--limit`) |
| `get` | Show resource details |
| `create` | Create a resource (`--template`, `--name`, `--params`) |
| `delete` | Soft-delete a resource |
| `restore` | Restore a deleted resource |
| `tree` | Show resource hierarchy (ancestors and descendants) |
| `lock` | Acquire a lock on a resource |
| `unlock` | Release a lock on a resource |
| `quantity set` | Set resource quantity to a specific value |
| `quantity adjust` | Adjust resource quantity by a delta |
| `template list` | List available resource templates |
| `template get` | Get a specific resource template |
| `history` | Show change history for a resource |

### `madsci location`

Manage laboratory locations, resource attachments, and node-specific references.

```bash
madsci location list                         # List locations
madsci location get <name>                   # Show location details
madsci location create --name <name>         # Create a location
madsci location create-from-template <t>     # Create from template
madsci location delete <name>                # Delete a location
madsci location resources <name>             # Show attached resources
madsci location attach <name> <resource_id>  # Attach resource
madsci location detach <name>                # Detach resource
madsci location set-repr <loc> <node>        # Set representation
madsci location remove-repr <loc> <node>     # Remove representation
madsci location transfer-graph               # Show transfer graph
madsci location plan-transfer <src> <tgt>    # Plan a transfer
madsci location export                       # Export locations
madsci location import <file>                # Import locations
madsci location template list                # List location templates
madsci location rep-template list            # List repr templates
```

**Alias**: `loc`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List all locations |
| `get` | Show location details |
| `create` | Create a location (`--name`, `--description`, `--allow-transfers`) |
| `create-from-template` | Create from template (`--template`, `--name`, `--bindings`, `--repr-overrides`) |
| `delete` | Delete a location |
| `resources` | Show resources attached to a location |
| `attach` | Attach a resource to a location |
| `detach` | Detach a resource from a location |
| `set-repr` | Set a node-specific representation for a location |
| `remove-repr` | Remove a node-specific representation |
| `transfer-graph` | Show the location transfer adjacency graph |
| `plan-transfer` | Plan a transfer between two locations |
| `export` | Export all locations to a file |
| `import` | Import locations from a file |
| `template list` | List available location templates |
| `rep-template list` | List available representation templates |

### `madsci node`

Manage and interact with laboratory instrument nodes.

```bash
madsci node list                         # List all nodes
madsci node info <name>                  # Show node details
madsci node status <name>               # Show node status
madsci node state <name>                 # Show node state
madsci node log <name>                   # Show node events
madsci node admin <name> <command>       # Send admin command
madsci node action <name> <action>       # Execute an action
madsci node action-result <name> <id>    # Get action result
madsci node action-history <name>        # Show action history
madsci node config <name>                # Show node config
madsci node set-config <name> --data {}  # Update node config
madsci node add <name> <url>             # Add node to workcell
madsci node shell <name>                 # Interactive REPL
```

**Alias**: `nd`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List all registered nodes |
| `info` | Show detailed node information |
| `status` | Show node status |
| `state` | Show node state |
| `log` | Show node event log (`--tail` to limit entries) |
| `admin` | Send admin command (safety_stop, reset, pause, resume, cancel, shutdown, lock, unlock) |
| `action` | Execute a node action |
| `action-result` | Get the result of a previous action |
| `action-history` | Show action history for a node |
| `config` | Show node configuration |
| `set-config` | Update node configuration (`--data`) |
| `add` | Add a node to the workcell |
| `shell` | Launch an interactive REPL for a node |

### `madsci experiment`

Manage experiments and experimental campaigns.

```bash
madsci experiment list                   # List recent experiments
madsci experiment get <id>               # Show experiment details
madsci experiment start --name "run 1"   # Start a new experiment
madsci experiment run ./my_exp.py        # Execute experiment script
madsci experiment pause <id>             # Pause an experiment
madsci experiment continue <id>          # Continue a paused experiment
madsci experiment cancel <id>            # Cancel an experiment
madsci experiment end <id>               # End an experiment
```

**Alias**: `exp`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List experiments (filterable by `--count`, `--status`) |
| `get` | Show experiment details |
| `start` | Start a new experiment (`--design`, `--name`, `--desc`, `--run-name`) |
| `run` | Execute an experiment script |
| `pause` | Pause a running experiment |
| `continue` | Continue a paused experiment |
| `cancel` | Cancel an experiment |
| `end` | End an experiment (`--status`) |

### `madsci campaign`

Manage experimental campaigns.

```bash
madsci campaign create --name "My Campaign"
madsci campaign get <campaign_id>
```

**Alias**: `camp`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `create` | Create a new campaign (`--name`, `--desc`) |
| `get` | Show campaign details |

### `madsci data`

Manage datapoints and data capture.

```bash
madsci data list                         # List recent datapoints
madsci data get <id>                     # Get datapoint value
madsci data metadata <id>               # Show datapoint metadata
madsci data submit --file ./results.csv  # Submit a file datapoint
madsci data submit --value '{"a": 1}'    # Submit a JSON value
madsci data query --selector '{"label": "test"}'
```

**Alias**: `dt`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List recent datapoints (`--count`) |
| `get` | Get datapoint value (`--save-to` to save to file) |
| `metadata` | Show datapoint metadata |
| `submit` | Submit a datapoint (`--file` or `--value`, mutually exclusive; `--label`) |
| `query` | Query datapoints (`--selector`, `--limit`) |

### `madsci events`

Query and manage event logs.

```bash
madsci events query                     # Query recent events
madsci events get <id>                  # Show event details
madsci events archive --ids <id1,id2>   # Archive specific events
madsci events purge --older-than-days 30
madsci events backup --create           # Create event backup
```

**Alias**: `ev`

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `query` | Query events (`--selector`, `--count`, `--level`) |
| `get` | Show event details |
| `archive` | Archive events (`--before-date`, `--ids`) |
| `purge` | Purge old events (`--older-than-days`, `--yes` to skip confirmation) |
| `backup` | Manage event backups (`--create`, `--status`) |

---

## Utility Commands

### `madsci version`

Show MADSci version information.

```bash
madsci version
madsci --version
```

### `madsci completion`

Generate shell completion scripts.

```bash
madsci completion bash          # Bash completions
madsci completion zsh           # Zsh completions
madsci completion fish          # Fish completions
```

### `madsci commands`

List all available CLI commands with descriptions.

```bash
madsci commands
```

**Alias**: `cmd`

### `madsci tui`

Launch the interactive terminal user interface.

```bash
madsci tui
```

**Alias**: `ui`

**Main screens** (9) — accessible via keyboard shortcuts:

| Key | Screen | Description |
|-----|--------|-------------|
| `d` | Dashboard | Service overview and quick actions |
| `s` | Status | Detailed service health with auto-refresh |
| `l` | Logs | Filterable log viewer with follow mode |
| `n` | Nodes | Node status, admin commands, and action executor |
| `w` | Workflows | Workflow monitoring with step progress and filtering |
| `e` | Experiments | Experiment browsing with status filtering |
| `i` | Resources | Resource inventory with type filtering and detail panels |
| `b` | Data Browser | Datapoint browsing with label and type filtering |
| `o` | Locations | Location browsing with transfer graph visualization |

**Detail/Modal screens** (5) — opened from context within main screens:
- **Resource Tree**: Hierarchical resource ancestor/descendant visualization
- **Transfer Graph**: Location transfer adjacency graph
- **Workflow Detail**: Step-by-step workflow progress with timing
- **Step Detail**: Individual workflow step details and results
- **Action Executor**: Interactive node action execution

**Additional shortcuts**: `q` quit, `?` help, `r` refresh, `Ctrl+P` command palette

### `madsci registry`

Manage the MADSci service registry.

```bash
madsci registry list
madsci registry show <service_name>
```

### `madsci migrate`

Run database migrations.

```bash
madsci migrate --db-url postgresql://localhost/resources
madsci migrate status
madsci migrate rollback                    # Roll back a migration
```

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `status` | Show migration status |
| `rollback` | Roll back a migration to restore original files |

---

## Command Aliases

For faster CLI usage:

| Alias | Command |
|-------|---------|
| `n` | `new` |
| `s` | `status` |
| `l` | `logs` |
| `doc` | `doctor` |
| `val` | `validate` |
| `ui` | `tui` |
| `cmd` | `commands` |
| `cfg` | `config` |
| `wf` | `workflow` |
| `res` | `resource` |
| `loc` | `location` |
| `nd` | `node` |
| `exp` | `experiment` |
| `camp` | `campaign` |
| `dt` | `data` |
| `ev` | `events` |
