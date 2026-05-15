# MADSci CLI Command Reference

Detailed reference for every `madsci` command. SKILL.md links here when you need the full surface area; for the architecture and authoring workflow stay in SKILL.md.

## Contents

- [version](#version)
- [doctor](#doctor-alias-doc)
- [status](#status-alias-s)
- [logs](#logs-alias-l)
- [tui](#tui-alias-ui)
- [registry](#registry)
- [migrate](#migrate)
- [new](#new-alias-n)
- [start](#start)
- [stop](#stop)
- [init](#init)
- [validate](#validate-alias-val)
- [run](#run)
- [completion](#completion)
- [backup](#backup)
- [commands](#commands-alias-cmd)
- [config](#config-alias-cfg)
- [Manager interaction commands](#manager-interaction-commands)

## `version`
Display installed MADSci package versions, Python info, platform.
- `--json`, `--check-updates`

## `doctor` (alias: `doc`)
System diagnostics: Python version, virtualenv, Docker, port availability.
- `--fix`, `--check [python|docker|ports|network]`, `--json`

## `status` (alias: `s`)
Show health of MADSci services (hits `/health` endpoints).
- `[services]` args, `-w/--watch`, `--interval`, `--timeout`, `--json`

## `logs` (alias: `l`)
View/stream logs from Event Manager.
- `-f/--follow`, `--tail N`, `--since 5m/1h/1d`, `--level`, `--grep`, `--json`

## `tui` (alias: `ui`)
Launch Textual terminal UI with 9 main screens + 5 detail/modal screens.
- `--screen [dashboard|status|logs|nodes|workflows|experiments|resources|locations|data]`
- Keybindings: `d/s/l/n/w/e/i/o/b` (screens), `r` (refresh), `q` (quit), `?` (help), `Ctrl+P` (command palette)

## `registry`
Manage ID Registry (ULID mappings for component names).
- Subcommands: `list [--type] [--include-stale]`, `resolve <name>`, `clean`

## `migrate`
Upgrade from deprecated definition files to Settings + ID Registry.
- Subcommands: `scan [dir]`, `convert [--all]`, `status`, `finalize`

## `new` (alias: `n`)
Create new components from templates. Interactive parameter prompts.
- Subcommands: `lab`, `module`, `node`, `interface`, `experiment`, `workflow`
- `--tui` launches Textual template browser

## `start`
Start MADSci services.
- `-d/--detach`, `--build`, `--services`, `--mode [docker|local]`, `--wait/--no-wait`, `--settings-dir`
- Subcommands: `manager <name> [-d]`, `node <path> [-d]`
- Docker mode: finds compose file, runs `docker compose up`
- Local mode: all 7 managers in-process with in-memory backends (no Docker)

## `stop`
Stop MADSci services.
- `--remove`, `--volumes` (requires confirmation), `--config`
- Subcommands: `manager <name>`, `node <name>`

## `init`
Initialize new MADSci lab (scaffolds `.madsci/`, settings, templates).
- `[directory]`, `--template [minimal]`, `--name`, `--description`, `--no-interactive`

## `validate` (alias: `val`)
Validate YAML configuration files (workflow, node, manager definitions).
- `[paths]`, `--json`

## `run`
Execute workflows or experiments.
- Subcommands: `workflow <path> [--parameters JSON] [--no-wait]`, `experiment <path>`

## `completion`
Generate shell completion scripts.
- `<shell>` arg: `bash`, `zsh`, `fish`

## `backup`
Database backup management (re-exports from `madsci.common.backup_tools.cli`).
- Subcommands: `create --db-url`, `restore --backup --db-url`, `validate --backup --db-url`
- Auto-detects PostgreSQL vs MongoDB/FerretDB

## `commands` (alias: `cmd`)
Launch Trogon interactive command palette (TUI forms for all commands).

## `config` (alias: `cfg`)
Configuration management with secret redaction.
- Subcommands: `export [manager_type] [--all] [-o path] [--format yaml|json] [--include-secrets]`, `create manager <type>`

## Manager Interaction Commands

Eight command groups provide direct access to manager APIs. Each resolves the manager URL from the lab context automatically.

| Command | Alias | Subcommands |
|---------|-------|-------------|
| `workflow` | `wf` | list, show, submit, pause, resume, cancel, retry, resubmit |
| `resource` | `res` | list, get, create, delete, restore, tree, lock, unlock, quantity, template, history |
| `location` | `loc` | list, get, create, create-from-template, delete, resources, attach, detach, set-repr, remove-repr, transfer-graph, plan-transfer, export, import, template, rep-template |
| `node` | `nd` | list, info, status, state, log, admin, action, action-result, action-history, config, set-config, add, shell |
| `experiment` | `exp` | list, get, start, run, pause, continue, cancel, end |
| `campaign` | `camp` | create, get |
| `data` | `dt` | list, get, metadata, submit, query |
| `events` | `ev` | query, get, archive, purge, backup |

All commands support `--json` for machine-readable output. URL resolution follows: explicit `--<manager>-url` flag > lab context > localhost default.

Command modules are in `src/madsci_client/madsci/client/cli/commands/` (one file per group).
