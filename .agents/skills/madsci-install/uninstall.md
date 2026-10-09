# MADSci Uninstall / Tear Down

Companion to [SKILL.md](SKILL.md). Load this when the user's intent is to **remove** a MADSci lab — stop the stack, `docker compose down`, remove pulled images, and hand off the `.madsci/` data deletion.

Uninstalling touches **irreversible, data-destroying** territory that installing never does. Treat it with more caution, not less:

- **Never delete `.madsci/` yourself.** Stopping containers and removing images is reversible — a re-install re-pulls and re-starts. Deleting the databases under `.madsci/` is not. You resolve the path, print the exact command, and hand it to the operator to run (§U3). This is a hard rule, not a default you can talk yourself out of, and it holds no matter how explicitly the user asks.
- Every other destructive action is a separate AskUserQuestion with an explicit warning, and you never remove anything the user didn't name.

Contributor dev environment cleanup (`.venv/`, pre-commit hooks, PDM/uv state) is not covered here.

## Step U0 — Determine uninstall scope

Uninstall is layered — each layer is additive. Both scopes you can carry out are **reversible**:

> **Question:** "How much of MADSci do you want to remove?"
> **Header:** `Uninstall scope`
> **Options:**
> 1. **Stop only** — halt the running stack but keep containers, images, and all data. The fastest way back to running. *(Recommended default.)*
> 2. **Stop + remove** — also remove MADSci Docker images, but **keep data** in `.madsci/`. A re-install re-pulls them.

**Deleting `.madsci/` data is deliberately not a scope here.** If the user wants a full wipe, run scope 2 first, then go to §U3 — you resolve and print the path and the exact `rm` command, and *they* run it. Say so up front when the user asks for a full teardown, so the hand-off isn't a surprise at the end.

**Always recommend a backup before they delete anything** — see [docs/guides/operator/03-backup-recovery.md](../../../docs/guides/operator/03-backup-recovery.md) and the `madsci-backup` CLI. Offer it; don't force it.

## Step U1 — Stop the stack

Run from the directory the stack was started from — the MADSci repo clone (Install Options 1 / 2) or the user's own full lab directory (Install Option 3). This is the directory containing `compose.yaml` and `.madsci/`:

```bash
cd "$INSTALL_DIR"
uv run madsci stop           # wraps `docker compose down` (finds compose.yaml via CWD/parent)
# or, without the venv:  docker compose down   (from a repo checkout: just down)
```

For **detached** managers/nodes started with `-d`: `uv run madsci stop manager <name>` / `... node <name>` reads the PID file under `.madsci/pids/`, SIGTERMs, then SIGKILLs, and removes the PID file. Manager names: `lab, event, experiment, resource, data, workcell, location`.

**Trap:** `madsci stop --volumes` (or `docker compose down -v`) removes *named* volumes only. MADSci compose configurations typically use **bind mounts to `./.madsci/`**, so `-v` deletes *nothing* of the DB data. §U3 covers the real data deletion — which the operator runs, not you.

For scope `stop`, U1 is enough. Continue to U2 only for scope `remove`.

## Step U2 — Remove the reproducible artifacts (scope: remove)

Two things get removed here, both rebuildable from scratch by re-running the install: the Docker images and the host CLI venv. Do **both** for scope `remove` — the venv is not an optional extra.

Only start after the containers are gone (U1).

### U2.a — Docker images

Frees several GB. Confirm with the user — a re-install re-pulls them.

```bash
docker rmi ghcr.io/ad-sdl/madsci:latest ghcr.io/ad-sdl/madsci_dashboard:latest
# Infra images (only if nothing else on the host uses them):
docker rmi ghcr.io/ferretdb/ferretdb:2 valkey/valkey:8 \
  ghcr.io/ferretdb/postgres-documentdb-dev:17-ferretdb postgres:17 chrislusf/seaweedfs:4.17
```

Do **not** run `docker system prune` / `docker volume prune` on the user's behalf — it can delete unrelated resources. Offer it as an option they run themselves.

### U2.b — The host `madsci` CLI venv

**This is the entire Python uninstall.** There is no `pip uninstall` step anywhere in this skill, because the install never installs into a shared environment: Step 5.B creates a project-local venv at `$INSTALL_DIR/.venv/` and puts `madsci-client` and its dependencies there and nowhere else. (`$INSTALL_DIR` is the directory chosen at install Step 1.2 — the MADSci repo clone for Options 1/2, the user's own lab directory for Option 3.) All manager code runs inside the containers; the host CLI is a thin `docker compose` wrapper.

Because the venv is strictly local to `$INSTALL_DIR`, deleting the directory *is* the uninstall — no reasoning about system Python, no risk of hitting an unrelated environment, nothing left behind to check for:

```bash
# Confirm the target first:
"$INSTALL_DIR/.venv/bin/python" -c "import sys; print(sys.prefix)"
ls -la "$INSTALL_DIR/.venv/bin/madsci"

rm -rf "$INSTALL_DIR/.venv"
```

Skip this only if the user says they want to keep the CLI — e.g. they're removing the containers but plan to re-start the stack later. Rebuilding it is `uv venv --python 3.10 && uv pip install madsci-client`.

### What U2 deliberately leaves alone

**The repo clone at `$INSTALL_DIR`.** It's a git checkout the user may have edited, and `$INSTALL_DIR/.env` is where per-manager overrides and secrets live — the install told them to edit it directly. More importantly, `$INSTALL_DIR` *contains* `.madsci/`, so removing the directory wholesale would delete the databases through the back door, which §U3 exists to prevent.

If the user wants the clone gone too, that's the same hand-off as §U3: tell them the path, note that `.madsci/` and `.env` are inside it, and let them run the removal.

## Step U3 — Hand off the `.madsci/` data deletion (operator-run — IRREVERSIBLE)

**You do not run the deletion in this step.** You resolve the path, show the operator what's in it, offer a backup, and print the exact command for them to run. Three reasons this is a hard rule rather than a cautious default:

- The data is irreplaceable in a way nothing else in the teardown is. Containers and images come back from a re-install; a dropped Postgres volume doesn't.
- The DB subdirectories are root-owned (created inside the containers), so the command is `sudo rm -rf` — the one shape of command where a wrong path resolution is unrecoverable.
- Resolving `.madsci/` depends on how the install was done, and the agent's CWD is the single most common thing to be wrong about. A human looking at the printed path catches a mistake that an agent confident in its own resolution will not.

This is where the real data lives (bind-mounted DB dirs). The install never explicitly scaffolds `.madsci/` — Docker auto-creates it on first `compose up` because the compose file bind-mounts `../../.madsci:/home/madsci/.madsci`.

**First: find the right directory.** Where `.madsci/` lives depends on how the install was done:

- **Install Options 1 / 2 (repo-in-place):** `$INSTALL_DIR/.madsci/` — the parent of the compose file's `../../` resolves to the repo root (where `$INSTALL_DIR` is the directory from install skill Step 1.2).
- **Install Option 3 (user's own full lab dir):** `<lab-dir>/.madsci/`.

Resolve the path explicitly before anything else — do **not** assume `./.madsci`:

```bash
# Pick ONE based on how the install was done:
MADSCI_DIR="$INSTALL_DIR/.madsci"    # Options 1 / 2
# or
MADSCI_DIR="<lab-dir>/.madsci"       # Option 3

# Both commands are read-only — run these yourself to resolve and show the target:
[[ -d "$MADSCI_DIR" ]] || { echo "No .madsci/ at $MADSCI_DIR — nothing there. Did you mean another path?" >&2; exit 1; }
ls -la "$MADSCI_DIR"                 # show what's actually there and who owns it
du -sh "$MADSCI_DIR" 2>/dev/null     # how much data is at stake
```

If `MADSCI_DIR` doesn't exist, there's nothing to delete at that location — stop and re-check with the user before guessing another path. (The symptom "`./.madsci` is empty / has nothing" almost always means the CWD isn't the right directory.)

**Offer a backup first** — this one you *can* run, because it only reads:

> **Question:** "Before you delete `$MADSCI_DIR`, do you want a backup of the databases?"
> **Header:** `Back up first`
> **Options:**
> 1. **Yes, back up now** — I'll run `madsci-backup` / DB dumps to a path outside `$MADSCI_DIR`. *(Recommended.)*
> 2. **No backup** — you've confirmed you don't need this data.

**Then hand over the commands.** Print `$MADSCI_DIR` back to the user with the listing above, state plainly that this is irreversible, and give them this block to run themselves:

```bash
# Containers MUST be down first (U1), or Postgres/FerretDB may hold the dirs open.
# DB data dirs are root-owned (created by the containers) → sudo required.

# Either remove the data directories individually:
sudo rm -rf "$MADSCI_DIR/postgresql" "$MADSCI_DIR/postgresql_resources" \
            "$MADSCI_DIR/mongodb" "$MADSCI_DIR/valkey" "$MADSCI_DIR/seaweedfs"
rm -rf "$MADSCI_DIR/logs" "$MADSCI_DIR/pids" "$MADSCI_DIR/backups" "$MADSCI_DIR/registry.json"

# ...or remove the whole directory in one shot:
sudo rm -rf "$MADSCI_DIR"
```

Expand `$MADSCI_DIR` to the literal resolved path when you print it — the operator should be reading the actual directory they're about to delete, not a variable they have to trust you set correctly.

**Do not run these, and do not offer to.** If the user asks you to run it anyway, decline and re-print the command: the point of the hand-off is that a second pair of eyes sees the resolved path, and running it for them removes exactly the check that makes this safe. Once they confirm they've run it, continue to U4 to verify.

## Step U4 — Verify the teardown

Confirm the removal actually happened. A clean uninstall is "nothing answers and nothing is left," not "the command exited 0."

Invoke the verification script by **absolute path** (`<SKILL_DIR>` is wherever your agent runtime resolved this skill from — e.g. `.agents/skills/madsci-install/` in the current repo):

```bash
bash <SKILL_DIR>/uninstall-check.sh --scope <stop|remove> \
    [--compose-project <name>] --madsci-dir "$MADSCI_DIR"
```

**Always pass `--madsci-dir`** with the same `$MADSCI_DIR` resolved in U3 — the script's default (`./.madsci`) assumes CWD is the install directory and will give you a vacuous PASS from the wrong location.

Scoped to what was asked, the script verifies that no containers run or remain under the compose project (default `madsci_example_lab`; pass `--compose-project` for any other name), that ports 8000–8006 are free, that the MADSci images are gone (scope `remove` — reported as SKIP, not a vacuous PASS, when none were ever present), and that no stale `*.pid` files remain under `<madsci-dir>/pids/`.

**`--scope wipe` is verification-only.** It additionally asserts that `.madsci/` is gone at `--madsci-dir`. Use it *after* the operator tells you they ran the §U3 deletion themselves — it confirms their `rm` landed on the directory you resolved. It is not a scope you tear down to; nothing in this document deletes `.madsci/` on the user's behalf.

**Report its pass/fail matrix verbatim**, same as install. If a check unexpectedly fails, consult [troubleshooting.md](troubleshooting.md) §Uninstall before improvising.

Announce completion only when the requested scope is fully torn down:

> ✅ MADSci uninstall verified for scope *<scope>*. No containers running under project *<name>*, ports 8000–8006 free, images removed.

If the user also deleted `.madsci/` and you verified it with `--scope wipe`, say so as a separate line — it was their action, not yours.
