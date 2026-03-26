# Agent Skills Reference

MADSci includes four domain-specific **skills** for AI coding agents (Claude Code, etc.). These skills auto-load contextual knowledge about MADSci's architecture, patterns, and conventions when working on relevant code, reducing errors and improving code quality.

## Available Skills

| Skill | Trigger | What It Teaches |
|-------|---------|-----------------|
| `madsci-nodes` | Node module code | AbstractNode, RestNode, `@action` decorator, file parameters, lifecycle, testing |
| `madsci-experiments` | Experiment code | 4 modalities (Script, Notebook, TUI, Node), lifecycle, `manage_experiment()` |
| `madsci-managers` | Manager services | AbstractManagerBase, settings, DB handlers, clients, health checks |
| `madsci-cli` | CLI commands | Click commands, lazy loading, templates, start/stop, output helpers, TUI |

## How Skills Work

Skills are defined in `.agents/skills/madsci-*/SKILL.md` (symlinked from `.claude/skills/`). Each contains:

- **Frontmatter** with a `name` and `description` that tells the agent when to activate
- **Reference content** covering architecture, key files, code patterns, testing approaches, and common pitfalls

### Automatic Activation

Skills are **model-invocable** — the agent automatically loads the relevant skill when it detects you're working on related code. For example, asking "add a new action to the plate reader node" will auto-load `madsci-nodes`.

### Manual Activation

You can explicitly invoke a skill in Claude Code with a slash command:

```
/madsci-nodes
/madsci-experiments
/madsci-managers
/madsci-cli
```

This is useful when you want to preload context before asking a question.

## Skill Summaries

### madsci-nodes

Covers the node module development workflow for wrapping laboratory instruments behind MADSci's standard API.

**Key topics:**
- `AbstractNode` → `RestNode` class hierarchy
- `@action` decorator usage, parameter types (`Path` for files, `LocationArgument`, `Annotated`)
- Return types: plain dict, `Path`, `ActionFiles`, `ActionDatapoints`, tuples
- Node lifecycle: `startup_handler()` → status/state loops → `shutdown_handler()`
- REST 3-phase action execution (create → upload → start → poll → result)
- Resource/location template registration via `ClassVar` lists
- Testing with `start_node(testing=True)` and `TestClient`

### madsci-experiments

Covers the four experiment modalities and experiment lifecycle management.

**Key topics:**
- Choosing a modality: Script (batch), Notebook (Jupyter), TUI (interactive), Node (REST)
- `ExperimentDesign` (template) vs `Experiment` (runtime instance)
- `manage_experiment()` context manager for safe lifecycle handling
- Client access via `MadsciClientMixin` (7 lazy client properties)
- Pause/cancel handling with `check_experiment_status()`
- Modality-specific patterns (Notebook cell workflow, TUI thread-safe events)

### madsci-managers

Covers the 7 manager services and their implementation patterns.

**Key topics:**
- `AbstractManagerBase[SettingsT]` with `classy_fastapi.Routable`
- Settings: `prefixed_alias_generator()`, env prefixes, secret marking, `model_dump_safe()`
- 4 database handler ABCs with real + in-memory implementations
- Manager-specific details (ports, DB types, key endpoints, unique features)
- `EventClient` dual nature (logging + HTTP), `MadsciClientMixin` lazy init
- Health check overrides, OpenTelemetry integration
- Testing with in-memory handlers (no Docker required)

### madsci-cli

Covers the `madsci` command-line interface architecture and extension.

**Key topics:**
- Click-based CLI with `AliasedGroup` and lazy loading via `_LAZY_COMMANDS`
- Step-by-step guide for adding new commands
- 17 commands with aliases and key flags
- Template system (26 templates, `template.yaml` manifests, Jinja2)
- Start/stop lifecycle (Docker vs local mode, PID tracking, health polling)
- Output helpers (`get_console()`, `success()`, `error()`, etc.)
- Testing with Click's `CliRunner`

## Skills in Generated Projects

When you scaffold a new project using `madsci new` or `madsci init`, the relevant agent skills are automatically copied into the generated project's `.agents/skills/` directory. This means AI coding agents working on the generated project will have MADSci domain knowledge from day one, without any manual setup.

The skills included depend on the template category:

| Template Category | Skills Included |
|-------------------|----------------|
| Module, Node, Interface, Comm | `madsci-nodes` |
| Experiment | `madsci-experiments` |
| Workflow, Workcell | `madsci-nodes`, `madsci-managers`, `madsci-cli` |
| Lab | All 4 skills |

The skill files are output to `.agents/skills/{skill-name}/SKILL.md` in the generated project directory. No additional configuration is needed.

## Customizing Skills

Skills live in `.agents/skills/` and are symlinked into `.claude/skills/`. To modify a skill, edit the `SKILL.md` file directly. The frontmatter controls when the skill activates:

```yaml
---
name: madsci-nodes
description: Working with MADSci node modules for laboratory instrument integration...
---
```

The `description` field is what the agent uses to decide whether to auto-load the skill, so keep it specific and action-oriented.

## Other Available Skills

In addition to the MADSci-specific skills, the project includes two general coding quality skills:

- **`galahad`** — Testing, types, lints, and coverage best practices
- **`code-ratchets`** — Preventing proliferation of deprecated code patterns via pre-commit ratchets
