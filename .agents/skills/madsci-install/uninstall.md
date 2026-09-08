# MADSci Uninstall / Tear Down

Companion to [SKILL.md](SKILL.md). Load this when the user's intent is to **remove** a MADSci lab (stop the stack, `docker compose down`, `pip uninstall`, wipe `.madsci/` data, remove pulled images).

Uninstalling has **irreversible, data-destroying** steps that installing never does. Treat with more caution, not less: **every destructive action is a separate AskUserQuestion with an explicit DATA LOSS warning, and never delete data the user didn't name.**

**Scope, mirroring the install skill:**
- **In scope:** teardown of a MADSci lab installed by this skill (`--method docker` or `--method local`). Uninstall the pip packages, stop the running stack, remove containers/images, wipe `.madsci/` data.
- **Out of scope:** the shipped example lab at the repo root (a user tears that down with `docker compose down` from the repo). Contributor dev environment cleanup (`.venv/`, pre-commit hook, PDM/uv/devbox state) — handled by a contributor skill.

## Step U0 — Determine uninstall scope

Uninstall is layered — each layer is additive:

> **Question:** "How much of MADSci do you want to remove?"
> **Header:** `Uninstall scope`
> **Options:**
> 1. **Stop only** — halt the running stack/processes but keep containers, packages, and all data. Reversible; the fastest way back to running. *(Recommended default.)*
> 2. **Stop + remove** — also remove Docker containers/network/images (`--method docker`) or `pip uninstall` the packages (`--method local`), but **keep data** in `.madsci/`.
> 3. **Full wipe** — everything above **plus delete `.madsci/` data** (databases, logs, registry). *(DATA LOSS — irreversible. Confirm explicitly.)*

If you don't know which method was used, infer:
- `docker compose ps` shows MADSci containers → `--method docker`.
- `pgrep -f 'madsci start --mode local'` shows a running process → `--method local`.
- Neither → ask the user directly.

**Always recommend a backup before any Full wipe** — see [docs/guides/operator/03-backup-recovery.md](../../docs/guides/operator/03-backup-recovery.md) and the `madsci-backup` CLI. Offer it; don't force it.

## Step U1 — Stop the stack

### Method = docker

Run from the lab directory (the one containing `settings.yaml` and `.env`):

```bash
madsci stop                  # wraps `docker compose down` (finds compose.yaml via CWD/parent)
```

Alternatively, from a repo checkout:

```bash
just down                    # == docker compose down
```

For **detached** managers/nodes started with `-d`: `madsci stop manager <name>` / `madsci stop node <name>` reads the PID file under `.madsci/pids/`, SIGTERMs, then SIGKILLs, and removes the PID file. Manager names: `lab, event, experiment, resource, data, workcell, location`.

**Trap:** `madsci stop --volumes` (or `docker compose down -v`) removes *named* volumes only. MADSci compose configurations typically use **bind mounts to `./.madsci/`**, so `-v` deletes *nothing* of the DB data. See U4 for the real data wipe.

### Method = local

Native mode is a single foreground, in-memory process. There is nothing to `docker compose down`.

```bash
# If running in the foreground: Ctrl+C in the terminal running it.
# If backgrounded:
pkill -f 'madsci start --mode local'
# Or, if you know the PID:
kill <PID>
```

Data is in-memory — it evaporates the moment the process exits. Nothing to wipe from `.madsci/` for `--method local` beyond logs/PIDs.

For scope `stop`, U1 is enough. Continue to U2 only for scope `remove` or `wipe`.

## Step U2 — Uninstall the pip packages (scope: remove | wipe)

Only relevant for `--method local` (or `--method docker` if the user wants to remove the host CLI too — `docker` method installs the CLI on the host for `madsci start`, and it may be worth keeping if the user manages multiple labs).

**Always confirm the target environment first** (`which python`, `pip show madsci.client`) so you don't uninstall from the wrong venv:

```bash
# All MADSci distributions (11 packages):
pip uninstall -y \
  madsci.client madsci.common madsci.node_module madsci.squid \
  madsci.event_manager madsci.experiment_manager madsci.resource_manager \
  madsci.data_manager madsci.workcell_manager madsci.location_manager \
  madsci.experiment_application
```

Distribution names use dots by convention, but **pip normalizes `.`/`-`/`_`** — `madsci.client` == `madsci-client` == `madsci_client`. Uninstalling `madsci.client` removes the `madsci` CLI entry point.

If MADSci lives in a throwaway venv, deleting the venv directory is cleaner than `pip uninstall`:

```bash
deactivate 2>/dev/null; rm -rf <path-to-venv>
```

## Step U3 — Remove Docker images (scope: remove | wipe, method: docker)

Only after the containers are gone (U1). This frees several GB. Confirm with the user — a re-install re-pulls them.

```bash
docker rmi ghcr.io/ad-sdl/madsci:latest ghcr.io/ad-sdl/madsci_dashboard:latest
# Infra images (only if nothing else on the host uses them):
docker rmi ghcr.io/ferretdb/ferretdb:2 valkey/valkey:8 \
  ghcr.io/ferretdb/postgres-documentdb-dev:17-ferretdb postgres:17 chrislusf/seaweedfs:4.17
```

Do **not** run `docker system prune` / `docker volume prune` on the user's behalf — it can delete unrelated resources. Offer it as an option they run themselves.

## Step U4 — Delete `.madsci/` data (scope: wipe only — IRREVERSIBLE)

This is where the real data lives (bind-mounted DB dirs for `--method docker`). Compose containers created much of it **as root**, so deletion needs `sudo`.

> **Question:** "Full wipe deletes all local MADSci data in `.madsci/` (databases, logs, registry). This cannot be undone. Proceed?"
> **Header:** `Wipe .madsci`
> **Options:**
> 1. **Back up first, then wipe** — I'll run `madsci-backup` / DB dumps, then delete. *(Recommended.)*
> 2. **Wipe now, no backup** — you confirm you don't need the data.
> 3. **Keep data, stop here** — leave `.madsci/` intact.

```bash
# Containers MUST be down first (U1), or Postgres/FerretDB may hold the dirs open.
# DB data dirs are root-owned (created by containers) → sudo required:
sudo rm -rf ./.madsci/postgresql ./.madsci/postgresql_resources \
            ./.madsci/mongodb ./.madsci/valkey ./.madsci/seaweedfs
# User-owned runtime state:
rm -rf ./.madsci/logs ./.madsci/pids ./.madsci/backups ./.madsci/registry.json
# Or remove the whole directory:
sudo rm -rf ./.madsci
```

Show the user `ls -la ./.madsci` and confirm which entries are root-owned **before** invoking `sudo rm`. Never `sudo rm -rf` a path you haven't printed back to them.

For `--method local`, the `.madsci/` directory contains only user-owned logs/PIDs/registry (no DB bind mounts) — no `sudo` needed:

```bash
rm -rf ~/<lab-name>/.madsci
```

## Step U5 — Verify the teardown

Confirm the removal actually happened. A clean uninstall is "nothing answers and nothing is left," not "the command exited 0."

```bash
bash .agents/skills/madsci-install/uninstall-check.sh --method <docker|local> --scope <stop|remove|wipe>
```

The script verifies (as appropriate for the method/scope):

- **No MADSci containers running / existing** (`--method docker`).
- **Native (`--mode local`) process stopped** (`--method local`).
- **Manager & dashboard ports free** (8000–8006).
- **MADSci Docker images removed** (`--method docker` + scope `remove`/`wipe`).
- **`.madsci/` data directory removed** (scope `wipe`).
- **No stale PID files** in `.madsci/pids/`.
- **MADSci Python packages uninstalled** (`--method local` + scope `remove`/`wipe`).

**Report its pass/fail matrix verbatim**, same as install. If a check unexpectedly fails, consult [troubleshooting.md](troubleshooting.md) §Uninstall before improvising.

Announce completion only when the requested scope is fully torn down:

> ✅ MADSci uninstall verified for method *<docker|local>* / scope *<scope>*. No containers/processes running, ports 8000–8006 free, `.madsci/` removed, MADSci CLI/packages gone.
