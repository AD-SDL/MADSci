---
name: madsci-install
description: Install, bootstrap, verify, or uninstall a MADSci lab (Docker Compose). Use when the user wants to install MADSci, start or tear down a lab stack, point an install at existing `.madsci/` data, or debug install and startup failures such as missing Docker, port conflicts, or `.madsci/` discovery. Interactive — confirms destructive choices, offers fallbacks on error, and verifies the result.
---

# MADSci Install & Bootstrap

Getting MADSci running on a host via Docker Compose: a full persistent stack with 7 managers + dashboard + real databases (FerretDB with its own PostgreSQL backend, a second standalone PostgreSQL for the Resource Manager, Valkey, and SeaweedFS). If the user has existing MADSci data, attach it; if not, start fresh.

**The one architectural constraint everything else follows from:** `examples/example_lab/compose.yaml` has relative bind-mounts (`../../src`, `../../.madsci`) that resolve from the *compose file's own directory*, so they only work when it sits inside a MADSci repo clone. The install therefore clones the repo and runs the compose **in place**. Never copy, fetch, or edit that compose file into a separate directory, and never rewrite it to use absolute paths — doing so mounts an empty host directory over the installed MADSci source and nothing works.

Covers install (Steps 1–5), error recovery (Step 6), verification (Step 7), and uninstall (Step 8 → [uninstall.md](uninstall.md)).

## Rules of engagement

- **Never guess for the user.** Every decision that can't be inferred from the conversation MUST be resolved with the **AskUserQuestion tool** before you run a command.
- **Gate all "needs sudo / may require consent" questions UP FRONT** (Step 1). Once the user has consented, the install runs to completion without coming back for more approvals.
- **Every recoverable error offers fallbacks** — never a silent retry.
- **Announce every locked-in decision** (Docker install, existing data, UI) in a one-liner *before* running any install command in Step 5.
- **Read [troubleshooting.md](troubleshooting.md) before writing your own diagnosis** — the common failures are catalogued.

## Bundled reference files

- [install-check.sh](install-check.sh) — install verification (`--install-dir <path>` to probe the stack venv; `--with-ui`/`--no-ui`).
- [uninstall.md](uninstall.md) — teardown workflow (scope selection, Docker removal; `.madsci/` data deletion is handed to the operator, never run by the skill).
- [uninstall-check.sh](uninstall-check.sh) — teardown verification (`--scope stop|remove`, plus verify-only `wipe`).
- [troubleshooting.md](troubleshooting.md) — failure modes keyed by error signature.

## Scope

- Install `curl`, Docker, and `uv` if missing, with up-front consent (Step 1.0, 1.1, 1.4).
- Ask for `$INSTALL_DIR` (default `~/MADSci`) — the single directory holding the repo clone, the `.venv/`, and the stack-created `.madsci/` data (Step 1.2).
- Create a project-local venv at `$INSTALL_DIR/.venv/` with `uv` and install `madsci-client` into it — host CLI only; manager code runs in the containers (Step 5.B).
- Start the stack from `$INSTALL_DIR`, scoped to either **core stack only** (7 managers + databases) or the **full example lab** (adds demo nodes), per Step 1.3.
- Handle three starting states (Step 2): fresh install, existing `.madsci/` data to attach, or a user's own complete lab directory used as-is (no clone, no `madsci init`, no edits to their config).
- Verify with `install-check.sh` (Step 7); tear down via [uninstall.md](uninstall.md) (Step 8).

## Step 1 — Up-front consent (one and done)

Ask every "needs sudo / needs network / may surprise the user" question **now**, before any state changes. Once the user answers, the install runs autonomously.

### 1.0 — Confirm `curl` is available (needed by the installers below)

The Docker option in 1.1 and the `uv` option in 1.4 both work by piping `curl` into `sh`, so a missing `curl` has to be caught *before* either question is asked — otherwise a user who consents to "install Docker now" hits `curl: command not found` mid-install, after they already said yes. Run this first:

```bash
command -v curl >/dev/null 2>&1 && echo "curl: present" || echo "curl: MISSING"
```

If present, skip the question below. If missing:

> **Question:** "`curl` isn't installed. The Docker and `uv` installers below both need it. How do you want to proceed?"
> **Header:** `Install curl?`
> **Options:**
> 1. **Yes — install curl now (requires sudo)** — I'll run `sudo apt-get update && sudo apt-get install -y curl` (Debian/Ubuntu) or the equivalent for your distro. *(Recommended.)*
> 2. **No — I'll install it myself and come back** — stop here with instructions; re-invoke once `curl --version` works.
> 3. **Abort**.

Record the consent and continue — do **not** re-prompt in Step 4.

### 1.1 — Confirm Docker install

Run this first — do not skip straight to the question below without executing it:

```bash
docker info >/dev/null 2>&1 && echo "docker: reachable" || echo "docker: NOT reachable"
```

If it's already up, skip the question. If it's missing or the daemon isn't running:

> **Question:** "Docker isn't installed (or the daemon isn't running). To make this install unattended, I can install Docker now via the official convenience script. This needs `sudo` and will add your user to the `docker` group. Proceed?"
> **Header:** `Install Docker?`
> **Options:**
> 1. **Yes — install Docker now (apt + convenience script, requires sudo)** — I'll run `curl -fsSL https://get.docker.com | sudo sh` then `sudo usermod -aG docker $USER`. On Ubuntu/Debian this is the official supported path. You may need to log out/in or `newgrp docker` once; I'll handle it in-session. *(Recommended for unattended installs.)*
> 2. **No — I'll install Docker myself and come back** — I'll stop here with instructions; re-invoke this skill once `docker info` works.
> 3. **Abort**.

If option 2 or 3, stop with a one-line reason and don't touch anything else. If option 1, record the consent and continue — do **not** re-prompt later.

### 1.2 — Choose the install directory

One directory — `$INSTALL_DIR` — holds the repo clone, the venv (`.venv/`), and the `.madsci/` data the stack creates on first `docker compose up`. They live together because of the in-place compose constraint above. For **Step 2 Options 1 and 2** (fresh or data-only install), `$INSTALL_DIR` **is** the MADSci repo clone. Ask up front:

> **Question:** "Where do you want to install MADSci? This directory will hold the MADSci repo clone (code), `.venv/` (the `madsci` CLI venv), and `.madsci/` (DB data) — everything the install creates lives under it, nothing is written to system Python or outside it. Default: `~/MADSci`."
> **Header:** `Install directory`
> **Options:**
> 1. **Use `~/MADSci` (recommended default)** — I'll `git clone https://github.com/AD-SDL/MADSci ~/MADSci`.
> 2. **I'll give you a different path** — follow-up free-form message with the absolute path (e.g. `/opt/madsci`, `~/labs/alpha`). I'll clone there.
> 3. **I already have a MADSci clone — I'll point you at it** — follow-up free-form message with the absolute path to the existing clone.
> 4. **Abort**.

Record the resolved absolute path as `$INSTALL_DIR` and lock it in — it'll feed every subsequent step. Expand `~`:

```bash
INSTALL_DIR="$(python3 -c 'import os,sys;print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "<user-answer>")"
```

**Pre-flight checks on `$INSTALL_DIR`:**

- Option 1/2 (will clone): the path must either not exist, or exist and be an empty directory. If it exists and is non-empty, re-ask (don't overwrite).
- Option 3 (existing clone): verify it's actually a MADSci repo before using it:

  ```bash
  [[ -f "$INSTALL_DIR/compose.yaml" && -f "$INSTALL_DIR/examples/example_lab/compose.yaml" && -d "$INSTALL_DIR/src" ]] \
    || { echo "Not a MADSci repo at $INSTALL_DIR (missing compose.yaml / examples/example_lab/compose.yaml / src/)" >&2; exit 1; }
  ```

For **Install Option 3** (full prior lab directory — handled in Step 2), `$INSTALL_DIR` is the user's own lab directory and is asked there. Skip this question in that case; Step 2 covers it.

### 1.3 — Choose install profile (core stack vs. full example lab)

The repo's `examples/example_lab/compose.yaml` defines both the core MADSci stack **and** a set of demo node containers (`liquidhandler_1`, `liquidhandler_2`, `robotarm_1`, `platereader_1`, `advanced_example_node`, `sila_example_server`). The demo nodes are useful for learning MADSci; they are **not** useful for a user who wants to run their own nodes against a bare stack.

Ask now so Step 5 can pick the right `docker compose up` service list:

> **Question:** "Which services do you want to run?"
> **Header:** `Install profile`
> **Options:**
> 1. **Core stack only** — 7 managers (`lab_manager`, `event_manager`, `experiment_manager`, `resource_manager`, `data_manager`, `location_manager`, `workcell_manager`) + their databases (FerretDB, Postgres, Valkey, SeaweedFS, pulled in via `depends_on`). No example nodes. *(Recommended if you plan to run your own nodes against the stack.)*
> 2. **Full example lab** — core stack + all example-lab node containers (liquid handlers, robot arm, plate reader, advanced example node, SiLA example server). *(Recommended if you're exploring MADSci for the first time.)*

This is an **install-time** choice only — `docker compose up -d <service>` / `docker compose stop <service>` can add or drop demo nodes later. Record the choice for Step 5.E. Skip the question only if the user already stated a preference in the invoking message (e.g. "install the full example lab" / "just the managers").

### 1.4 — Confirm `uv` is available (venv tool)

The install uses [`uv`](https://docs.astral.sh/uv/) to create the venv at `$INSTALL_DIR/.venv/` (see 5.B). Run this first — do not skip straight to the question below without executing it:

```bash
uv --version >/dev/null 2>&1 && echo "uv: present" || echo "uv: MISSING"
```

If it's already on PATH, skip the question. If not:

> **Question:** "`uv` isn't installed. The install needs it to create a dedicated venv for the `madsci` CLI inside the stack directory. How do you want to proceed?"
> **Header:** `Install uv?`
> **Options:**
> 1. **Yes — install `uv` now (official standalone installer, no sudo)** — I'll run `curl -LsSf https://astral.sh/uv/install.sh | sh`. Writes to `~/.local/bin/uv`. *(Recommended.)*
> 2. **I already have another tool (`pipx install uv` / `pip install --user uv`)** — tell me how you want to install it; I'll run that command.
> 3. **No — I'll install it myself and come back** — stop here with instructions; re-invoke once `uv --version` works.
> 4. **Abort**.

Record the consent and continue — do **not** re-prompt in Step 4.

## Step 2 — Ask what the user already has

Before running any install commands, find out which of three starting states the user is in. This drives whether Step 5 scaffolds a lab from scratch, or just points `madsci start` at an existing one.

> **Question:** "What do you already have on this host?"
> **Header:** `Starting state`
> **Options:**
> 1. **Nothing — fresh install** — no prior MADSci data on this host. I'll start the example-lab stack directly from `$INSTALL_DIR` (chosen in Step 1.2); the stack will create a fresh `.madsci/` at `$INSTALL_DIR/.madsci/`. *(Default for a first-time install.)*
> 2. **Existing `.madsci/` data only** (e.g. a backup, or the DB directories from a prior run) — no `settings.yaml` / `compose.yaml` alongside it. I'll attach your `.madsci/` at `$INSTALL_DIR/.madsci/` and start the stack from `$INSTALL_DIR`.
> 3. **A full prior lab directory** containing `settings.yaml`, `.env`, `compose.yaml`, and `.madsci/` (one you set up yourself with your own compose). I'll just `cd` into it and start the stack — no clone, no `madsci init`, no overwrites of your config.

Ask for the path as a free-form follow-up message (not an AskUserQuestion). Then:

**Option 2 (data only):**

- Verify the path looks like a `.madsci/` directory: `ls -la <path>` should show `postgresql/`, `mongodb/`, `valkey/`, `seaweedfs/`, `logs/`, or at minimum `registry.json`. If it also contains `settings.yaml` or `compose.yaml`, you're probably in Option 3 — stop and re-confirm with the user.
- Hand off to Step 5's "attach data" sub-step, which symlinks or copies the existing `.madsci/` into `$INSTALL_DIR/.madsci/` before `madsci start`.

**Option 3 (full lab directory):**

- Verify the directory actually contains all three: `settings.yaml`, `.env` (or `.env.example`), `compose.yaml`. If any are missing, treat it as Option 2 instead and re-confirm with the user.
- Verify the user's compose doesn't have unresolved relative bind-mounts (`grep -nE '\.\./' <path>/compose.yaml` — flag any `../...` paths and ask the user to confirm they resolve). The whole reason the install uses the MADSci repo in-place is that `../../src` and `../../.madsci` only work from inside the repo.
- Record the path; Step 5 will skip the clone step and run `madsci start` from this directory.
- Do **not** modify any file in this directory without an explicit AskUserQuestion — the user owns this config.

**Schema-version check** (Options 2 and 3): the Resource Manager's `DatabaseVersionChecker` validates the schema on startup. If mismatched, `madsci start` fails with "Database schema version mismatch." Ask:

> **Question:** "The existing data was created by a different MADSci version. How do you want to proceed?"
> **Header:** `Version mismatch`
> **Options:**
> 1. **Migrate the data to the current version** — I'll run `python -m madsci.resource_manager.migration_tool --db_url <url>` (auto-detected from the mounted data; snake_case flag — the kebab-case form is silently discarded by pydantic-settings). Backups are created automatically. *(Recommended.)*
> 2. **Load anyway, ignore the mismatch** — proceed and hope the schema is forward-compatible. Risk: manager crashes at startup.
> 3. **Discard and start fresh** — abandon the existing data (it stays on disk, but the new stack ignores it).

## Step 3 — Include the dashboard UI?

Default **yes** for Docker: the compose files typically reference the `madsci_dashboard` image which bakes in the built UI, so you get the dashboard for free. Only ask if the user wants to explicitly skip it (e.g. for a slim API-only compose).

> **Question:** "Include the dashboard UI on port 8000? Default is yes — the Docker compose uses the `madsci_dashboard` image which bundles the Vue UI."
> **Header:** `Include UI?`
> **Options:**
> 1. **Yes — use the dashboard image (default)** — compose stays as-is; `/` serves the Vue dashboard. *(Recommended.)*
> 2. **No — slim API-only compose** — swap the `lab_manager` service to the base `madsci` image. `/` returns 404 JSON; `/docs` still works.

The answer drives Step 7's `--with-ui`/`--no-ui` flag.

## Step 4 — Check prerequisites

Run these in parallel *before* the first install command. All five are **hard blocks**: `python3 --version` (3.10+, required by the `madsci` CLI), `docker info` (exit 0), `uv --version`, `curl --version`, and `git --version` (only when Step 1.2 chose to clone).

Step 1 should already have put `curl` (1.0), Docker (1.1), and `uv` (1.4) in place, so this is a confirmation pass, not a prompting one. If something is still missing, stop and tell the user — do **not** re-prompt mid-step.

`curl` is a hard block because every HTTP assertion in `install-check.sh` runs through it — without it the verification step can't tell a healthy stack from a dead one. Checking it here, next to `docker info`, is what lets the script assume it exists. Note that `uninstall-check.sh` needs `ss` (iproute2) or `lsof` for the same reason, and will SKIP its port checks rather than guess if neither is present; worth installing one now if you expect to tear the lab down later.

`pip` is intentionally **not** a prereq: the install drives Python packaging through `uv`, which bundles its own resolver.

## Step 5 — Run the install

Before running any command in this step, announce the locked-in decisions in one line, e.g.:

> Installing MADSci via Docker, install dir *`$INSTALL_DIR`* (venv at `$INSTALL_DIR/.venv/`), starting state *fresh | data-only (`<path>`) | existing lab (`<path>`)*, profile *core stack only | full example lab*, UI *enabled via dashboard image*.

**`$INSTALL_DIR` is already locked in** from Step 1.2 (fresh / data-only — Options 1 and 2) or Step 2 (full prior lab — Option 3). Everything in Step 5 operates on that single directory. If `$INSTALL_DIR` isn't set at this point, stop and go back to Step 1.2 / Step 2 — do not guess a path.

### 5.A — Clone the MADSci repo into `$INSTALL_DIR` (Options 1 and 2 only)

If `$INSTALL_DIR` is **not** already a MADSci repo clone (Step 1.2 chose option 1 or 2 — fresh clone), do the clone now:

```bash
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone https://github.com/AD-SDL/MADSci "$INSTALL_DIR" \
    || { echo "git clone failed — check the URL / your network / write permission to $(dirname "$INSTALL_DIR")" >&2; exit 1; }
fi

# Re-run the Step 1.2 shape check — cheap, and catches a bad clone:
[[ -f "$INSTALL_DIR/compose.yaml" \
   && -f "$INSTALL_DIR/examples/example_lab/compose.yaml" \
   && -d "$INSTALL_DIR/src" ]] \
  || { echo "$INSTALL_DIR does not look like a MADSci repo (missing compose.yaml / examples/example_lab/compose.yaml / src/)" >&2; exit 1; }
```

**Do not run `madsci init`.** The example-lab compose configures each manager from baked-in defaults plus `$INSTALL_DIR/.env`; a scaffolded `settings.yaml` in a separate lab dir is never read, and running `madsci init` inside the clone would overwrite tracked files. For per-manager overrides, edit `$INSTALL_DIR/.env` directly.

**(Step 2 Option 3 skips this sub-step: `$INSTALL_DIR` is the user's own compose+config, nothing to clone.)**

### 5.B — Create a Python venv at `$INSTALL_DIR/.venv/` (always)

The host `madsci` CLI lives in a project-local venv at `$INSTALL_DIR/.venv/`, created and managed by `uv`:

```bash
cd "$INSTALL_DIR"

# Create a Python 3.10+ venv AT $INSTALL_DIR/.venv/. --python 3.10 picks the
# newest 3.10-or-later interpreter uv finds; pass --python 3.11/3.12 for a pin.
uv venv --python 3.10

# Install madsci-client into that venv (uv auto-detects .venv/ in CWD).
uv pip install madsci-client

# Smoke check — invoke the CLI via uv run (no manual activation needed).
uv run madsci --version
```

The venv holds only `madsci-client` and its deps — the CLI is a thin `docker compose` wrapper here, and all manager code runs inside the containers. Pinning it to `$INSTALL_DIR` means the CLI for this stack is unambiguously `$INSTALL_DIR/.venv/bin/madsci`, it can't clobber system Python or an unrelated venv, and `rm -rf "$INSTALL_DIR/.venv"` is a complete Python-side uninstall.

Invoke the CLI afterwards with `uv run madsci ...` from `$INSTALL_DIR` (the form used throughout this skill); see [troubleshooting.md](troubleshooting.md) §1 for the activation and direct-binary alternatives.

### 5.C — Option 3 fast-path: start and jump to verify

If Step 2 selected Option 3, the user has their own compose and config, so `$INSTALL_DIR` already has everything. **Skip 5.D** (no data to attach — the user's existing `.madsci/` is already where their compose expects it) and start:

```bash
cd "$INSTALL_DIR"
# Sanity-check (don't `madsci start` from the wrong dir):
[[ -f settings.yaml && -f compose.yaml ]] || { echo "Expected a MADSci lab here (settings.yaml + compose.yaml missing)" >&2; exit 1; }

uv run madsci start                              # foreground; add -d to detach
```

Jump straight to Step 7 (verify).

### 5.D — Attach existing `.madsci/` data (Option 2 only)

If Step 2 selected Option 2, attach the user's existing `.madsci/` at `$INSTALL_DIR/.madsci/` before `madsci start`.

> **Question:** "How do you want to attach the existing data at `<existing-path>` to `$INSTALL_DIR/.madsci/`?"
> **Header:** `Attach data`
> **Options:**
> 1. **Symlink** — reversible, no data copy. Reflects future changes back to the original path.
> 2. **Copy** — independent copy; safer if the original data source shouldn't be modified. Slower for large databases.

**Never delete `.madsci/` data to make room for the attach.** Both options need `$INSTALL_DIR/.madsci` to be free, but the way to free it is to *refuse and hand the decision back*, not to `rm -rf`. Run all three guards first:

```bash
# 1. Resolve both paths and refuse if they're the same (an attach onto itself).
TARGET_MADSCI="$(realpath -m "$INSTALL_DIR/.madsci")"
EXISTING="$(realpath -m "<existing-path>")"
if [[ "$TARGET_MADSCI" == "$EXISTING" ]]; then
  echo "Refusing: $INSTALL_DIR/.madsci/ and <existing-path> resolve to the same directory ($TARGET_MADSCI)." >&2
  exit 1
fi

# 2. Confirm $INSTALL_DIR is a MADSci repo (same shape check as 5.A — fast and cheap to re-check).
[[ -f "$INSTALL_DIR/compose.yaml" && -d "$INSTALL_DIR/src" ]] \
  || { echo "$INSTALL_DIR is not a MADSci repo — refusing to touch its .madsci/." >&2; exit 1; }

# 3. The target must be absent, or an empty directory. Anything else is somebody's data.
if [[ -e "$TARGET_MADSCI" ]]; then
  if [[ -d "$TARGET_MADSCI" && -z "$(ls -A "$TARGET_MADSCI" 2>/dev/null)" ]]; then
    rmdir "$TARGET_MADSCI"               # empty by definition — nothing to lose
  else
    echo "Refusing: $TARGET_MADSCI already exists and is not empty." >&2
    ls -la "$TARGET_MADSCI" >&2
    exit 1
  fi
fi
```

If guard 3 refuses, **stop and tell the user what's in the way** — print the listing above and ask them to move, rename, or delete `$TARGET_MADSCI` themselves, then re-run the attach. Do not offer to do it for them: a non-empty `.madsci/` holds databases, and the subdirectories are root-owned (created inside the containers), so removing it would need `sudo rm -rf` on a path that may not be the one they meant.

With the target free, confirm the attach with the user — print both paths back and get a final yes/no — then:

```bash
ln -s "$EXISTING" "$TARGET_MADSCI"       # option 1: symlink
# or
cp -a "$EXISTING" "$TARGET_MADSCI"       # option 2: copy
```

Neither command can clobber data: `ln -s` and `cp -a` both fail if the target already exists, so guard 3 is the only thing standing between them and a successful attach.

### 5.E — Start the stack from `$INSTALL_DIR` (Options 1 and 2)

`cd "$INSTALL_DIR"` first — the repo-root `compose.yaml` `include:`s `docker/compose.yaml` and `examples/example_lab/compose.yaml` (which pulls in `compose.infra.yaml` for the databases), and the relative bind-mounts only resolve from here.

**Branch on the Step 1.3 install profile:**

- **Core stack only** — start just the 7 managers; `depends_on` cascades pull in the databases automatically (including `madsci_seaweedfs`, which the Data Manager needs for object storage), and the example-node containers stay down. Use the CLI's repeatable `--services` flag rather than a bare `docker compose up -d`, so the service list is explicit:

  ```bash
  uv run madsci start \
    --services lab_manager --services event_manager --services experiment_manager \
    --services resource_manager --services data_manager --services location_manager \
    --services workcell_manager                      # foreground; add -d to detach
  ```

  **This choice does not persist on its own.** A bare `uv run madsci start` / `docker compose up -d` with no `--services` list always starts *every* service the compose files define (see the Full example lab bullet below) — including the demo nodes. To restart later without the demo nodes, repeat the same `--services` list.

- **Full example lab** — bring up everything the top-level compose defines (managers + databases + all demo nodes). Use the CLI from the project venv:

  ```bash
  uv run madsci start                           # foreground; add -d to detach
  # or equivalently, without the venv:
  # docker compose up -d
  ```

(Option 3 already started in 5.C — the user's own compose decides what runs.)

## Step 6 — Handle install-time errors

The most common failures and the questions they map to:

### 6.1 Port already in use

Manager ports are 8001–8006, dashboard 8000.

> **Question:** "Port <N> is already in use. How do you want to resolve it?"
> **Header:** `Port conflict`
> **Options:**
> 1. **Show me what's on that port** — I'll run `lsof -i :<N>` and report; you decide.
> 2. **Stop the conflicting process** — only if you tell me exactly which one.
> 3. **Remap the port** — edit the lab's `settings.yaml` (I'll show the diff first) and retry.
> 4. **Abort**.

### 6.2 `.madsci/` sentinel not found where expected

PIDs, logs, and backups are resolved by walking up for a `.madsci/` directory, then `.git/`, then falling back to `~/.madsci/` ([sentry.py](../../../src/madsci_common/madsci/common/sentry.py)). If `madsci status` or `madsci start` behaves like it can't find state, the CWD is probably wrong.

> **Question:** "MADSci is resolving `.madsci/` in an unexpected location (`<path>`). What do you want?"
> **Header:** `Settings dir`
> **Options:**
> 1. **Scaffold `.madsci/` in this directory** — I'll create it with the standard subdirs via `ensure_madsci_dir()` (pass the PARENT dir; the helper appends `.madsci` itself).
> 2. **Point MADSci at a different directory** — set `MADSCI_SETTINGS_DIR` or pass `--settings-dir`; you tell me the path.
> 3. **`cd` into the intended lab directory and retry** — you tell me which one.

### 6.3 Docker daemon reachable but `docker compose up` hangs on healthchecks

A manager container can reach its port but the database (FerretDB/Postgres) inside the compose network isn't up yet, or a volume from a previous run has incompatible data.

> **Question:** "Compose is stuck on healthchecks. What's the history of this stack?"
> **Header:** `Compose stuck`
> **Options:**
> 1. **Fresh start — recreate containers** — `docker compose down -v` then `docker compose up`. *(Removes named volumes. The example lab bind-mounts `.madsci/` instead of using named volumes, so DB data normally survives this — do not present it as a data reset. Confirm before running.)*
> 2. **Tail logs first** — I'll run `docker compose logs --tail=100 <service>`; you decide.
> 3. **Give it more time** — some images pull large layers on first run; wait 60s and re-check.
> 4. **Abort**.

### 6.4 Schema version mismatch on Resource Manager startup

`ResourceManager` runs a `DatabaseVersionChecker` on init that compares the installed MADSci version against `madsci_schema_version` in the mounted database. Mismatch → the manager refuses to start and the whole stack aborts.

This is the same failure the Step 2 schema-version check anticipates — **ask the Step 2 "Version mismatch" question** (migrate / load anyway / discard and start fresh) and apply the chosen branch here.

For anything else, read [troubleshooting.md](troubleshooting.md) before improvising.

## Step 7 — Verify the install succeeded

Always run at the end — "command exited 0" ≠ "stack answers correctly."

Invoke the verification script by **absolute path** (your skill root is wherever your agent runtime resolved this skill from, e.g. `.agents/skills/madsci-install/` in the current repo, or wherever the skill is installed on the user's machine):

```bash
bash <SKILL_DIR>/install-check.sh --install-dir "$INSTALL_DIR" [--with-ui | --no-ui]
```

If `--with-ui`/`--no-ui` is omitted, the script defaults to `--with-ui` (Docker compose typically mounts the dashboard image). Pass `--no-ui` if Step 3 said "slim API-only compose."

The script checks Python 3.10+, MADSci imports (host venv informationally, a manager container authoritatively), `docker info`, every manager's `/health` on 8001–8006 and the dashboard's on 8000 — asserting the body reports `{"healthy": true}`, since HTTP 200 alone isn't enough — and the content-type at `/` (HTML for `--with-ui`, JSON 404 for `--no-ui`). `madsci status` / `madsci doctor` are dumped informationally only and never gate pass/fail here — `madsci status` always exits 0, and while `madsci doctor` exits 1 on its own failed checks, this script deliberately ignores that exit code since the `/health` curls above are the authoritative signal.

**Report the pass/fail matrix verbatim, one line per check.** Do not summarize. If any check fails, drop back to Step 6 with the failure signature; do not announce completion.

Announce completion only when every check passes:

> ✅ MADSci install verified via Docker, dashboard UI *<enabled | API-only>*. Managers up on 8001–8006, dashboard on 8000 (HTML at `/` | JSON API only), all `/health` endpoints report `healthy=true`.

## Step 8 — Uninstall / tear down

If the user wants to **remove** MADSci, load [uninstall.md](uninstall.md) and follow it — scope selection (`stop` / `remove`), image removal, and verification via `uninstall-check.sh`.

**Deleting `.madsci/` is not something this skill does.** Stopping the stack and removing images is reversible; dropping the databases under `.madsci/` is not, and the command is a root-owned `sudo rm -rf` against a path whose resolution depends on how the install was done. uninstall.md §U3 resolves and prints that path, offers a backup, and hands the command to the operator to run. Follow that hand-off even if the user asks you to run it directly.

## What this skill does NOT do

**It never deletes `.madsci/` data.** Not on install (Step 5.D refuses a non-empty target instead of clearing it), not on uninstall (§U3 hands the `sudo rm -rf` to the operator), and not on request. Every other action this skill takes is reversible by re-running something; this one isn't.

Beyond that and the Rules of engagement above: it never installs Docker without the Step 1.1 consent, never modifies version-controlled files without showing a diff first, never removes Python packages from an unconfirmed environment (the venv at `$INSTALL_DIR/.venv/` is the only one it touches), and never silences errors with `|| true`, `2>/dev/null`, retry loops, or linter/CI config edits.

It also does not extend into implementation — hand off to [madsci-nodes](../madsci-nodes/SKILL.md), [madsci-managers](../madsci-managers/SKILL.md), or [madsci-experiments](../madsci-experiments/SKILL.md) once the stack is up.

## Cross-references (not linked inline above)

- Backup & recovery (offer this before the user deletes `.madsci/`): [docs/guides/operator/03-backup-recovery.md](../../../docs/guides/operator/03-backup-recovery.md)
- Updates & maintenance (stop services, upgrade/downgrade): [docs/guides/operator/05-updates-maintenance.md](../../../docs/guides/operator/05-updates-maintenance.md)
- CLI details for `init` / `start` / `stop` / `status` / `doctor`: [madsci-cli](../madsci-cli/SKILL.md)
