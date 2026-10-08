# MADSci Uninstall / Tear Down

Companion to [SKILL.md](SKILL.md). Load this when the user's intent is to **remove** a MADSci lab (stop the stack, `docker compose down`, wipe `.madsci/` data, remove pulled images).

Uninstalling has **irreversible, data-destroying** steps that installing never does. Treat with more caution, not less: **every destructive action is a separate AskUserQuestion with an explicit DATA LOSS warning, and never delete data the user didn't name.**

Contributor dev environment cleanup (`.venv/`, pre-commit hooks, PDM/uv state) is not covered here.

## Step U0 — Determine uninstall scope

Uninstall is layered — each layer is additive:

> **Question:** "How much of MADSci do you want to remove?"
> **Header:** `Uninstall scope`
> **Options:**
> 1. **Stop only** — halt the running stack but keep containers, images, and all data. Reversible; the fastest way back to running. *(Recommended default.)*
> 2. **Stop + remove** — also remove MADSci Docker images, but **keep data** in `.madsci/`.
> 3. **Full wipe** — everything above **plus delete `.madsci/` data** (databases, logs, registry). *(DATA LOSS — irreversible. Confirm explicitly.)*

**Always recommend a backup before any Full wipe** — see [docs/guides/operator/03-backup-recovery.md](../../../docs/guides/operator/03-backup-recovery.md) and the `madsci-backup` CLI. Offer it; don't force it.

## Step U1 — Stop the stack

Run from the directory the stack was started from — the MADSci repo clone (Install Options 1 / 2) or the user's own full lab directory (Install Option 3). This is the directory containing `compose.yaml` and `.madsci/`:

```bash
cd "$INSTALL_DIR"
uv run madsci stop           # wraps `docker compose down` (finds compose.yaml via CWD/parent)
# or, without the venv:  docker compose down   (from a repo checkout: just down)
```

For **detached** managers/nodes started with `-d`: `uv run madsci stop manager <name>` / `... node <name>` reads the PID file under `.madsci/pids/`, SIGTERMs, then SIGKILLs, and removes the PID file. Manager names: `lab, event, experiment, resource, data, workcell, location`.

**Trap:** `madsci stop --volumes` (or `docker compose down -v`) removes *named* volumes only. MADSci compose configurations typically use **bind mounts to `./.madsci/`**, so `-v` deletes *nothing* of the DB data. See U3 for the real data wipe.

For scope `stop`, U1 is enough. Continue to U2 only for scope `remove` or `wipe`.

## Step U2 — Remove Docker images (scope: remove | wipe)

Only after the containers are gone (U1). This frees several GB. Confirm with the user — a re-install re-pulls them.

```bash
docker rmi ghcr.io/ad-sdl/madsci:latest ghcr.io/ad-sdl/madsci_dashboard:latest
# Infra images (only if nothing else on the host uses them):
docker rmi ghcr.io/ferretdb/ferretdb:2 valkey/valkey:8 \
  ghcr.io/ferretdb/postgres-documentdb-dev:17-ferretdb postgres:17 chrislusf/seaweedfs:4.17
```

Do **not** run `docker system prune` / `docker volume prune` on the user's behalf — it can delete unrelated resources. Offer it as an option they run themselves.

**Removing the host `madsci` CLI venv (optional):** the install creates a project-local venv at `$INSTALL_DIR/.venv/` (`$INSTALL_DIR` is the directory chosen at the install skill's Step 1.2 — the MADSci repo clone for Options 1/2, or the user's own lab directory for Option 3). Because it's strictly local to `$INSTALL_DIR`, removal is a safe one-shot `rm -rf` — no `pip uninstall` reasoning about system Python, no risk of hitting an unrelated environment. Keep it if the user plans to re-use the stack; delete it for a full teardown:

```bash
# Confirm the target first:
"$INSTALL_DIR/.venv/bin/python" -c "import sys; print(sys.prefix)"
ls -la "$INSTALL_DIR/.venv/bin/madsci"

rm -rf "$INSTALL_DIR/.venv"
```

## Step U3 — Delete `.madsci/` data (scope: wipe only — IRREVERSIBLE)

This is where the real data lives (bind-mounted DB dirs). The install never explicitly scaffolds `.madsci/` — Docker auto-creates it on first `compose up` because the compose file bind-mounts `../../.madsci:/home/madsci/.madsci`. The DB subdirs are created inside the containers **as root**, so deletion needs `sudo`.

**First: find the right directory.** Where `.madsci/` lives depends on how the install was done:

- **Install Options 1 / 2 (repo-in-place):** `$INSTALL_DIR/.madsci/` — the parent of the compose file's `../../` resolves to the repo root (where `$INSTALL_DIR` is the directory from install skill Step 1.2).
- **Install Option 3 (user's own full lab dir):** `<lab-dir>/.madsci/`.

Resolve the path explicitly before anything else — do **not** assume `./.madsci`:

```bash
# Pick ONE based on how the install was done:
MADSCI_DIR="$INSTALL_DIR/.madsci"    # Options 1 / 2
# or
MADSCI_DIR="<lab-dir>/.madsci"       # Option 3

# Verify the path and its ownership before any destructive command:
[[ -d "$MADSCI_DIR" ]] || { echo "No .madsci/ at $MADSCI_DIR — nothing to wipe here. Did you mean another path?" >&2; exit 1; }
ls -la "$MADSCI_DIR"                 # show what's actually there and who owns it
```

If `MADSCI_DIR` doesn't exist, there's nothing to delete at that location — stop and re-check with the user before guessing another path. (The symptom "`./.madsci` is empty / has nothing" almost always means the CWD isn't the right directory.)

> **Question:** "Full wipe deletes all local MADSci data in `$MADSCI_DIR` (databases, logs, registry). This cannot be undone. Proceed?"
> **Header:** `Wipe .madsci`
> **Options:**
> 1. **Back up first, then wipe** — I'll run `madsci-backup` / DB dumps, then delete. *(Recommended.)*
> 2. **Wipe now, no backup** — you confirm you don't need the data.
> 3. **Keep data, stop here** — leave `.madsci/` intact.

```bash
# Containers MUST be down first (U1), or Postgres/FerretDB may hold the dirs open.
# DB data dirs are root-owned (created by containers) → sudo required:
sudo rm -rf "$MADSCI_DIR/postgresql" "$MADSCI_DIR/postgresql_resources" \
            "$MADSCI_DIR/mongodb" "$MADSCI_DIR/valkey" "$MADSCI_DIR/seaweedfs"
# User-owned runtime state:
rm -rf "$MADSCI_DIR/logs" "$MADSCI_DIR/pids" "$MADSCI_DIR/backups" "$MADSCI_DIR/registry.json"
# Or remove the whole directory:
sudo rm -rf "$MADSCI_DIR"
```

Print `$MADSCI_DIR` back to the user and confirm the destructive command **before** invoking `sudo rm`. Never `sudo rm -rf` a path you haven't printed back to them.

## Step U4 — Verify the teardown

Confirm the removal actually happened. A clean uninstall is "nothing answers and nothing is left," not "the command exited 0."

Invoke the verification script by **absolute path** (`<SKILL_DIR>` is wherever your agent runtime resolved this skill from — e.g. `.agents/skills/madsci-install/` in the current repo):

```bash
bash <SKILL_DIR>/uninstall-check.sh --scope <stop|remove|wipe> \
    [--compose-project <name>] --madsci-dir "$MADSCI_DIR"
```

**Always pass `--madsci-dir`** with the same `$MADSCI_DIR` resolved in U3 — the script's default (`./.madsci`) assumes CWD is the install directory and will give you a vacuous PASS from the wrong location.

Scoped to what was asked, the script verifies that no containers run or remain under the compose project (default `madsci_example_lab`; pass `--compose-project` for any other name), that ports 8000–8006 are free, that the MADSci images are gone (scope `remove`/`wipe` — reported as SKIP, not a vacuous PASS, when none were ever present), that `.madsci/` is deleted at `--madsci-dir` (scope `wipe`), and that no stale `*.pid` files remain under `<madsci-dir>/pids/`.

**Report its pass/fail matrix verbatim**, same as install. If a check unexpectedly fails, consult [troubleshooting.md](troubleshooting.md) §Uninstall before improvising.

Announce completion only when the requested scope is fully torn down:

> ✅ MADSci uninstall verified for scope *<scope>*. No containers running under project *<name>*, ports 8000–8006 free, images removed, `.madsci/` deleted.
