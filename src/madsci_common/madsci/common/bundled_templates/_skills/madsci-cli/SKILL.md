---
name: madsci-cli
description: Working with the MADSci CLI (the `madsci` command). Use when adding, modifying, or debugging CLI commands, or when using the CLI to operate a MADSci lab.
---

# MADSci CLI

The `madsci` CLI is built on Click with lazy command loading, Rich output formatting, and a Textual TUI. It provides 17 commands for managing MADSci labs.

## Key Files

| File | Purpose |
|------|---------|
| `src/madsci_client/madsci/client/cli/__init__.py` | Root command, `AliasedGroup`, `_LAZY_COMMANDS` |
| `src/madsci_client/madsci/client/cli/commands/` | 17 command modules |
| `src/madsci_client/madsci/client/cli/utils/output.py` | Rich console output helpers |
| `src/madsci_client/madsci/client/cli/tui/app.py` | Textual TUI application |
| `src/madsci_client/madsci/client/cli/tui/styles/theme.tcss` | TUI CSS theme |
| `src/madsci_common/madsci/common/bundled_templates/` | 25 template manifests + Jinja2 files |

## Architecture

```
madsci (AliasedGroup)
  ├── Global options: --lab-url, -v, -q, --no-color, --json, --version
  ├── Context: MadsciContext (lazy), Console, verbosity flags
  └── Commands (lazy-loaded via _LAZY_COMMANDS):
      ├── version, doctor (doc), status (s), logs (l)
      ├── tui (ui), registry, migrate, new (n)
      ├── start, stop, init, validate (val)
      ├── run, completion, backup
      ├── commands (cmd), config (cfg)
      └── [aliases resolve via AliasedGroup]
```

### Lazy Command Loading

Commands are loaded on first use to minimize CLI startup time:

```python
# In cli/__init__.py
_LAZY_COMMANDS = {
    "version": ("madsci.client.cli.commands.version", "version"),
    "doctor": ("madsci.client.cli.commands.doctor", "doctor"),
    "status": ("madsci.client.cli.commands.status", "status"),
    "logs": ("madsci.client.cli.commands.logs", "logs"),
    "tui": ("madsci.client.cli.commands.tui", "tui"),
    "registry": ("madsci.client.cli.commands.registry", "registry"),
    "migrate": ("madsci.client.cli.commands.migrate", "migrate"),
    "new": ("madsci.client.cli.commands.new", "new"),
    "start": ("madsci.client.cli.commands.start", "start"),
    "stop": ("madsci.client.cli.commands.stop", "stop"),
    "init": ("madsci.client.cli.commands.init", "init"),
    "validate": ("madsci.client.cli.commands.validate", "validate"),
    "run": ("madsci.client.cli.commands.run", "run"),
    "completion": ("madsci.client.cli.commands.completion", "completion"),
    "backup": ("madsci.client.cli.commands.backup", "backup"),
    "commands": ("madsci.client.cli.commands.commands", "commands"),
    "config": ("madsci.client.cli.commands.config", "config"),
}
```

### AliasedGroup

```python
class AliasedGroup(click.Group):
    _aliases: ClassVar[dict[str, str]] = {
        "n": "new",
        "s": "status",
        "l": "logs",
        "doc": "doctor",
        "val": "validate",
        "ui": "tui",
        "cmd": "commands",
        "cfg": "config",
    }
```

Resolves aliases first, then tries eager commands, then lazy-imports.

## Adding a New Command

### Step 1: Create the command module

```python
# src/madsci_client/madsci/client/cli/commands/my_command.py
import click

@click.command()
@click.pass_context
def my_command(ctx: click.Context):
    """One-line description shown in --help."""
    # Lazy imports for heavy dependencies
    from madsci.client.cli.utils.output import get_console, success

    console = get_console(ctx)
    success(console, "Command executed successfully")
```

### Step 2: Register in `_LAZY_COMMANDS`

```python
# In cli/__init__.py, add to _LAZY_COMMANDS dict:
_LAZY_COMMANDS = {
    ...
    "my_command": ("madsci.client.cli.commands.my_command", "my_command"),
}
```

### Step 3: (Optional) Add alias

```python
# In AliasedGroup._aliases:
_aliases = {
    ...
    "mc": "my_command",
}
```

**Critical rules:**
- **Lazy imports are mandatory** for heavy dependencies (clients, types, etc.) - import inside the function body, not at module top
- Use `@click.pass_context` to access the CLI context (console, verbosity, etc.)
- All informational output should support `--json` via `ctx.obj["json"]`

## Command Reference

### `version`
Display installed MADSci package versions, Python info, platform.
- `--json`, `--check-updates`

### `doctor` (alias: `doc`)
System diagnostics: Python version, virtualenv, Docker, port availability.
- `--fix`, `--check [python|docker|ports|network]`, `--json`

### `status` (alias: `s`)
Show health of MADSci services (hits `/health` endpoints).
- `[services]` args, `-w/--watch`, `--interval`, `--timeout`, `--json`

### `logs` (alias: `l`)
View/stream logs from Event Manager.
- `-f/--follow`, `--tail N`, `--since 5m/1h/1d`, `--level`, `--grep`, `--json`

### `tui` (alias: `ui`)
Launch Textual terminal UI with 5 screens (dashboard, status, logs, nodes, workflows).
- `--screen [dashboard|status|logs|nodes|workflows]`
- Keybindings: `d/s/l/n/w` (screens), `r` (refresh), `q` (quit), `?` (help), `Ctrl+P` (command palette)

### `registry`
Manage ID Registry (ULID mappings for component names).
- Subcommands: `list [--type] [--include-stale]`, `resolve <name>`, `clean`

### `migrate`
Upgrade from deprecated definition files to Settings + ID Registry.
- Subcommands: `scan [dir]`, `convert [--all]`, `status`, `finalize`

### `new` (alias: `n`)
Create new components from templates. Interactive parameter prompts.
- Subcommands: `lab`, `module`, `node`, `interface`, `experiment`, `workflow`
- `--tui` launches Textual template browser

### `start`
Start MADSci services.
- `-d/--detach`, `--build`, `--services`, `--mode [docker|local]`, `--wait/--no-wait`, `--settings-dir`
- Subcommands: `manager <name> [-d]`, `node <path> [-d]`
- Docker mode: finds compose file, runs `docker compose up`
- Local mode: all 7 managers in-process with in-memory backends (no Docker)

### `stop`
Stop MADSci services.
- `--remove`, `--volumes` (requires confirmation), `--config`
- Subcommands: `manager <name>`, `node <name>`

### `init`
Initialize new MADSci lab (scaffolds `.madsci/`, settings, templates).
- `[directory]`, `--template [minimal]`, `--name`, `--description`, `--no-interactive`

### `validate` (alias: `val`)
Validate YAML configuration files (workflow, node, manager definitions).
- `[paths]`, `--json`

### `run`
Execute workflows or experiments.
- Subcommands: `workflow <path> [--parameters JSON] [--no-wait]`, `experiment <path>`

### `completion`
Generate shell completion scripts.
- `<shell>` arg: `bash`, `zsh`, `fish`

### `backup`
Database backup management (re-exports from `madsci.common.backup_tools.cli`).
- Subcommands: `create --db-url`, `restore --backup --db-url`, `validate --backup --db-url`
- Auto-detects PostgreSQL vs MongoDB/FerretDB

### `commands` (alias: `cmd`)
Launch Trogon interactive command palette (TUI forms for all commands).

### `config` (alias: `cfg`)
Configuration management with secret redaction.
- Subcommands: `export [manager_type] [--all] [-o path] [--format yaml|json] [--include-secrets]`, `create manager <type>`

## Output Helpers

```python
from madsci.client.cli.utils.output import (
    get_console,      # Get Rich Console from click context
    output_result,    # Handles json/yaml/text output
    success,          # Green checkmark message
    error,            # Red X message (with optional details)
    warning,          # Yellow warning message
    info,             # Blue info message
    print_panel,      # Rich Panel with border
    format_url,       # Rich link format
)

# Usage pattern:
console = get_console(ctx)
success(console, "Operation completed")
error(console, "Failed to connect", details="Connection refused on port 8001")

# JSON-aware output:
if ctx.obj.get("json"):
    output_result(console, data, format="json")
else:
    output_result(console, data, format="text", title="Results")
```

## Template System

Templates live in `src/madsci_common/madsci/common/bundled_templates/`. Each has a `template.yaml` manifest:

```yaml
name: "Module Name"
version: "1.0.0"
description: "What this template creates"
category: "lab|module|node|interface|experiment|workflow"
tags: ["device", "robot"]

parameters:
  - name: module_name
    type: string
    description: "Name of the module"
    required: true
    pattern: "^[a-z][a-z0-9_]*$"
  - name: port
    type: integer
    description: "Server port"
    default: 2000
    min: 1024
    max: 65535
  - name: include_tests
    type: boolean
    description: "Include test files"
    default: true

files:
  - source: "template/{{module_name}}_node.py.j2"
    destination: "{{module_name}}/{{module_name}}_node.py"
  - source: "template/test_node.py.j2"
    destination: "{{module_name}}/tests/test_node.py"
    condition: "{{ include_tests }}"

hooks:
  post_generate:
    - command: "ruff format {{module_name}}/"
      continue_on_error: true
```

**Template categories (25 total):**
- `lab/`: minimal lab scaffold
- `module/`: device, compute modules (full packages with tests, Dockerfile)
- `node/`: basic node, rest node
- `interface/`: node interface
- `experiment/`: script, notebook, tui, node modalities
- `workflow/`: basic workflow

**Jinja2 filters:** `pascal_case` (converts `my_module` -> `MyModule`)

### Template-Model Alignment

Every template that generates YAML/JSON configuration must produce output that validates against a specific Pydantic model. Templates declare their target model via the `target_model` field in `template.yaml`:

```yaml
# In template.yaml
target_model: "madsci.common.types.workflow_types.WorkflowDefinition"
```

| Template Category | Output Type | Target Pydantic Model |
|---|---|---|
| lab/* | settings.yaml | MadsciContext / ManagerSettings subclasses (no single target_model — shared file) |
| workflow/* | *.workflow.yaml | `WorkflowDefinition` |
| node/* | Python code | Uses `RestNodeConfig` in generated code |
| module/* | Python package | Uses `RestNodeConfig`, domain-specific models |
| experiment/* | Python code | Uses `ExperimentDesign` in generated code |

When creating new templates for config files:
1. Identify the Pydantic model first
2. Build the template to match its schema
3. Set `target_model` in `template.yaml` so tests validate output automatically

## Start/Stop Lifecycle

### Docker Mode (default)
```bash
madsci start              # docker compose up (foreground)
madsci start -d           # detached + health polling
madsci start --build      # rebuild images first
madsci start --services event resource  # specific services
madsci stop               # docker compose down
madsci stop --volumes     # remove volumes (data loss!)
```

### Local Mode (no Docker)
```bash
madsci start --mode=local     # All 7 managers in-process, in-memory backends
madsci start --mode=local -d  # Background with PID tracking
```

### Individual Services
```bash
madsci start manager event -d     # Start Event Manager in background
madsci start node ./my_node.py -d # Start node in background
madsci stop manager event         # Stop background Event Manager
madsci stop node my_node          # Stop background node
```

### PID Tracking
- PIDs stored in `.madsci/pids/{name}.pid` (JSON: `{pid, exe, name}`)
- Logs stored in `.madsci/logs/{name}_TIMESTAMP.log`
- Process identity verified to prevent PID reuse
- Stop sends SIGTERM, waits 5s for exit

### Health Polling (`-d` with `--wait`)
After detached start, polls `/health` on each service every 2s (timeout: 60s). Displays live Rich table with status.

## TUI Application

5 screens built with Textual:

| Screen | Key | Description |
|--------|-----|-------------|
| Dashboard | `d` | Service overview, quick actions, recent events |
| Status | `s` | Detailed health with infrastructure checks |
| Logs | `l` | Log viewer with filtering and follow mode |
| Nodes | `n` | Node registry with status and actions |
| Workflows | `w` | Workflow history and details |

- Auto-refresh every 5 seconds
- CSS theming in `tui/styles/theme.tcss`
- Trogon integration via `Ctrl+P`

## Testing CLI Commands

Use Click's `CliRunner`:

```python
from click.testing import CliRunner
from madsci.client.cli import madsci

def test_version_command():
    runner = CliRunner()
    result = runner.invoke(madsci, ["version"])
    assert result.exit_code == 0
    assert "madsci" in result.output

def test_version_json():
    runner = CliRunner()
    result = runner.invoke(madsci, ["version", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "packages" in data

def test_command_alias():
    runner = CliRunner()
    result = runner.invoke(madsci, ["s"])  # alias for "status"
    # Will fail to connect but should parse correctly
    assert result.exit_code in (0, 1)
```

**Smoke test pattern:** Verify all 17 commands parse without import errors:
```python
@pytest.mark.parametrize("cmd", ["version", "doctor", "status", ...])
def test_command_help(cmd):
    runner = CliRunner()
    result = runner.invoke(madsci, [cmd, "--help"])
    assert result.exit_code == 0
```

## Common Pitfalls

- **Lazy imports mandatory**: Heavy deps (clients, types, managers) must be imported inside function bodies, not at module top. Startup time is critical.
- **`_LazyMadsciContext`**: The context object is lazy; it only initializes `MadsciContext` when attributes are first accessed. Don't force early initialization.
- **yarn, not npm**: UI directory uses `yarn` for Node.js package management
- **Compose file discovery**: `start` searches for `compose.yaml`, `compose.yml`, `docker-compose.yaml`, `docker-compose.yml` in current and parent directories
- **ULID not UUID**: Use `new_ulid_str()` for any IDs
- **AnyUrl trailing slash**: All URLs stored via Pydantic AnyUrl get a trailing slash
- **JSON output**: All informational commands should support `--json` output mode
- **Click groups vs commands**: `start` and `stop` are Click groups with `manager`/`node` subcommands
- **Trogon patch**: The `commands` command patches Trogon's `_apply_default_value` for Click `Sentinel.UNSET` compatibility
