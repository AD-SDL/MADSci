# CLI Reference

Complete reference for the MADSci command-line interface.

## Global Options

```
madsci [OPTIONS] COMMAND [ARGS]...
```

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `-c, --config PATH` | `MADSCI_CONFIG` | Configuration file path |
| `--lab-url URL` | `MADSCI_LAB_URL` | Lab manager URL (default: `http://localhost:8000/`) |
| `-v, --verbose` | | Increase verbosity (repeatable: `-vv`, `-vvv`) |
| `-q, --quiet` | | Suppress non-essential output |
| `--no-color` | `NO_COLOR` | Disable colored output |
| `--json` | | Output in JSON format (where applicable) |
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
madsci new list                             # List all 26 templates
madsci new list --category module           # Filter by category
madsci new module                           # Interactive module creation
madsci new module --name my_pipette --template module/device
madsci new interface --type fake            # Add fake interface to module
madsci new experiment --modality script     # Create experiment
madsci new workflow                         # Create workflow
madsci new workcell --name my_workcell      # Create workcell config
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
| `workcell` | Create workcell configuration |
| `lab` | Create lab configuration (`--template`: minimal, standard, distributed) |

All subcommands support `--name`, `--no-interactive`, and template-specific options.

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

```bash
madsci run workflow path/to/workflow.yaml
madsci run experiment path/to/experiment.py
```

### `madsci validate`

Validate MADSci configuration and definition files.

```bash
madsci validate path/to/config.yaml
madsci validate --type workcell path/to/workcell.yaml
```

**Alias**: `val`

### `madsci config`

Manage MADSci configuration files.

```bash
madsci config export            # Export current config to YAML
madsci config create            # Create a new config file interactively
madsci config show              # Display active configuration
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

Provides five screens:
- **Dashboard**: Service overview and quick actions
- **Status**: Detailed service health with auto-refresh
- **Logs**: Filterable log viewer
- **Nodes**: Node status and management
- **Workflows**: Workflow monitoring and control

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
```

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
