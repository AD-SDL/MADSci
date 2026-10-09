# MADSci Install-Time Troubleshooting

Failure modes seen during install / first-startup, keyed by the message the user is likely to paste at you. **Match on the signature, run the AskUserQuestion prompt from the parent SKILL.md, then apply the fix.** Do not silently retry.

For runtime troubleshooting (workflows failing mid-run, node action errors, resource lock issues, etc.) see [../../../docs/guides/troubleshooting.md](../../../docs/guides/troubleshooting.md) instead.

Scope, mirroring the install skill: this covers install/uninstall of user labs via Docker Compose. Contributor-dev issues (`pdm install`, `just init`, pre-commit hooks, `.venv/` in the repo) are not covered here.

---

## 1. CLI not on PATH

### `madsci: command not found` after `uv pip install madsci-client`

The install creates a project-local venv at `$INSTALL_DIR/.venv/` and the CLI lives at `$INSTALL_DIR/.venv/bin/madsci`. `uv pip install` into that venv **does not** put it on your shell's PATH; you reach it in one of three ways:

```bash
# Preferred — `uv run` finds the project venv automatically:
cd "$INSTALL_DIR" && uv run madsci --version

# OR activate the venv explicitly (one shell only):
source "$INSTALL_DIR/.venv/bin/activate" && madsci --version

# OR invoke the binary directly:
"$INSTALL_DIR/.venv/bin/madsci" --version
```

If none work, diagnose which venv `uv` is actually touching:
```bash
cd "$INSTALL_DIR"
uv run python -c "import sys; print(sys.executable, sys.prefix)"
ls -la .venv/bin/madsci   # must exist and be executable
uv pip list | grep -i madsci
```

Options:
1. The venv is in a different directory than you think — `cd` to the actual `$INSTALL_DIR` from Step 5 and retry.
2. The venv exists but doesn't contain `madsci.client` — re-run `uv pip install madsci-client` from inside `$INSTALL_DIR`.
3. The venv was never created — re-run Step 5's `uv venv --python 3.10` + `uv pip install madsci-client`.

---

## 2. Docker

### `docker: command not found` or `Cannot connect to the Docker daemon`

Offer the up-front SKILL.md §Step 1 options: install Docker (via the official convenience script under sudo) or abort.

### `lab_manager` container shows `(unhealthy)` but `curl http://localhost:8000/health` returns 200

**False alarm caused by a malformed healthcheck.** Fixed in the example lab, but still possible in any compose file that uses exec-form `CMD` with shell operators:
```yaml
test: ["CMD", "curl", "-f", "${LAB_SERVER_URL:-http://localhost:8000}/health", "||", "exit", "1"]
```
Exec form has no shell, so `||`, `exit` and `1` become **three extra URLs** for curl. Curl parses the bare `1` as a packed IP and hangs on `http://0.0.0.1/` until Docker kills the probe, and it returns the *last* error either way — so raising `timeout:` never helps.

**The manager itself is the source of truth, not Docker's health flag:**
```bash
curl -fsS http://localhost:8000/health    # → {"healthy":true,...}
```
`install-check.sh` curls `/health` directly, so it reports PASS regardless of the Docker label — treat `(unhealthy)` as cosmetic until the compose file is fixed.

**Fix** — drop the redundant `|| exit 1` (`curl -f` already exits non-zero on HTTP failure) and strip the trailing slash, since `LAB_SERVER_URL` conventionally ends in `/` and `//health` returns 404:
```yaml
test: ["CMD-SHELL", 'URL="${LAB_SERVER_URL:-http://localhost:8000}"; curl -f "$${URL%/}/health"']
```
Healthchecks are baked in at container creation — recreate with `docker compose up -d lab_manager` for the change to take effect.

### `docker compose up` starts but a service stays `unhealthy`

**Diagnose:**
```bash
docker compose logs --tail=200 <service-name>
docker compose ps
```

**Common causes:**
- A previous run left an incompatible volume (schema mismatch after a migration). Fix: `docker compose down -v` — DATA LOSS, confirm first (SKILL.md §6.3).
- First-time image pull still in progress. Fix: wait 60s, re-check.
- Host port already bound (see §3).

### `docker compose up` fails immediately with "network ... not found" or similar

Try `docker compose down` first (without `-v`), then `docker compose up` again. If that fails, you can safely `docker network prune` — no data loss, but confirm with the user.

### Managers log `Connection refused` exporting to `http://localhost:4317` (OTEL)

**Not a failure.** OTEL is often enabled in a lab's `.env`, but the OTEL collector may not be running on 4317. A plain `docker compose up` (no collector) has nothing listening on 4317, so every manager logs periodic export errors. `/health` still returns 200 and the lab works normally.

Options:
- Ignore it (default).
- Start an observability stack (e.g. an `otel` compose profile if the lab defines one).
- Disable OTEL by setting `*_OTEL_ENABLED=false` in `.env`.

### Root-owned files appear in `.madsci/`, or managers can't write PIDs/logs

Cause: `docker compose up` was run without setting `USER_ID`/`GROUP_ID`, so the containers wrote the mounted `.madsci/` volume as root. Fix:
```bash
echo "USER_ID=$(id -u)"  >> .env
echo "GROUP_ID=$(id -g)" >> .env
sudo chown -R "$(id -u):$(id -g)" ./.madsci   # only if root-owned files already exist
docker compose down && docker compose up -d
```
Better: use `madsci start` — the CLI wraps the compose call with the right env vars.

---

## 3. Port conflicts

### `bind: address already in use` on 8000 / 8001 / 8002 / 8003 / 8004 / 8005 / 8006

Ports map: 8000 dashboard (Squid), 8001 Event, 8002 Experiment, 8003 Resource, 8004 Data, 8005 Workcell, 8006 Location.

**Diagnose:**
```bash
# Linux/macOS:
lsof -i :<port>
# or, wider view:
ss -tulpn | grep :<port>
```

**Fixes (SKILL.md §6.1 prompt):**
- Stop the offending process (only if user identifies it).
- Remap the port. For Install Options 1/2 (repo-in-place), edit `$INSTALL_DIR/.env` (e.g. `LAB_SERVER_PORT=...`); for Option 3, edit the user's own `settings.yaml` / `.env`. Show the diff before applying.
- Abort and let the user free the port on their own.

---

## 4. `.madsci/` sentinel resolution

### `madsci status` reports "no PID file" / behaves as if the lab isn't running, but `docker compose ps` shows it up

Cause: the CWD is above or beside the `.madsci/` directory the service wrote its PID into. See [src/madsci_common/madsci/common/sentry.py](../../../src/madsci_common/madsci/common/sentry.py) and the *Settings Directory (Walk-Up Discovery)* section of [CLAUDE.md](../../../CLAUDE.md).

**Diagnose:**
```bash
python3 -c "from madsci.common.sentry import find_madsci_dir; print(find_madsci_dir())"
```

**Fixes (SKILL.md §6.2 prompt):**
- `cd` into the lab directory (the one containing `.madsci/` or `.git/`).
- Set `MADSCI_SETTINGS_DIR=/path/to/lab` in the environment.
- Pass `--settings-dir /path/to/lab` on the `madsci` command (supported on `start`, `config export`, etc.).
- Scaffold a fresh `.madsci/` in CWD via the sentry helpers if the user actually wants one here.

### Two labs share `~/.madsci/` and their PIDs / logs collide

The user probably ran `madsci start` from a directory with no `.madsci/` and no `.git/`, so it fell back to `~/.madsci/`. Give each lab its own sentinel:
```bash
mkdir -p /path/to/lab/.madsci
# or let ensure_madsci_dir() scaffold the standard subdirs — pass the PARENT
# directory; the helper appends `.madsci` itself (passing a path ending in
# `.madsci` would nest it as `.madsci/.madsci/`):
python3 -c "from madsci.common.sentry import ensure_madsci_dir; ensure_madsci_dir('/path/to/lab')"
```

---

## 5. Database

### FerretDB / Postgres container starts but the manager fails to connect

- Check `settings.yaml` and `.env` for the DB URL (see [Configuration.md](../../../docs/Configuration.md)). Common mistake: `localhost` in `.env` when the manager is inside a compose network that names the DB `ferretdb` or `postgres`.
- Confirm the env var prefix matches the manager: `EVENT_`, `WORKCELL_`, `RESOURCE_`, etc.
- URLs must be [`AnyUrl`](../../../src/madsci_common/madsci/common/) — trailing slash is added automatically; do not fight it.

### `alembic` migration fails on Resource Manager startup

Pre-migration backup runs automatically ([CLAUDE.md](../../../CLAUDE.md) *Database Migrations* section) and auto-restores on failure. Ask the user:
1. Look at the auto-created backup in the backup dir before retrying.
2. Retry with `python -m madsci.resource_manager.migration_tool --db_url <url>` after fixing the schema issue (snake_case — pydantic-settings' CLI parser silently drops the kebab-case `--db-url` because `cli_ignore_unknown_args=True`).
3. Restore from backup and roll back to the prior MADSci version.

### `Database schema version mismatch detected; server startup aborted`

Resource Manager runs a `DatabaseVersionChecker` on init that compares the installed MADSci version against `madsci_schema_version` in the mounted database. This fires when a fresh install is pointed at existing DB data (see SKILL.md §2 existing-data flow). **Don't improvise a fix here** — ask the exact "Version mismatch" question from SKILL.md §2 (migrate / load anyway, ignore / discard and start fresh) and apply the chosen branch; SKILL.md §6.4 is the pointer back to it from a startup failure. The migration command, if chosen, is `python -m madsci.resource_manager.migration_tool --db_url <url>` (snake_case — the kebab-case form is silently discarded by pydantic-settings).

---

## 6. Frontend / dashboard

### `yarn build` in `ui/` fails with peer-dep errors

Use `yarn`, not `npm` (per [CLAUDE.md](../../../CLAUDE.md)). If a previous `npm install` created a `package-lock.json`, delete it and rerun `yarn install`.

### Dashboard at `http://localhost:8000/` returns 404 JSON instead of HTML

The Lab Manager API is up but no dashboard bundle is mounted. This is unexpected — the compose file should be using the `madsci_dashboard` image, which bakes in the UI. Check: `docker compose ps` should show `lab_manager` running from `ghcr.io/ad-sdl/madsci_dashboard:*`, not `ghcr.io/ad-sdl/madsci:*`. If it's the base image, either the compose file is wrong or the image tag was overridden.

### Dashboard returns 502 / connection refused

The Lab Manager (Squid) isn't running. `docker compose ps lab_manager` (or `madsci status`) will show whether the container is up — the compose service is named `lab_manager`, not `squid`. If it's up but responds 502, tail its logs — usually a downstream manager crash cascading up.

---

## 7. Uninstall / teardown

Failure modes seen while **removing** MADSci. See [uninstall.md](uninstall.md) for the scoped teardown flow and `uninstall-check.sh` for verification.

### `docker compose down` / `madsci stop` leaves the databases intact — data survives a "wipe"

**By design, and the #1 uninstall gotcha.** MADSci compose configurations typically use **bind mounts to `./.madsci/`, not named Docker volumes**. Therefore:
- `docker compose down -v` and `madsci stop --volumes` remove named volumes — **of which there are none** — so they delete *no* database data.
- The real data lives in `./.madsci/postgresql`, `./.madsci/postgresql_resources`, `./.madsci/mongodb`, `./.madsci/valkey`, `./.madsci/seaweedfs`.

To actually delete the data, those directories have to be removed on the host — which is **the operator's command to run, not yours**. Resolve and print the path, offer a backup, and hand over the `sudo rm -rf` per uninstall.md §U3.

### `rm: cannot remove '.madsci/postgresql/...': Permission denied`

The DB data dirs were created **by the containers as root**, so a non-root user can't delete them — this is the operator hitting the §U3 hand-off, not a failure on your side.

Run the read-only half yourself to prepare the hand-off:
```bash
docker compose down                      # release the dirs first — safe, reversible
ls -la "$MADSCI_DIR"                     # show which entries are root-owned
```
Then give them the `sudo` command to run, with `$MADSCI_DIR` expanded to the literal resolved path:
```bash
sudo rm -rf "$MADSCI_DIR/postgresql" "$MADSCI_DIR/postgresql_resources" \
            "$MADSCI_DIR/mongodb" "$MADSCI_DIR/valkey" "$MADSCI_DIR/seaweedfs"
```
Do not run it on their behalf, and never put a path in front of `sudo rm -rf` that you haven't printed back to them first.

### `madsci` still resolves after the venv was deleted

The install's only Python footprint is the project-local venv at `$INSTALL_DIR/.venv/`, removed with `rm -rf` (uninstall.md §U2) — there is no `pip uninstall` step. If `madsci` still runs afterwards, it came from somewhere else: a pre-existing system/user install, another lab's venv, or a stale shell hash. Check `which -a madsci` and `hash -r`, then re-check. Leave any install outside `$INSTALL_DIR` alone unless the user explicitly asks for it.

### `docker compose down` errors because a container "is in use" / won't stop

A detached manager/node may still hold a port or a data dir. Find detached MADSci processes via PID files:
```bash
ls .madsci/pids/                          # *.pid files for detached managers/nodes
madsci stop manager <name>                # SIGTERM→SIGKILL, removes the PID file
madsci stop node <name>
```

### `docker rmi` fails: "image is being used by stopped container"

Containers must be removed before their images. Run `docker compose down` (removes containers), then `docker rmi ...`. Do not reach for `docker system prune -a` on the user's behalf — it deletes unrelated images/build cache; offer it as something they run themselves.

### `uninstall-check.sh` reports FAIL but the user says they removed everything

Check the **scope** you passed. `--scope stop` only expects the stack halted + ports free; `--scope remove` also expects MADSci Docker images gone. A "FAIL" on images under `--scope remove` is correct if the user *chose to keep* images — re-run with `--scope stop`, or accept the image lines as intentional. Also pass `--madsci-dir <path>` if `.madsci/` isn't at `./.madsci`.

`--scope wipe` additionally expects `.madsci/` to be gone. It is **verify-only** — the skill never deletes that directory (uninstall.md §U3 hands the command to the operator), so a FAIL here means their `rm` didn't land where you resolved the path, not that a step of yours failed. Re-check `--madsci-dir` against the path they actually deleted.

---

## When none of the above matches

Escalate to the user with:
1. The exact command you ran.
2. The full stderr (do not summarize).
3. The output of `install-check.sh` (install) or `uninstall-check.sh` (teardown) if the operation partially completed.
4. An AskUserQuestion offering: retry with a different `$INSTALL_DIR`, change the uninstall scope, roll back the last step, or hand off to a human.
