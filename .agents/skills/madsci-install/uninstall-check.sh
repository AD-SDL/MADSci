#!/usr/bin/env bash
# uninstall-check.sh — verify a MADSci teardown actually removed what the scope asked for.
#
# A clean uninstall is "nothing answers and nothing is left", not "the command exited 0".
# Mirror image of install-check.sh: every check here PASSES when the thing is *absent*
# (containers gone, ports free, images/.madsci/packages removed).
#
# Usage:
#   bash uninstall-check.sh --method docker --scope stop     # containers down, ports free
#   bash uninstall-check.sh --method docker --scope remove   # + images removed
#   bash uninstall-check.sh --method docker --scope wipe     # + .madsci/ deleted
#   bash uninstall-check.sh --method local  --scope remove   # pip packages uninstalled
#   bash uninstall-check.sh --method local  --scope wipe     # + .madsci/ deleted
#   bash uninstall-check.sh --managers 8001,8002      # override which ports must be free
#   bash uninstall-check.sh --dashboard-port 8000
#   bash uninstall-check.sh --madsci-dir ./.madsci    # override where .madsci/ is expected
#   bash uninstall-check.sh --no-color
#
# Scopes (additive):
#   stop   — running stack halted: no containers/processes, ports free.
#   remove — the above + Docker images removed (method=docker) and/or pip packages
#            uninstalled (method=local).
#   wipe   — the above + .madsci/ data directory deleted.
#
# Scope: this script certifies teardown of a MADSci stack. It does NOT check for a
# dev-repo `.venv/` or pre-commit hook removal — those are contributor-tooling
# concerns handled by a different skill.
#
# Exit codes:
#   0 = all checks passed (teardown clean for the requested scope)
#   1 = one or more checks failed (something is still present)
#   2 = usage error

set -u  # keep -e OFF: run every check even if an earlier one fails.

# ---------- args ----------
METHOD=""
SCOPE="stop"
MANAGERS="8001,8002,8003,8004,8005,8006"
DASHBOARD_PORT="8000"
MADSCI_DIR="./.madsci"
USE_COLOR=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --method)          METHOD="${2:-}"; shift 2 ;;
    --scope)           SCOPE="${2:-}"; shift 2 ;;
    --managers)        MANAGERS="${2:-}"; shift 2 ;;
    --dashboard-port)  DASHBOARD_PORT="${2:-}"; shift 2 ;;
    --madsci-dir)      MADSCI_DIR="${2:-}"; shift 2 ;;
    --no-color)        USE_COLOR=0; shift ;;
    -h|--help)
      sed -n '2,34p' "$0"; exit 0 ;;
    --goal)
      echo "Error: --goal was removed. Use --method docker|local instead. See --help." >&2
      exit 2 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$METHOD" ]]; then
  echo "Error: --method is required (docker|local). See --help." >&2
  exit 2
fi
if [[ "$METHOD" != "docker" && "$METHOD" != "local" ]]; then
  echo "--method must be 'docker' or 'local' (got: $METHOD)" >&2
  exit 2
fi
if [[ ! "$SCOPE" =~ ^(stop|remove|wipe)$ ]]; then
  echo "--scope must be stop, remove, or wipe (got: $SCOPE)" >&2; exit 2
fi

# ---------- output helpers ----------
if [[ $USE_COLOR -eq 1 && -t 1 ]]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; DIM=""; RESET=""
fi

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() { printf "  %sPASS%s  %s\n" "$GREEN" "$RESET" "$1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { printf "  %sFAIL%s  %s%s%s\n" "$RED" "$RESET" "$1" "${2:+ — $2}" ""; FAIL_COUNT=$((FAIL_COUNT+1)); }
skip() { printf "  %sSKIP%s  %s%s%s\n" "$YELLOW" "$RESET" "$1" "${2:+ — $2}" ""; SKIP_COUNT=$((SKIP_COUNT+1)); }
section() { printf "\n%s== %s ==%s\n" "$DIM" "$1" "$RESET"; }

# MADSci container names created by the example lab compose (fixed via container_name:).
MADSCI_CONTAINERS=(
  lab_manager event_manager experiment_manager resource_manager data_manager
  location_manager workcell_manager liquidhandler_1 liquidhandler_2 robotarm_1
  platereader_1 advanced_example_node sila_example_server notebook_validator
  madsci_ferretdb madsci_valkey madsci_postgres madsci_postgres_resources madsci_seaweedfs
)

# MADSci images the install may have pulled/built.
MADSCI_IMAGES=(
  ghcr.io/ad-sdl/madsci ghcr.io/ad-sdl/madsci_dashboard
)

# ---------- individual checks ----------

check_no_containers() {
  # For --method local, there should be no MADSci containers; but the user may
  # still have some laying around from a prior Docker install — probe anyway so
  # the check surfaces them.
  section "MADSci containers stopped/removed"
  if ! command -v docker >/dev/null 2>&1; then
    if [[ "$METHOD" == "docker" ]]; then
      fail "docker CLI on PATH" "required to verify --method docker teardown"
    else
      skip "docker container check" "docker CLI not on PATH (fine for --method local)"
    fi
    return
  fi
  if ! docker info >/dev/null 2>&1; then
    skip "docker container check" "docker daemon not reachable"
    return
  fi

  local running
  running="$(docker ps --format '{{.Names}}' 2>/dev/null)"
  local found=0
  for name in "${MADSCI_CONTAINERS[@]}"; do
    if grep -qx "$name" <<<"$running"; then
      fail "container '$name' still running"
      found=1
    fi
  done
  [[ $found -eq 0 ]] && pass "no MADSci containers running"

  # For remove/wipe, containers should also be fully removed (not just stopped).
  if [[ "$SCOPE" != "stop" ]]; then
    local all_containers
    all_containers="$(docker ps -a --format '{{.Names}}' 2>/dev/null)"
    local leftover=0
    for name in "${MADSCI_CONTAINERS[@]}"; do
      if grep -qx "$name" <<<"$all_containers"; then
        fail "container '$name' still exists (stopped)" "run 'docker compose down'"
        leftover=1
      fi
    done
    [[ $leftover -eq 0 ]] && pass "no MADSci containers exist (removed)"
  fi
}

check_ports_free() {
  section "Manager & dashboard ports free"
  local ports=()
  IFS=',' read -r -a mports <<< "$MANAGERS"
  ports+=("${mports[@]}")
  ports+=("$DASHBOARD_PORT")

  for port in "${ports[@]}"; do
    port="${port// /}"
    [[ -z "$port" ]] && continue
    # A freed port must NOT answer /health.
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 "http://localhost:${port}/health" 2>/dev/null)"
    code="${code:-000}"
    if [[ "$code" == "200" ]]; then
      fail "port $port still serving /health (HTTP 200)" "a manager/dashboard is still up"
    else
      pass "port $port free (no /health response)"
    fi
  done
}

check_images_removed() {
  # Only relevant for remove/wipe with method=docker.
  case "$SCOPE" in stop) return ;; esac
  [[ "$METHOD" != "docker" ]] && return
  section "MADSci Docker images removed"
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    skip "image removal check" "docker not available"
    return
  fi
  local imgs
  imgs="$(docker images --format '{{.Repository}}' 2>/dev/null)"
  local found=0
  for img in "${MADSCI_IMAGES[@]}"; do
    if grep -qx "$img" <<<"$imgs"; then
      fail "image '$img' still present" "docker rmi it (or user chose to keep images)"
      found=1
    fi
  done
  [[ $found -eq 0 ]] && pass "MADSci app images removed (madsci, madsci_dashboard)"
}

check_madsci_dir_gone() {
  # Only meaningful for a full wipe.
  [[ "$SCOPE" != "wipe" ]] && return
  section ".madsci/ data directory removed"
  if [[ -e "$MADSCI_DIR" ]]; then
    # Report what's left so the user can see root-owned leftovers.
    local leftover
    leftover="$(ls -A "$MADSCI_DIR" 2>/dev/null | tr '\n' ' ')"
    fail ".madsci/ still exists at $MADSCI_DIR" "remaining: ${leftover:-<empty>} (root-owned dirs need sudo rm)"
  else
    pass ".madsci/ removed ($MADSCI_DIR absent)"
  fi
}

check_no_local_process() {
  # For --method local: the `madsci start --mode local` process should be gone.
  [[ "$METHOD" != "local" ]] && return
  section "Native (--mode local) process stopped"
  local pids
  pids="$(pgrep -f 'madsci start --mode local' 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')"
  if [[ -z "$pids" ]]; then
    pass "no 'madsci start --mode local' process running"
  else
    fail "PID(s) still running: $pids" "kill them with 'pkill -f \"madsci start --mode local\"' or 'kill <pid>'"
  fi
}

check_no_stale_pids() {
  # Detached managers/nodes leave PID files under .madsci/pids/.
  section "No stale PID files"
  local pids_dir="${MADSCI_DIR%/}/pids"
  if [[ ! -d "$pids_dir" ]]; then
    pass "no pids/ directory (nothing detached, or already removed)"
    return
  fi
  local stale
  stale="$(find "$pids_dir" -maxdepth 1 -name '*.pid' 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$stale" == "0" ]]; then
    pass "no *.pid files in $pids_dir"
  else
    fail "$stale PID file(s) remain in $pids_dir" "run 'madsci stop manager/node <name>' or delete them"
  fi
}

check_packages_uninstalled() {
  # Only relevant for method=local (host pip install). --method docker doesn't
  # touch host pip packages (except optionally madsci-client for the CLI, which
  # a user may want to keep independent of tearing down the Docker stack).
  [[ "$METHOD" != "local" ]] && return
  [[ "$SCOPE" == "stop" ]] && return
  section "MADSci Python packages uninstalled"

  if command -v madsci >/dev/null 2>&1; then
    fail "madsci CLI still on PATH" "provided by madsci.client — pip uninstall it or deactivate the venv"
  else
    pass "madsci CLI not on PATH"
  fi

  for pkg in madsci.common madsci.client; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
      fail "import ${pkg} still succeeds" "still installed in the active environment"
    else
      pass "import ${pkg} fails (uninstalled)"
    fi
  done
}

# ---------- run ----------
printf "MADSci uninstall verification (method=%s, scope=%s)\n" "$METHOD" "$SCOPE"

check_no_containers
check_no_local_process
check_ports_free
check_images_removed
check_madsci_dir_gone
check_no_stale_pids
check_packages_uninstalled

# ---------- summary ----------
section "Summary"
printf "  %sPassed%s: %d    %sFailed%s: %d    %sSkipped%s: %d\n" \
  "$GREEN" "$RESET" "$PASS_COUNT" \
  "$RED" "$RESET" "$FAIL_COUNT" \
  "$YELLOW" "$RESET" "$SKIP_COUNT"

if (( FAIL_COUNT > 0 )); then
  printf "\n%sUninstall verification FAILED.%s Something is still present — see the failing checks above and troubleshooting.md §Uninstall.\n" "$RED" "$RESET"
  exit 1
fi

printf "\n%s✅ Uninstall verification PASSED.%s Teardown clean for scope '%s'.\n" "$GREEN" "$RESET" "$SCOPE"
exit 0
