#!/usr/bin/env bash
# uninstall-check.sh — verify a MADSci Docker teardown actually removed what the scope asked for.
#
# A clean uninstall is "nothing answers and nothing is left", not "the command exited 0".
# Mirror image of install-check.sh: every check here PASSES when the thing is *absent*
# (containers gone, ports free, images / .madsci/ removed).
#
# Usage:
#   bash uninstall-check.sh --scope stop     # containers down, ports free
#   bash uninstall-check.sh --scope remove   # + images removed
#   bash uninstall-check.sh --scope wipe     # + .madsci/ deleted (verify-only, see below)
#   bash uninstall-check.sh --managers 8001,8002             # override which ports must be free
#   bash uninstall-check.sh --dashboard-port 8000
#   bash uninstall-check.sh --madsci-dir <path>              # path to .madsci/ (required for --scope wipe)
#   bash uninstall-check.sh --compose-project madsci_example_lab  # Docker Compose project label to probe
#   bash uninstall-check.sh --no-color
#
# Scopes (additive):
#   stop   — running stack halted: no containers, ports free.
#   remove — the above + MADSci Docker images removed.
#   wipe   — the above + .madsci/ data directory deleted. VERIFY-ONLY: the skill
#            never deletes .madsci/ (uninstall.md §U3 hands that command to the
#            operator). Use this scope to confirm a deletion they already ran.
#
# IMPORTANT: --madsci-dir
#   REQUIRED with --scope wipe (the script exits 2 without it). That scope
#   asserts a directory is GONE, so a wrong path looks exactly like success.
#   The default ./.madsci is relative to the CWD; with the install skill's
#   Options 1 / 2 the data lives at $INSTALL_DIR/.madsci ($INSTALL_DIR is chosen
#   at install Step 1.2), so pass --madsci-dir "$INSTALL_DIR/.madsci".
#   Optional for stop/remove, where it only locates the stale-PID check.
#
# This script does NOT check for a dev-repo `.venv/` or pre-commit hook removal —
# those are contributor-tooling concerns handled by a different skill.
#
# Exit codes:
#   0 = all checks passed (teardown clean for the requested scope)
#   1 = one or more checks failed (something is still present)
#   2 = usage error

set -u  # keep -e OFF: run every check even if an earlier one fails.

# ---------- args ----------
SCOPE="stop"
MANAGERS="8001,8002,8003,8004,8005,8006"
DASHBOARD_PORT="8000"
MADSCI_DIR="./.madsci"
MADSCI_DIR_EXPLICIT=0
COMPOSE_PROJECT="madsci_example_lab"
USE_COLOR=1

# Guard against value-taking flags being the last argument: without this, an
# empty "${2:-}" + failing `shift 2` under `set +e` would loop forever.
need_value() {
  # usage: need_value <flag-name> <remaining-arg-count>
  [[ "$2" -ge 2 ]] && return 0
  echo "Error: $1 requires a value" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope)            need_value "$1" "$#"; SCOPE="$2"; shift 2 ;;
    --managers)         need_value "$1" "$#"; MANAGERS="$2"; shift 2 ;;
    --dashboard-port)   need_value "$1" "$#"; DASHBOARD_PORT="$2"; shift 2 ;;
    --madsci-dir)       need_value "$1" "$#"; MADSCI_DIR="$2"; MADSCI_DIR_EXPLICIT=1; shift 2 ;;
    --compose-project)  need_value "$1" "$#"; COMPOSE_PROJECT="$2"; shift 2 ;;
    --no-color)         USE_COLOR=0; shift ;;
    -h|--help)
      sed -n '2,40p' "$0"; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$SCOPE" =~ ^(stop|remove|wipe)$ ]]; then
  echo "--scope must be stop, remove, or wipe (got: $SCOPE)" >&2; exit 2
fi

# --scope wipe asserts a directory is GONE, so a wrong path is indistinguishable
# from success: the default is relative, and from the wrong CWD this check
# cheerfully certifies a deletion that never happened. Refuse to guess.
if [[ "$SCOPE" == "wipe" && $MADSCI_DIR_EXPLICIT -eq 0 ]]; then
  cat >&2 <<'EOF'
Error: --scope wipe requires an explicit --madsci-dir.

  The default (./.madsci) is relative to the current directory. Run from
  anywhere else and the "removed" check PASSES against a path that was never
  the lab's data directory — certifying a deletion that did not happen.

  Pass the path resolved in uninstall.md §U3, e.g.:
    --madsci-dir "$INSTALL_DIR/.madsci"

  To check only the containers/ports/images, use --scope stop or --scope remove.
EOF
  exit 2
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
# Used only as a fallback when the compose-project label filter returns nothing — a user
# running a non-example lab should pass --compose-project to get a correct check.
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
  section "MADSci containers stopped/removed (compose project: $COMPOSE_PROJECT)"
  if ! command -v docker >/dev/null 2>&1; then
    fail "docker CLI on PATH" "required to verify Docker teardown"
    return
  fi
  if ! docker info >/dev/null 2>&1; then
    skip "docker container check" "docker daemon not reachable"
    return
  fi

  # Prefer the Compose project label — it accurately targets the stack the user
  # started, regardless of container naming. Fall back to the hard-coded names
  # (and SKIP vacuously-passing checks) only if the label query returns nothing
  # AND no legacy container names match either.
  local label_running label_all
  label_running="$(docker ps        --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --format '{{.Names}}' 2>/dev/null)"
  label_all="$(docker ps -a         --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --format '{{.Names}}' 2>/dev/null)"

  if [[ -n "$label_running" ]]; then
    while read -r name; do
      [[ -z "$name" ]] && continue
      fail "container '$name' still running (project=$COMPOSE_PROJECT)"
    done <<<"$label_running"
  elif [[ "$SCOPE" == "stop" ]]; then
    pass "no containers running under project '$COMPOSE_PROJECT'"
  fi

  if [[ "$SCOPE" != "stop" ]]; then
    local leftover
    leftover="$(comm -23 <(printf '%s\n' "$label_all" | sort -u) <(printf '%s\n' "$label_running" | sort -u))"
    if [[ -n "$leftover" && "$leftover" != $'\n' ]]; then
      while read -r name; do
        [[ -z "$name" ]] && continue
        fail "container '$name' still exists (stopped under project=$COMPOSE_PROJECT)" "run 'docker compose down'"
      done <<<"$leftover"
    elif [[ -z "$label_all" ]]; then
      :  # fall through to the legacy name check below
    else
      pass "all containers removed under project '$COMPOSE_PROJECT'"
    fi
  fi

  # Legacy name fallback — informational if we found NO label matches at all.
  if [[ -z "$label_all" ]]; then
    local running all
    running="$(docker ps --format '{{.Names}}' 2>/dev/null)"
    all="$(docker ps -a --format '{{.Names}}' 2>/dev/null)"
    local any=0
    for name in "${MADSCI_CONTAINERS[@]}"; do
      if grep -qx "$name" <<<"$all"; then
        any=1
        if grep -qx "$name" <<<"$running"; then
          fail "container '$name' still running (matched by legacy name)"
        elif [[ "$SCOPE" != "stop" ]]; then
          fail "container '$name' still exists (stopped, matched by legacy name)" "run 'docker rm $name'"
        fi
      fi
    done
    if (( any == 0 )); then
      skip "container check (compose project '$COMPOSE_PROJECT' not found and no legacy MADSci container names present)" \
        "nothing to verify — pass --compose-project if you used a different name"
    fi
  fi
}

# Deciding "this port is free" from a failed HTTP request is unsound: a slow host
# tripping --max-time and a service that is listening but doesn't answer /health
# are both indistinguishable from "nothing is listening" — and each one produced
# a PASS. Ask the kernel for the listener instead.
PORT_PROBE=""
if command -v ss >/dev/null 2>&1; then
  PORT_PROBE="ss"
elif command -v lsof >/dev/null 2>&1; then
  PORT_PROBE="lsof"
fi

# port_listening <port> -> 0 = listening, 1 = not listening
port_listening() {
  local port="$1"
  case "$PORT_PROBE" in
    ss)
      # Local Address:Port column, e.g. 0.0.0.0:8001, *:8001, [::]:8001
      ss -ltn 2>/dev/null | grep -qE "[:.]${port}[[:space:]]" ;;
    lsof)
      lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1 ;;
    *)
      return 1 ;;
  esac
}

check_ports_free() {
  section "Manager & dashboard ports free"
  local ports=()
  IFS=',' read -r -a mports <<< "$MANAGERS"
  ports+=("${mports[@]}")
  ports+=("$DASHBOARD_PORT")

  if [[ -z "$PORT_PROBE" ]]; then
    # No probe = no evidence. Report that honestly instead of passing.
    skip "port-free checks (${#ports[@]} ports)" \
         "neither 'ss' nor 'lsof' on PATH — cannot prove a port is free; install iproute2 or lsof and re-run"
    return
  fi

  for port in "${ports[@]}"; do
    port="${port// /}"
    [[ -z "$port" ]] && continue
    if port_listening "$port"; then
      fail "port $port still has a listener" \
           "something is bound to it — 'sudo ss -ltnp sport = :$port' names the process"
    else
      pass "port $port free (no listener, via $PORT_PROBE)"
    fi
  done
}

check_images_removed() {
  case "$SCOPE" in stop) return ;; esac
  section "MADSci Docker images removed"
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    skip "image removal check" "docker not available"
    return
  fi
  local imgs
  imgs="$(docker images --format '{{.Repository}}' 2>/dev/null)"
  local checked=0 found=0
  for img in "${MADSCI_IMAGES[@]}"; do
    if grep -qx "$img" <<<"$imgs"; then
      fail "image '$img' still present" "docker rmi it (or user chose to keep images)"
      found=1
      checked=1
    fi
  done
  if (( checked == 0 )); then
    # Can't tell "removed" apart from "never pulled" — surface the ambiguity.
    skip "MADSci image removal" "no MADSci images present (removed or never pulled on this host)"
  elif (( found == 0 )); then
    pass "MADSci app images removed (madsci, madsci_dashboard)"
  fi
}

check_madsci_dir_gone() {
  [[ "$SCOPE" != "wipe" ]] && return
  section ".madsci/ data directory removed"
  if [[ -e "$MADSCI_DIR" ]]; then
    local leftover
    leftover="$(ls -A "$MADSCI_DIR" 2>/dev/null | tr '\n' ' ')"
    fail ".madsci/ still exists at $MADSCI_DIR" "remaining: ${leftover:-<empty>} (root-owned dirs need sudo rm)"
  else
    pass ".madsci/ removed ($MADSCI_DIR absent)"
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

# ---------- run ----------
printf "MADSci uninstall verification (scope=%s, compose-project=%s)\n" \
  "$SCOPE" "$COMPOSE_PROJECT"

check_no_containers
check_ports_free
check_images_removed
check_madsci_dir_gone
check_no_stale_pids

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
