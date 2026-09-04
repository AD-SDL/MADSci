---
name: madsci-install
description: Install or bootstrap the MADSci stack. Use when the user asks to install MADSci, spin up the example lab, set up a new lab, run the services locally, prepare a dev environment for contributing, choose between pip / Docker / PDM / devbox, or debug install/startup failures (missing Docker, PDM/uv resolver errors, `ModuleNotFoundError`, port conflicts, `.madsci/` discovery). This skill is *interactive*: it asks the user before making non-reversible choices, resolves errors by offering the available fallbacks, and finishes by inspecting the running stack to confirm success.
---

# MADSci Install & Bootstrap

Getting MADSci running is a *branching* task, not a linear script. There are four legitimate install paths (pip client, Docker Compose, PDM dev setup, devbox shell), each with its own prerequisites and gotchas, and the right choice depends on what the user is trying to do. **Never guess for the user** — the cost of picking wrong is a wasted `pdm install`, a mangled venv, or a Docker daemon left running for something they didn't need.

This skill is interactive. Every decision that can't be inferred from the conversation MUST be resolved with the **AskUserQuestion tool** before you run a command. Every recoverable error MUST offer the user the available fallbacks rather than being retried silently.

## Bundled Reference Files

- **[install-check.sh](install-check.sh)** — the verification recipe you run at the end. Pings each manager's `/health`, checks the dashboard, prints a pass/fail matrix.
- **[troubleshooting.md](troubleshooting.md)** — install-time failure modes and their fixes, keyed by error signature. Read this the moment a command fails.

Read `troubleshooting.md` before writing your own diagnosis of a failed install command — the common ones are already catalogued.

## Step 1 — Determine the install goal

Before running anything, resolve *what the user actually wants*. If the conversation doesn't already make this obvious, ask via **AskUserQuestion**:

> **Question:** "What are you trying to do with MADSci?"
> **Header:** `Install goal`
> **Options:**
> 1. **Try the example lab** — clone the repo and `docker compose up` the shipped example. Fastest way to see MADSci running. *(Recommended for first-time users.)*
> 2. **Start a new lab** — `pip install madsci-client`, `madsci init <name>`, then `madsci start`. Right when the user has their own lab in mind.
> 3. **Install specific packages** — `pip install madsci.<pkg>` into an existing project (e.g. only the client, only the resource manager). Right when MADSci is a dependency of something else the user already has.
> 4. **Contribute to MADSci itself** — clone the repo, `just init` (PDM) or `devbox shell`, run tests. Right when the user wants to edit MADSci source.

The four goals map to four workflows below. **Announce the chosen goal back to the user in one line before proceeding** ("Installing for goal: *Try the example lab*").

## Step 2 — Check prerequisites for the chosen path

Do this *before* the first install command so you fail fast with a real question, not a cryptic tool error. Run these checks in parallel:

| Prereq | Check | Needed for |
|---|---|---|
| Python 3.10+ | `python3 --version` | all paths |
| Docker daemon | `docker info` (exit 0) | goals 1, 2 (Docker mode), 4 (integration tests) |
| `pdm` | `pdm --version` | goal 4 |
| `just` | `just --version` | goal 4 (optional — commands can be run from `.justfile` manually) |
| `uv` | `uv --version` | goal 4, only relevant if `pdm.lock` resolver mismatch appears |
| `git` | `git --version` | goals 1, 4 |
| `yarn` | `yarn --version` | goal 4, only for dashboard work in `ui/` |

If Python is < 3.10, stop and tell the user — this is a hard block, no workaround is offered by MADSci.

**Every missing prereq → AskUserQuestion.** Do not silently install system packages or invoke a package manager on the user's machine. Example when Docker is missing on a system targeting goal 1 or 2:

> **Question:** "Docker isn't installed (or the daemon isn't running). How do you want to proceed?"
> **Header:** `No Docker`
> **Options:**
> 1. **Install Docker Desktop / Engine now** — I'll open the official install docs; you install it, I'll retry. *(Recommended if you plan to run MADSci long-term.)*
> 2. **Switch to local mode (`madsci start --mode=local`)** — pure Python, no Docker. Only works for goal 2 (new lab), and needs FerretDB/PostgreSQL running elsewhere or a local sqlite fallback where supported.
> 3. **Use Rancher Desktop or Podman instead** — I'll retry against a compatible daemon.
> 4. **Abort** — stop the install.

Do the same shape of prompt for any other missing prereq you hit. Never assume the user prefers to install a system dependency.

## Step 3 — Run the install for the chosen goal

Follow only the section for the goal picked in Step 1.

### Goal 1: Try the example lab

```bash
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
docker compose up            # foreground; add -d to detach
```

- Uses host network mode → the manager ports (8001–8006) and the dashboard (8000) must all be free on the host. If `lsof -i :8000` shows a conflict, **AskUserQuestion**: stop the conflicting process, remap the port in `compose.yaml`, or abort.
- The example lab config lives at [examples/example_lab/](../../examples/example_lab/); do not modify [compose.yaml](../../compose.yaml) at the repo root without telling the user — that's the file `docker compose up` at the root uses.

### Goal 2: Start a new lab

```bash
pip install madsci-client
madsci init <lab-name>       # interactive wizard; asks for lab name, template, etc.
cd <lab-name>
madsci start                 # Docker mode (default)
# OR
madsci start --mode=local    # pure Python mode
```

- If you already ran Step 2 and Docker is available, default to Docker mode. Otherwise, if the user picked local mode in the Step 2 fallback, honor that here.
- `madsci init` may prompt for a template. Do not answer for the user — let the wizard interact, or if they want it non-interactive, use `madsci new lab --template standard <name>` and note the choice.
- See the [madsci-cli](../madsci-cli/SKILL.md) skill for the full flag reference on `init` / `start` / `stop` / `status`.

### Goal 3: Install specific packages

Package matrix (from [README.md:65-82](../../README.md#L65-L82)):

| Package | Purpose |
|---|---|
| `madsci.common` | Shared types and utilities |
| `madsci.client` | Client libraries |
| `madsci.experiment_application` | Experiment logic |
| `madsci.event_manager` | Event logging and querying (port 8001) |
| `madsci.experiment_manager` | Experiment management (port 8002) |
| `madsci.resource_manager` | Resource tracking (port 8003) |
| `madsci.data_manager` | Data capture and storage (port 8004) |
| `madsci.workcell_manager` | Workflow coordination (port 8005) |
| `madsci.location_manager` | Location management (port 8006) |
| `madsci.squid` | Lab manager with dashboard (port 8000) |
| `madsci.node_module` | Node development framework |

Confirm the exact set with the user via **AskUserQuestion** (multiSelect) before running `pip install`, unless they already listed packages by name. Always install into a venv the user names — never into system Python.

### Goal 4: Contribute to MADSci itself

Preferred path (matches [CONTRIBUTING.md](../../CONTRIBUTING.md)):

```bash
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
just init                   # installs deps + sets up pre-commit
```

Alternative if the user has [devbox](https://www.jetify.com/devbox) installed — offer this with **AskUserQuestion** only when `devbox --version` succeeds:

```bash
devbox shell                # reproducible dev shell with pinned toolchain
# then inside:
pdm install -G:all
```

**Do not silently retry `pdm install` after a resolver failure.** See the resolver branch below.

## Step 4 — Handle install-time errors

Every failure surfaces as an AskUserQuestion, not as a silent retry. The five most common failures and the questions they map to:

### 4.1 PDM resolver error (`pdm.lock` was generated by uv)

Symptom: `pdm install` (or `just init`) errors during dependency resolution, usually with a message about incompatible versions or "conflicts detected".

> **Question:** "The lockfile was generated by uv. How should I resolve this?"
> **Header:** `PDM resolver`
> **Options:**
> 1. **Install uv and switch PDM to it** — `pip install uv && pdm config use_uv true`, then retry. *(Recommended — matches the committed lockfile.)*
> 2. **Delete `pdm.lock` and regenerate** — `rm pdm.lock`, then retry. Fine locally, but do not commit the regenerated lockfile without asking.
> 3. **Abort** — stop and let me look at the raw error.

### 4.2 `ModuleNotFoundError` after install

Almost always means the wrong virtualenv is active.

> **Question:** "`ModuleNotFoundError` for a MADSci module. What's the venv situation?"
> **Header:** `Wrong venv`
> **Options:**
> 1. **Activate PDM's venv** — `eval $(pdm venv activate)` (or use `pdm run <cmd>`). *(Recommended for goal 4.)*
> 2. **Reinstall into the current venv** — I'll rerun `pip install ...` after confirming `which python`.
> 3. **Show me `which python` and `pip list | grep madsci`** — diagnose first, then decide.

### 4.3 Port already in use

Manager ports are 8001–8006, dashboard 8000, and the example lab uses host network mode so remapping requires editing `compose.yaml`.

> **Question:** "Port <N> is already in use. How do you want to resolve it?"
> **Header:** `Port conflict`
> **Options:**
> 1. **Show me what's on that port** — I'll run `lsof -i :<N>` and report; you decide.
> 2. **Stop the conflicting process** — only if you tell me exactly which one.
> 3. **Remap the port** — edit `compose.yaml` (I'll show the diff first) and retry.
> 4. **Abort**.

### 4.4 `.madsci/` sentinel not found where expected

PIDs, logs, and backups are resolved by walking up for a `.madsci/` directory, then `.git/`, then falling back to `~/.madsci/` (see [sentry.py](../../src/madsci_common/madsci/common/sentry.py) and the *Settings Directory* section of [CLAUDE.md](../../CLAUDE.md)). If `madsci status` or `madsci start` behaves like it can't find state, the CWD is probably wrong.

> **Question:** "MADSci is resolving `.madsci/` in an unexpected location (`<path>`). What do you want?"
> **Header:** `Settings dir`
> **Options:**
> 1. **Scaffold `.madsci/` in this directory** — I'll create it with the standard subdirs via `ensure_madsci_dir()`.
> 2. **Point MADSci at a different directory** — set `MADSCI_SETTINGS_DIR` or pass `--settings-dir`; you tell me the path.
> 3. **`cd` into the intended lab directory and retry** — you tell me which one.

### 4.5 Docker daemon reachable but `docker compose up` hangs on healthchecks

Usually means a manager container can reach its port but the database (FerretDB/Postgres) inside the compose network isn't up yet, or a volume from a previous run has incompatible data.

> **Question:** "Compose is stuck on healthchecks. What's the history of this stack?"
> **Header:** `Compose stuck`
> **Options:**
> 1. **Fresh start — wipe volumes** — `docker compose down -v` then `docker compose up`. *(DATA LOSS: deletes local DB volumes. Confirm before running.)*
> 2. **Tail logs first** — I'll run `docker compose logs --tail=100 <service>`; you decide.
> 3. **Give it more time** — some images pull large layers on first run; wait 60s and re-check.
> 4. **Abort**.

For anything not covered by these five, read [troubleshooting.md](troubleshooting.md) before improvising a fix.

## Step 5 — Verify the install succeeded

Do this *always*, at the end of every path. A successful install is not "the command exited 0" — it is "the stack answers correctly."

Run [install-check.sh](install-check.sh) with the goal name so it knows what to check:

```bash
bash .agents/skills/madsci-install/install-check.sh --goal <1|2|3|4>
```

The script checks (as appropriate for the goal):

1. **Python + venv sanity** — `python --version`, `which python`, `python -c "import madsci"` for each installed package.
2. **Manager health** — `curl -fsS http://localhost:<port>/health` for each manager expected to be up (8001–8006). Every `AbstractManagerBase` subclass exposes `/health` — see [manager_base.py:430](../../src/madsci_common/madsci/common/manager_base.py#L430).
3. **Dashboard** — `curl -fsS http://localhost:8000/health` (Squid / Lab Manager).
4. **CLI wiring** — `madsci status` and `madsci doctor`. `doctor` runs its own diagnostics; treat any non-green line as a real finding, not noise.
5. **Example lab only (goal 1)** — check that the seeded resources/locations appear via `madsci resource list` and `madsci location list`.

**Report the pass/fail matrix to the user verbatim, one line per check.** Do not summarize to "everything looks good" — list the actual endpoints and their statuses. If any check fails, drop back to Step 4 with the specific failure signature; do not proceed to "install complete."

Announce completion only when every requested check passes:

> ✅ MADSci install verified for goal *<goal name>*. Managers up on 8001–8006, dashboard on 8000, `madsci status` and `madsci doctor` clean.

## What this skill does NOT do

- **Does not install system dependencies** (Docker, Python, Homebrew packages, apt packages) without an explicit AskUserQuestion approval per package.
- **Does not modify `pyproject.toml`, `pdm.lock`, `.env`, or `settings.yaml`** without showing a diff and getting approval.
- **Does not run `docker compose down -v`** (destroys volumes) without a confirming AskUserQuestion.
- **Does not silence errors** with `|| true`, `2>/dev/null`, retries in a loop, or by editing linter/CI config.
- **Does not extend into node/manager/experiment implementation** — hand off to [madsci-nodes](../madsci-nodes/SKILL.md), [madsci-managers](../madsci-managers/SKILL.md), or [madsci-experiments](../madsci-experiments/SKILL.md) once the stack is up.

## Cross-references

- Repo overview and package matrix: [README.md](../../README.md)
- Contributor prereqs and `just` targets: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Devbox pinned toolchain: [devbox.json](../../devbox.json)
- Settings-directory walk-up and precedence: [CLAUDE.md](../../CLAUDE.md) (*Settings Directory (Walk-Up Discovery)*)
- Sentry (`.madsci/` resolution): [src/madsci_common/madsci/common/sentry.py](../../src/madsci_common/madsci/common/sentry.py)
- Manager health endpoint: [src/madsci_common/madsci/common/manager_base.py:430](../../src/madsci_common/madsci/common/manager_base.py#L430)
- CLI details for `init` / `start` / `stop` / `status` / `doctor`: [madsci-cli](../madsci-cli/SKILL.md)
