# MADSci Install-Time Troubleshooting

Failure modes seen during install / first-startup, keyed by the message the user is likely to paste at you. **Match on the signature, run the AskUserQuestion prompt from the parent SKILL.md, then apply the fix.** Do not silently retry.

For runtime troubleshooting (workflows failing mid-run, node action errors, resource lock issues, etc.) see [../../../docs/guides/troubleshooting.md](../../../docs/guides/troubleshooting.md) instead.

---

## 1. PDM / dependency resolution

### `pdm install` fails with "unable to find a resolution" / "conflicts detected"

**Cause:** `pdm.lock` in this repo was generated with [uv](https://docs.astral.sh/uv/) as the resolver ([CONTRIBUTING.md](../../CONTRIBUTING.md) documents this). Stock PDM's resolver may reject it.

**Fixes (offer both — see SKILL.md §4.1):**
```bash
pip install uv
pdm config use_uv true
pdm install -G:all       # or `just init`
```
or
```bash
rm pdm.lock              # DO NOT commit the regenerated lockfile without asking
pdm install -G:all
```

### `pdm install` succeeds but `import madsci.<x>` fails

Almost never a PDM bug; almost always a wrong-venv problem. Jump to §2.

---

## 2. Wrong virtualenv

### `ModuleNotFoundError: No module named 'madsci'` (or a submodule)

**Diagnose first:**
```bash
which python
python -c "import sys; print(sys.executable, sys.prefix)"
pip list | grep -i madsci
```

**Fixes:**
- Contributor (goal 4): `eval $(pdm venv activate)` then retry, or prefix commands with `pdm run` (e.g. `pdm run pytest`).
- End user (goals 2/3): activate the venv you installed into. If unsure which one, reinstall into the currently-active one after confirming with the user.

### `madsci: command not found` after `pip install madsci-client`

The install went to a Python whose `bin/` isn't on `PATH`. Options to offer:
1. Activate that venv (recommended).
2. Reinstall into a venv that is on PATH.
3. Run via `python -m madsci ...` where supported.

---

## 3. Docker

### `docker: command not found` or `Cannot connect to the Docker daemon`

Offer the four options from SKILL.md §Step 2 (Docker Missing prompt): install Docker, switch to `--mode=local`, use Rancher/Podman, or abort.

### `docker compose up` starts but a service stays `unhealthy`

**Diagnose:**
```bash
docker compose logs --tail=200 <service-name>
docker compose ps
```

**Common causes:**
- A previous run left an incompatible volume (schema mismatch after a migration). Fix: `docker compose down -v` — DATA LOSS, confirm first (SKILL.md §4.5).
- First-time image pull still in progress. Fix: wait 60s, re-check.
- Host port already bound (see §4).

### `docker compose up` fails immediately with "network madsci_default not found" or similar

Try `docker compose down` first (without `-v`), then `docker compose up` again. If that fails, you can safely `docker network prune` — no data loss, but confirm with the user.

---

## 4. Port conflicts

### `bind: address already in use` on 8000 / 8001 / 8002 / 8003 / 8004 / 8005 / 8006

Ports map: 8000 dashboard (Squid), 8001 Event, 8002 Experiment, 8003 Resource, 8004 Data, 8005 Workcell, 8006 Location.

**Diagnose:**
```bash
# Linux/macOS:
lsof -i :<port>
# or, wider view:
ss -tulpn | grep :<port>
```

**Fixes (SKILL.md §4.3 prompt):**
- Stop the offending process (only if user identifies it).
- Remap the port. The root-level [compose.yaml](../../compose.yaml) uses **host network mode**, so remapping means changing the *service's bind address*, not a `-p host:container` line. For the example lab that is set via env vars in `settings.yaml` under [examples/example_lab/](../../examples/example_lab/).
- Abort and let the user free the port on their own.

---

## 5. `.madsci/` sentinel resolution

### `madsci status` reports "no PID file" / behaves as if the lab isn't running, but `docker compose ps` shows it up

Cause: the CWD is above or beside the `.madsci/` directory the service wrote its PID into. See [src/madsci_common/madsci/common/sentry.py](../../src/madsci_common/madsci/common/sentry.py) and the *Settings Directory (Walk-Up Discovery)* section of [CLAUDE.md](../../CLAUDE.md).

**Diagnose:**
```bash
python3 -c "from madsci.common.sentry import find_madsci_dir; print(find_madsci_dir())"
```

**Fixes (SKILL.md §4.4 prompt):**
- `cd` into the lab directory (the one containing `.madsci/` or `.git/`).
- Set `MADSCI_SETTINGS_DIR=/path/to/lab` in the environment.
- Pass `--settings-dir /path/to/lab` on the `madsci` command (supported on `start`, `config export`, etc.).
- Scaffold a fresh `.madsci/` in CWD via the sentry helpers if the user actually wants one here.

### Two labs share `~/.madsci/` and their PIDs / logs collide

The user probably ran `madsci start` from a directory with no `.madsci/` and no `.git/`, so it fell back to `~/.madsci/`. Give each lab its own sentinel:
```bash
mkdir -p /path/to/lab/.madsci
# or let ensure_madsci_dir() scaffold the standard subdirs:
python3 -c "from madsci.common.sentry import ensure_madsci_dir; ensure_madsci_dir('/path/to/lab/.madsci')"
```

---

## 6. Database

### FerretDB / Postgres container starts but the manager fails to connect

- Check `settings.yaml` and `.env` for the DB URL (see [Configuration.md](../../docs/Configuration.md)). Common mistake: `localhost` in `.env` when the manager is inside a compose network that names the DB `ferretdb` or `postgres`.
- Confirm the env var prefix matches the manager: `EVENT_`, `WORKCELL_`, `RESOURCE_`, etc.
- URLs must be [`AnyUrl`](../../src/madsci_common/madsci/common/) — trailing slash is added automatically; do not fight it.

### `alembic` migration fails on Resource Manager startup

Pre-migration backup runs automatically ([CLAUDE.md](../../CLAUDE.md) *Database Migrations* section) and auto-restores on failure. Ask the user:
1. Look at the auto-created backup in the backup dir before retrying.
2. Retry with `python -m madsci.resource_manager.migration_tool --db-url <url>` after fixing the schema issue.
3. Restore from backup and roll back to the prior MADSci version.

---

## 7. Frontend / dashboard

### `yarn dev` in `ui/` fails with peer-dep errors

Use `yarn`, not `npm` (per [CLAUDE.md](../../CLAUDE.md)). If a previous `npm install` created a `package-lock.json`, delete it and rerun `yarn install`.

### Dashboard at `http://localhost:8000` returns 502 / connection refused

- The dashboard is served by `madsci.squid`. Confirm the Squid container / process is running (`docker compose ps squid` or `madsci status`).
- If Squid is up but the dashboard is blank, the frontend build wasn't included in the image. Rebuild: `just build` (or `docker compose build squid`).

---

## 8. Pre-commit hooks (goal 4 only)

### `pre-commit install` fails during `just init`

Usually a stale `~/.cache/pre-commit`. Fix:
```bash
pre-commit clean
pre-commit install
```

### A hook fails on a file you didn't touch

Ratchets (see [../code-ratchets/SKILL.md](../code-ratchets/SKILL.md)) count deprecated patterns across the whole repo and fail if the count moved either direction. Do **not** silence with `--no-verify` without user permission ([CLAUDE.md](../../CLAUDE.md) is explicit about this).

---

## When none of the above matches

Escalate to the user with:
1. The exact command you ran.
2. The full stderr (do not summarize).
3. The output of `install-check.sh` if the stack partially came up.
4. An AskUserQuestion offering: try a different install goal, roll back the last step, or hand off to a human.
