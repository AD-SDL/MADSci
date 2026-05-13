---
name: madsci-cli
description: Working with the MADSci CLI (the `madsci` command). Use when adding, modifying, or debugging CLI commands, or when using the CLI to operate a MADSci lab.
---

# MADSci CLI

The `madsci` CLI is built on Click with lazy command loading, Rich output formatting, and a Textual TUI. It provides 26 commands for managing MADSci labs.

## Reference Files

Detailed material is in `reference/`. Read the relevant file when the task touches that area:

- **Command Reference** — every command's flags, subcommands, and behavior. See [reference/commands.md](reference/commands.md).
- **Template System** — manifest format, categories, Jinja2 filters, Pydantic alignment. See [reference/templates.md](reference/templates.md).

## Key Files

| File | Purpose |
|------|---------|
| `src/madsci_client/madsci/client/cli/__init__.py` | Root command, `AliasedGroup`, `_LAZY_COMMANDS` |
| `src/madsci_client/madsci/client/cli/commands/` | 26 command modules |
| `src/madsci_client/madsci/client/cli/utils/output.py` | Rich console output helpers |
| `src/madsci_client/madsci/client/cli/tui/app.py` | Textual TUI application |
| `src/madsci_client/madsci/client/cli/tui/styles/theme.tcss` | TUI CSS theme |
| `src/madsci_common/madsci/common/bundled_templates/` | 33 template manifests + Jinja2 files |

## Architecture

```
madsci (AliasedGroup)
  ├── Global options: --lab-url, -v, -q, --no-color, --json, --version
  ├── Context: MadsciContext (lazy), Console, verbosity flags
  └── Commands (lazy-loaded via _LAZY_COMMANDS):
      ├── version, doctor (doc), status (s), logs (l)
      ├── tui (ui), registry, migrate, new (n)
      ├── start, stop, init, validate (val)
      ├── run, completion, backup, add
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
    "workflow": ("madsci.client.cli.commands.workflow", "workflow"),
    "resource": ("madsci.client.cli.commands.resource", "resource"),
    "location": ("madsci.client.cli.commands.location", "location"),
    "node": ("madsci.client.cli.commands.node", "node"),
    "experiment": ("madsci.client.cli.commands.experiment", "experiment"),
    "campaign": ("madsci.client.cli.commands.campaign", "campaign"),
    "data": ("madsci.client.cli.commands.data", "data"),
    "events": ("madsci.client.cli.commands.events", "events"),
    "add": ("madsci.client.cli.commands.add", "add"),
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
        "wf": "workflow",
        "res": "resource",
        "loc": "location",
        "nd": "node",
        "exp": "experiment",
        "camp": "campaign",
        "dt": "data",
        "ev": "events",
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

9 main screens + 5 detail/modal screens built with Textual:

| Screen | Key | Description |
|--------|-----|-------------|
| Dashboard | `d` | Service overview, quick actions, recent events |
| Status | `s` | Detailed health with infrastructure checks |
| Logs | `l` | Log viewer with filtering and follow mode |
| Nodes | `n` | Node registry with status and actions |
| Workflows | `w` | Workflow history and details |
| Experiments | `e` | Experiment listing with search/filter and detail panels |
| Resources | `i` | Resource inventory with search/filter and detail panels |
| Data Browser | `b` | Data capture browsing and querying |
| Locations | `o` | Location management with resource attachments |

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

**Smoke test pattern:** Verify all 26 commands parse without import errors:
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
