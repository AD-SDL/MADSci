---
name: madsci-install
description: Install, bootstrap, verify, or uninstall a MADSci lab. Use when the user wants to install MADSci, start or tear down a lab stack, choose between Docker and native (`madsci start --mode local`), point an install at existing `.madsci/` data, or debug install and startup failures such as missing Docker, ModuleNotFoundError, port conflicts, or `.madsci/` discovery. Interactive — confirms destructive choices, offers fallbacks on error, and verifies the result.
---

# MADSci Install & Bootstrap

Getting MADSci running is a branching task with one primary axis: **method** — **Docker** (full persistent stack in containers) or **local** (pure-Python, in-memory, via `madsci start --mode local`). This skill installs MADSci on the host and stands up a lab; if the user has existing MADSci data, it points the new stack at it; if not, it starts fresh.

Covers install (Steps 1–5), error recovery (Step 6), verification (Step 7), and uninstall (Step 8 → [uninstall.md](uninstall.md)).

## Rules of engagement

- **Never guess for the user.** Every decision that can't be inferred from the conversation MUST be resolved with the **AskUserQuestion tool** before you run a command.
- **Every recoverable error offers fallbacks** — never a silent retry.
- **Announce every locked-in decision** (method, existing data, UI) in a one-liner *before* running any install command in Step 5.
- **Read [troubleshooting.md](troubleshooting.md) before writing your own diagnosis** — the common failures are catalogued.

## Bundled reference files

- [install-check.sh](install-check.sh) — install verification (`--method docker|local`, `--with-ui`/`--no-ui`).
- [uninstall.md](uninstall.md) — teardown workflow (scope selection, per-method removal, data wipe).
- [uninstall-check.sh](uninstall-check.sh) — teardown verification (`--method docker|local` `--scope stop|remove|wipe`).
- [troubleshooting.md](troubleshooting.md) — failure modes keyed by error signature.

## Scope

- Install `madsci-client` (and manager packages when `--method local` needs them) on the host.
- Run `madsci init <lab-name>` to scaffold a lab directory if the user doesn't already have one.
- Point the new stack at existing MADSci data (Docker method only — bind-mounts an existing `.madsci/` from a user-specified path).
- Start the stack via `madsci start` or `madsci start --mode local`.
- Verify the install with `install-check.sh`.
- Tear the stack back down (Step 8 → [uninstall.md](uninstall.md)).

## Step 1 — Choose the install method

The one branching decision at the top of the install:

- **`docker`** — full stack (7 managers + dashboard + real databases: FerretDB, PostgreSQL, Valkey, SeaweedFS) in containers via Docker Compose. Persistent data. Matches production/CI.
- **`local`** — pure-Python install run with `madsci start --mode local`: all managers in-process with in-memory backends. No Docker, no external databases. ⚠ **Data is ephemeral and lost on restart** (mode is foreground-only, no persistence).

> **Question:** "How do you want to run MADSci — in Docker, or natively (pure Python)?"
> **Header:** `Install method`
> **Options:**
> 1. **Docker (Compose)** — full persistent stack with real databases. Needs a running Docker daemon. *(Recommended for anything beyond a quick trial.)*
> 2. **Native (`--mode local`, in-memory)** — pure Python, no Docker, no databases to install. Fast to start, but **data is ephemeral and lost on restart**. Good for a quick look or offline/unit-style work.

Native is not a lock-in — the same lab directory works with `madsci start` (Docker mode) later.

## Step 2 — Ask about existing MADSci data

Before running any install commands, ask whether the user has existing MADSci data to load into the new stack:

> **Question:** "Do you have existing MADSci data you want the new stack to use? (a `.madsci/` directory from a prior install, or a backup path)"
> **Header:** `Existing data?`
> **Options:**
> 1. **No — fresh install** — start with an empty stack, no prior data. *(Default if you're setting up MADSci for the first time on this machine.)*
> 2. **Yes — I'll give you the path** — you'll provide the absolute path to an existing `.madsci/` directory. I'll wire the new stack to it.

**If the user answers "Yes":**

- Ask for the path (a normal follow-up message, not an AskUserQuestion — the path is free-form).
- Verify the path exists and looks like a `.madsci/` directory (`ls -la <path>` — expect `postgresql/`, `mongodb/`, `valkey/`, `seaweedfs/`, `logs/`, or at minimum a `registry.json`).
- **Method-specific behavior:**
  - `--method docker`: the new lab's compose file will bind-mount this path. Practical implementation: copy or symlink the existing `.madsci/` into the new lab directory *before* `madsci start`. Symlink is reversible; copy is safer but slower.
  - `--method local`: **in-memory backends CANNOT load persisted data.** Warn the user explicitly:

    > **Question:** "You chose method `local`, but Native mode uses in-memory backends and cannot load persisted data from `.madsci/`. What do you want to do?"
    > **Header:** `Local can't load data`
    > **Options:**
    > 1. **Switch to method `docker`** — Docker can bind-mount your existing `.madsci/`. Recommended if data preservation matters.
    > 2. **Proceed with method `local`, ignore existing data** — fresh in-memory stack; existing data stays on disk untouched but won't be used.
    > 3. **Abort** — stop here so I can back up or migrate the data first.

- **Schema-version check** (Docker method only, after mounting): the Resource Manager's `DatabaseVersionChecker` will validate the schema on startup. If mismatched, `madsci start` fails with a "Database version mismatch" error. Ask:

    > **Question:** "The existing data was created by a different MADSci version. How do you want to proceed?"
    > **Header:** `Version mismatch`
    > **Options:**
    > 1. **Migrate the data to the current version** — I'll run `python -m madsci.resource_manager.migration_tool --db_url <url>` (auto-detected from the mounted data). Backups are created automatically. *(Recommended.)*
    > 2. **Load anyway, ignore the mismatch** — proceed and hope the schema is forward-compatible. Risk: manager crashes at startup.
    > 3. **Discard and start fresh** — abandon the existing data (it stays on disk, but the new stack ignores it).

## Step 3 — Include the dashboard UI?

Lab Manager on port 8000 has two personalities: **API-only** (FastAPI + `/docs` + `/health`; `GET /` returns 404 JSON), or **API + dashboard** (Vue 3 SPA mounted at `/`).

**Why the split exists:** the dashboard is a separate Vue project ([ui/](../../../ui/) — `squid_dashboard`) built with Vite; `src/madsci_squid/pyproject.toml` deliberately excludes it from the wheel, so `pip install madsci.squid` gives you API-only. The Docker `madsci_dashboard` image bakes the built bundle in ([docker/Dockerfile.dashboard](../../../docker/Dockerfile.dashboard)); Lab Manager mounts `dashboard_files_path` (default `~/MADSci/ui/dist`) at `/` only if the directory exists ([lab_server.py:48-55](../../../src/madsci_squid/madsci/squid/lab_server.py#L48-L55)).

| Method | Default UI status | Ask? |
|---|---|---|
| `docker` | ✅ Included (compose typically uses `madsci_dashboard` image) | No |
| `local` | ❌ Missing by default (pip-installed `madsci.squid` doesn't bundle it) | **Yes** |

For `--method local`, ask:

> **Question:** "Include the dashboard UI on port 8000? Without it, port 8000 serves only the FastAPI JSON API (`/docs`, `/health`, endpoints); `GET /` returns 404. Building the UI requires Node.js 18+ and yarn."
> **Header:** `Include UI?`
> **Options:**
> 1. **Yes — build the UI locally** — `cd ui && yarn install && yarn build` produces `ui/dist/`, then set `LAB_DASHBOARD_FILES_PATH=<repo>/ui/dist` before `madsci start`. Requires Node 18+ and yarn. *(Recommended if you want the dashboard.)*
> 2. **Yes — extract the UI from the `madsci_dashboard` Docker image** — `docker create` a scratch container from `ghcr.io/ad-sdl/madsci_dashboard:latest` and `docker cp /home/madsci/MADSci/ui/dist` out to a local path, then set `LAB_DASHBOARD_FILES_PATH` to that path. No Node install needed on the host, but you need Docker running just for this extraction step.
> 3. **No — API-only is fine** — `GET /` returns 404; use `/docs` for the Swagger UI. Fastest install. You can add the UI later without reinstalling.

The answer drives Step 4 prereqs (node/yarn), Step 5 subrecipe, and Step 7's `--with-ui`/`--no-ui` flag.

## Step 4 — Check prerequisites

Run in parallel *before* the first install command:

| Prereq | Check | Needed for |
|---|---|---|
| Python 3.10+ | `python3 --version` | all paths (hard block if <3.10) |
| Docker daemon | `docker info` (exit 0) | `--method docker` |
| `node` (>=18), `yarn` | `node --version && yarn --version` | UI answer = "build locally" |
| `docker` (for UI extract only) | `docker --version` | UI answer = "extract from image" (even with `--method local`) |
| Package manager (`pip` / `uv` / `pipx`) | `pip --version` etc. | needed for the host install; user picks below |

When Docker is missing and the chosen method needs it:

> **Question:** "Docker isn't installed (or the daemon isn't running). How do you want to proceed?"
> **Header:** `No Docker`
> **Options:**
> 1. **Install Docker Desktop / Engine now** — I'll open the official install docs; you install it, I'll retry. *(Recommended if you plan to run MADSci long-term.)*
> 2. **Switch to `--method local`** — pure Python, in-memory backends, no Docker; **data is ephemeral**. Not viable if Step 2 said "yes, load existing data" (in-memory cannot load).
> 3. **Abort**.

If the user takes option 2, record the method as `local` and re-run Step 3 (UI ask changes).

When Node/yarn are missing and the user chose "build the UI locally":

> **Question:** "Node.js and/or yarn are not installed, but you asked to build the dashboard UI locally. How do you want to install them?"
> **Header:** `No Node/yarn`
> **Options:**
> 1. **NodeSource + yarn via apt (system-wide, needs sudo)** — `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs && sudo npm install -g yarn`. Correct Node version (20 LTS). System-wide, requires sudo.
> 2. **nvm (per-user, no sudo)** — `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash`, then `nvm install 20 && npm install -g yarn`. User-scoped. *(Recommended if you don't want a system-wide Node install.)*
> 3. **Extract the UI from the `madsci_dashboard` Docker image instead** — switches Step 3's UI answer to option 2 (no Node needed). Only viable if Docker is available.
> 4. **Downgrade the UI answer to "No — API-only"** — skip the UI build entirely.
> 5. **Install Node/yarn yourself** — you handle it; I'll retry.

## Step 5 — Run the install

Before running any command in this step, announce the locked-in decisions in one line, e.g.:

> Installing MADSci with method *local*, existing data *none*, UI *enabled via local build*.

**Common setup (both methods):**

```bash
pip install madsci-client                    # or `uv pip install madsci-client` in a venv
madsci init <lab-name>                       # scaffolds ~/<lab-name>/ with settings.yaml, .env, .madsci/
cd <lab-name>
```

`madsci init` is interactive. If the user prefers non-interactive, use `madsci init --no-interactive --name <lab-name>` and mention the choice.

**If Step 2 said "yes, load existing data" (only viable with `--method docker`):**

Before `madsci start`, put the existing `.madsci/` in place inside the new lab directory. Two options — offer both:

> **Question:** "How do you want to attach the existing data to the new lab directory?"
> **Header:** `Attach data`
> **Options:**
> 1. **Symlink** — `rm -rf ~/<lab-name>/.madsci && ln -s <existing-path> ~/<lab-name>/.madsci`. Reversible, no data copy. Reflects future changes back to the original path.
> 2. **Copy** — `rm -rf ~/<lab-name>/.madsci && cp -a <existing-path> ~/<lab-name>/.madsci`. Independent copy; safer if the original data source shouldn't be modified. Slower for large databases.

Then start the stack based on method:

**Method = docker:**

```bash
madsci start                                 # foreground; add -d to detach
```

**Method = local:**

```bash
# In-memory managers, foreground only (Ctrl+C to stop; all data is lost)
madsci start --mode local
```

*Native mode + UI:* if Step 3's UI answer was **yes**, run the matching subrecipe *before* `madsci start --mode local`:

*UI option 1 — build locally from the repo* (requires Node 18+ and yarn):

```bash
git clone https://github.com/AD-SDL/MADSci.git ~/madsci-ui-build   # or use an existing checkout
cd ~/madsci-ui-build/ui
yarn install                                                       # ~2–5 min, ~500MB node_modules
yarn build                                                         # produces ui/dist/
export LAB_DASHBOARD_FILES_PATH=~/madsci-ui-build/ui/dist
```

*UI option 2 — extract prebuilt bundle from the `madsci_dashboard` Docker image* (requires Docker):

```bash
docker pull ghcr.io/ad-sdl/madsci_dashboard:latest
CID=$(docker create ghcr.io/ad-sdl/madsci_dashboard:latest)
mkdir -p ~/madsci-ui-bundle
docker cp "$CID":/home/madsci/MADSci/ui/dist/. ~/madsci-ui-bundle/
docker rm "$CID"
export LAB_DASHBOARD_FILES_PATH=~/madsci-ui-bundle
```

Persist `LAB_DASHBOARD_FILES_PATH=<path>` in `~/<lab-name>/.env` so it survives shell restarts. If Step 3's UI answer was **no**, just run `madsci start --mode local`; `/` returns 404 JSON, `/docs` still works.

## Step 6 — Handle install-time errors

The most common failures and the questions they map to:

### 6.1 `ModuleNotFoundError` after install

Almost always means the wrong virtualenv is active, or `--method local` is missing manager packages (`pip install madsci-client` alone is not enough for `madsci start --mode local` — it needs every manager package too: `madsci.event_manager`, `madsci.experiment_manager`, `madsci.resource_manager`, `madsci.data_manager`, `madsci.workcell_manager`, `madsci.location_manager`, `madsci.squid`).

> **Question:** "`ModuleNotFoundError` for a MADSci module. What's the situation?"
> **Header:** `Missing module`
> **Options:**
> 1. **Missing manager package (--method local)** — install every manager: `pip install madsci.event_manager madsci.experiment_manager madsci.resource_manager madsci.data_manager madsci.workcell_manager madsci.location_manager madsci.squid madsci.node_module madsci.experiment_application`. *(Recommended if the error names a manager module.)*
> 2. **Wrong venv active** — I'll show `which python` and `pip list | grep madsci`; you activate the right one.
> 3. **Reinstall into the current venv** — I'll rerun `pip install ...` after confirming `which python`.

### 6.2 Port already in use

Manager ports are 8001–8006, dashboard 8000.

> **Question:** "Port <N> is already in use. How do you want to resolve it?"
> **Header:** `Port conflict`
> **Options:**
> 1. **Show me what's on that port** — I'll run `lsof -i :<N>` and report; you decide.
> 2. **Stop the conflicting process** — only if you tell me exactly which one.
> 3. **Remap the port** — edit the lab's `settings.yaml` (I'll show the diff first) and retry.
> 4. **Abort**.

### 6.3 `.madsci/` sentinel not found where expected

PIDs, logs, and backups are resolved by walking up for a `.madsci/` directory, then `.git/`, then falling back to `~/.madsci/` ([sentry.py](../../../src/madsci_common/madsci/common/sentry.py)). If `madsci status` or `madsci start` behaves like it can't find state, the CWD is probably wrong.

> **Question:** "MADSci is resolving `.madsci/` in an unexpected location (`<path>`). What do you want?"
> **Header:** `Settings dir`
> **Options:**
> 1. **Scaffold `.madsci/` in this directory** — I'll create it with the standard subdirs via `ensure_madsci_dir()`.
> 2. **Point MADSci at a different directory** — set `MADSCI_SETTINGS_DIR` or pass `--settings-dir`; you tell me the path.
> 3. **`cd` into the intended lab directory and retry** — you tell me which one.

### 6.4 Docker daemon reachable but `docker compose up` hangs on healthchecks

A manager container can reach its port but the database (FerretDB/Postgres) inside the compose network isn't up yet, or a volume from a previous run has incompatible data.

> **Question:** "Compose is stuck on healthchecks. What's the history of this stack?"
> **Header:** `Compose stuck`
> **Options:**
> 1. **Fresh start — wipe volumes** — `docker compose down -v` then `docker compose up`. *(DATA LOSS: deletes local DB volumes. Confirm before running.)*
> 2. **Tail logs first** — I'll run `docker compose logs --tail=100 <service>`; you decide.
> 3. **Give it more time** — some images pull large layers on first run; wait 60s and re-check.
> 4. **Abort**.

### 6.5 Schema version mismatch on Resource Manager startup

`ResourceManager` runs a `DatabaseVersionChecker` on init that compares the installed MADSci version against `madsci_schema_version` in the mounted database. Mismatch → the manager refuses to start and the whole stack aborts.

> **Question:** "Resource Manager reports 'Database schema version mismatch detected'. How do you want to proceed?"
> **Header:** `Schema mismatch`
> **Options:**
> 1. **Run the migration tool** — `python -m madsci.resource_manager.migration_tool --db_url <url>` (backups automatic). *(Recommended.)*
> 2. **Discard mounted data and start fresh** — remove the schema-version row (or the whole DB dir) and let the manager initialize a new schema. DATA LOSS in the resource DB.
> 3. **Abort** — you'll handle the migration manually.

For anything else, read [troubleshooting.md](troubleshooting.md) before improvising.

## Step 7 — Verify the install succeeded

Always run at the end — "command exited 0" ≠ "stack answers correctly."

```bash
bash .agents/skills/madsci-install/install-check.sh --method <docker|local> [--with-ui | --no-ui]
```

If `--with-ui`/`--no-ui` is omitted, the script infers from method (`docker → --with-ui`, `local → --no-ui`). Override when your install differs from the default (e.g. Native install with a local UI build → `--with-ui`).

The script checks:

1. **Python + venv sanity** — version, `which python`, `import madsci.*` for `common`, `client`, `squid`.
2. **Docker daemon** — required for `--method docker`; skip cleanly for `--method local`.
3. **Manager health** — `curl` `http://localhost:<port>/health` for each manager (8001–8006).
4. **Dashboard health** — `curl http://localhost:8000/health`.
5. **Dashboard UI** — `curl http://localhost:8000/` and inspect content-type; `--with-ui` expects HTML, `--no-ui` expects JSON 404.
6. **CLI wiring** — `madsci status` and `madsci doctor`.

**Report the pass/fail matrix verbatim, one line per check.** Do not summarize. If any check fails, drop back to Step 6 with the failure signature; do not announce completion.

Announce completion only when every check passes:

> ✅ MADSci install verified with method *<docker|local>* and dashboard UI *<enabled | API-only>*. Managers up on 8001–8006, dashboard on 8000 (HTML at `/` | JSON API only), `madsci status` and `madsci doctor` clean.

## Step 8 — Uninstall / tear down

If the user wants to **remove** MADSci, load [uninstall.md](uninstall.md) and follow it — full teardown workflow with scope selection (`stop` / `remove` / `wipe`), per-method removal, data wipe, and verification via `uninstall-check.sh`.

## What this skill does NOT do

Beyond the Rules of engagement above:

- **Does not install system dependencies** (Docker, Node, Python, apt/brew packages) without an explicit per-package AskUserQuestion.
- **Does not modify version-controlled files** without showing a diff and getting approval.
- **Does not `pip uninstall` from an unconfirmed environment** — always checks `which python` / `pip show` first; never system Python.
- **Does not silence errors** with `|| true`, `2>/dev/null`, retry loops, or by editing linter/CI config.
- **Does not extend into implementation** — hand off to [madsci-nodes](../madsci-nodes/SKILL.md), [madsci-managers](../madsci-managers/SKILL.md), or [madsci-experiments](../madsci-experiments/SKILL.md) once the stack is up.

## Cross-references (not linked inline above)

- Backup & recovery (before a Full wipe): [docs/guides/operator/03-backup-recovery.md](../../../docs/guides/operator/03-backup-recovery.md)
- Updates & maintenance (stop services, upgrade/downgrade): [docs/guides/operator/05-updates-maintenance.md](../../../docs/guides/operator/05-updates-maintenance.md)
- CLI details for `init` / `start` / `stop` / `status` / `doctor`: [madsci-cli](../madsci-cli/SKILL.md)
