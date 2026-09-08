#!/usr/bin/env bash
# install-check.sh — inspect a running MADSci stack and report pass/fail per check.
#
# Usage:
#   bash install-check.sh --method docker         # stack running under Docker Compose
#   bash install-check.sh --method local          # stack running via `madsci start --mode local`
#   bash install-check.sh --method docker --with-ui   # explicitly expect the dashboard UI at /
#   bash install-check.sh --method local --no-ui      # explicitly expect API-only at /
#   bash install-check.sh --managers 8001,8002,8003   # override which manager ports to check
#   bash install-check.sh --dashboard-port 8000       # override dashboard port
#   bash install-check.sh --no-color
#
# Method inference for the UI check when neither --with-ui nor --no-ui is passed:
#   --method docker → --with-ui  (compose deployments typically use the madsci_dashboard image
#                                 which bakes in the built UI; pass --no-ui if you're on a
#                                 slim compose that only runs the base madsci image)
#   --method local  → --no-ui    (pip install madsci.squid does not bundle the UI; pass
#                                 --with-ui if you built ui/dist and set LAB_DASHBOARD_FILES_PATH)
#
# Scope: this script certifies that a MADSci stack is up and answers correctly. It does
# NOT check for seeded resources / nodes / locations — those belong to a separate skill.
# It does NOT distinguish "which install goal" (example lab vs. user-created lab vs.
# per-package pip install) — the only axis it cares about is HOW the stack is running.
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed
#   2 = usage error

set -u  # keep -e OFF: we want every check to run even if earlier ones fail.

# ---------- args ----------
METHOD=""
MANAGERS="8001,8002,8003,8004,8005,8006"
DASHBOARD_PORT="8000"
USE_COLOR=1
UI_MODE=""  # "with", "no", or "" (=infer from method)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --method)          METHOD="${2:-}"; shift 2 ;;
    --managers)        MANAGERS="${2:-}"; shift 2 ;;
    --dashboard-port)  DASHBOARD_PORT="${2:-}"; shift 2 ;;
    --with-ui)         UI_MODE="with"; shift ;;
    --no-ui)           UI_MODE="no"; shift ;;
    --no-color)        USE_COLOR=0; shift ;;
    -h|--help)
      sed -n '2,29p' "$0"; exit 0 ;;
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

# Infer UI expectation from method when --with-ui/--no-ui not given.
if [[ -z "$UI_MODE" ]]; then
  case "$METHOD" in
    docker) UI_MODE="with" ;;
    local)  UI_MODE="no" ;;
  esac
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

# ---------- individual checks ----------

check_python() {
  section "Python & environment"

  if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 on PATH"
    return
  fi
  local ver
  ver="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)"
  if [[ -z "$ver" ]]; then
    fail "python3 --version" "python3 exists but wouldn't report a version"
    return
  fi

  local major minor
  major="$(cut -d. -f1 <<<"$ver")"
  minor="$(cut -d. -f2 <<<"$ver")"
  if (( major > 3 )) || { (( major == 3 )) && (( minor >= 10 )); }; then
    pass "python3 >= 3.10 (found $ver)"
  else
    fail "python3 >= 3.10 required" "found $ver"
  fi

  local which_py
  which_py="$(command -v python3)"
  printf "         %spython3 → %s%s\n" "$DIM" "$which_py" "$RESET"

  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    printf "         %sVIRTUAL_ENV=%s%s\n" "$DIM" "$VIRTUAL_ENV" "$RESET"
  else
    printf "         %s(no VIRTUAL_ENV set — expected for --method docker; unusual for --method local)%s\n" "$DIM" "$RESET"
  fi
}

check_madsci_importable() {
  section "MADSci Python packages"

  # --method local: MADSci is installed in a host venv; check imports there.
  # --method docker: MADSci lives inside containers. Try host first (the caller may
  #   have `pip install madsci-client` for the CLI); if not, fall back to probing
  #   a running manager container. Never fail on host imports for docker method —
  #   the host doesn't need MADSci to run a Docker stack.
  local pkgs=(madsci.common madsci.client madsci.squid)

  if [[ "$METHOD" == "local" ]]; then
    for pkg in "${pkgs[@]}"; do
      if python3 -c "import ${pkg}" 2>/dev/null; then
        pass "import ${pkg} (host)"
      else
        fail "import ${pkg}" "not installed in the active Python environment"
      fi
    done
    return
  fi

  # --method docker
  local host_has_madsci=0
  if python3 -c "import madsci.common" 2>/dev/null; then
    host_has_madsci=1
  fi

  if [[ $host_has_madsci -eq 1 ]]; then
    for pkg in "${pkgs[@]}"; do
      if python3 -c "import ${pkg}" 2>/dev/null; then
        pass "import ${pkg} (host)"
      else
        skip "import ${pkg} (host)" "not on host, but Docker method — checking containers"
      fi
    done
  fi

  # Also verify at least one manager container can import madsci.* — proves
  # the running Docker stack is actually MADSci, not just something on 8001.
  if ! command -v docker >/dev/null 2>&1; then
    if [[ $host_has_madsci -eq 0 ]]; then
      fail "MADSci packages" "not importable on host and docker CLI not on PATH — cannot verify"
    fi
    return
  fi
  # Find any running MADSci-flavored container. event_manager is the canonical starter,
  # but the check tolerates alternative service names too.
  local container=""
  for candidate in event_manager madsci-event-manager madsci_event_manager lab_manager; do
    if docker compose ps --status running 2>/dev/null | grep -q "^${candidate}\b\|[[:space:]]${candidate}[[:space:]]"; then
      container="$candidate"
      break
    fi
  done
  if [[ -z "$container" ]]; then
    if [[ $host_has_madsci -eq 0 ]]; then
      fail "container MADSci import" "no running MADSci manager container found via 'docker compose ps'"
    else
      skip "container MADSci import" "no MADSci manager container found; host imports covered above"
    fi
    return
  fi
  for pkg in madsci.common madsci.client; do
    if docker compose exec -T "$container" python3 -c "import ${pkg}" >/dev/null 2>&1; then
      pass "import ${pkg} (in container '$container')"
    else
      fail "import ${pkg}" "not importable inside container '$container'"
    fi
  done
}

check_docker() {
  # Docker daemon reachability is required for --method docker, optional for --method local.
  section "Docker daemon"
  if ! command -v docker >/dev/null 2>&1; then
    if [[ "$METHOD" == "docker" ]]; then
      fail "docker CLI" "not on PATH (required for --method docker)"
    else
      skip "docker CLI" "not on PATH (fine for --method local)"
    fi
    return
  fi
  if docker info >/dev/null 2>&1; then
    pass "docker daemon reachable"
  else
    fail "docker daemon" "\`docker info\` failed — daemon likely not running"
  fi
}

check_manager_health() {
  section "Manager /health endpoints"
  IFS=',' read -r -a ports <<< "$MANAGERS"
  for port in "${ports[@]}"; do
    port="${port// /}"
    [[ -z "$port" ]] && continue
    local url="http://localhost:${port}/health"
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 "$url" 2>/dev/null)"
    code="${code:-000}"
    if [[ "$code" == "200" ]]; then
      pass "GET $url → 200"
    else
      fail "GET $url" "HTTP $code (is that manager running?)"
    fi
  done
}

check_dashboard() {
  section "Dashboard (Squid / Lab Manager)"
  local url="http://localhost:${DASHBOARD_PORT}/health"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 "$url" 2>/dev/null)"
  code="${code:-000}"
  if [[ "$code" == "200" ]]; then
    pass "GET $url → 200"
  else
    fail "GET $url" "HTTP $code — dashboard not up on port ${DASHBOARD_PORT}"
  fi
}

check_dashboard_ui() {
  # Distinguishes "Lab Manager API is up" (already covered by check_dashboard's /health)
  # from "the Vue dashboard bundle is being served at /". The mount is conditional on
  # dashboard_files_path existing — see src/madsci_squid/madsci/squid/lab_server.py:48-55.
  section "Dashboard UI (root /)"
  local url="http://localhost:${DASHBOARD_PORT}/"
  local tmp
  tmp="$(mktemp)"
  local code ctype
  # -L follows any redirect the SPA might issue; -o writes body for inspection.
  read -r code ctype < <(
    curl -sS -L -o "$tmp" -w '%{http_code} %{content_type}\n' --max-time 3 "$url" 2>/dev/null || echo "000 -"
  )
  code="${code:-000}"
  ctype="${ctype:-unknown}"

  local is_html=0 is_json=0
  # Content-type may be "text/html; charset=utf-8" — match prefix only.
  case "$ctype" in
    text/html*)         is_html=1 ;;
    application/json*)  is_json=1 ;;
  esac
  # Fallback: sniff first bytes if content-type wasn't declared.
  if [[ $is_html -eq 0 && $is_json -eq 0 ]]; then
    if head -c 20 "$tmp" 2>/dev/null | grep -qiE '^\s*<!doctype html|^\s*<html'; then
      is_html=1
    elif head -c 20 "$tmp" 2>/dev/null | grep -qE '^\s*[{[]'; then
      is_json=1
    fi
  fi
  rm -f "$tmp"

  if [[ "$UI_MODE" == "with" ]]; then
    if [[ "$code" == "200" && $is_html -eq 1 ]]; then
      pass "GET $url → 200 HTML (Vue dashboard mounted)"
    elif [[ "$code" == "404" && $is_json -eq 1 ]]; then
      fail "GET $url" "HTTP 404 JSON — Lab Manager did not mount the UI. \
Set LAB_DASHBOARD_FILES_PATH to a built ui/dist and restart, \
or re-run with --no-ui if you meant to skip the dashboard."
    else
      fail "GET $url" "HTTP $code content-type=$ctype (expected HTML for a mounted dashboard)"
    fi
  else  # UI_MODE == "no"
    if [[ "$code" == "404" && $is_json -eq 1 ]]; then
      pass "GET $url → 404 JSON (API-only, as expected — no dashboard bundle mounted)"
    elif [[ "$code" == "200" && $is_html -eq 1 ]]; then
      # User said --no-ui but the UI is present. Not a failure per se, but worth surfacing.
      skip "GET $url → 200 HTML" "UI is mounted despite --no-ui; \
LAB_DASHBOARD_FILES_PATH is set to an existing dist/ — remove it or re-run with --with-ui"
    else
      fail "GET $url" "HTTP $code content-type=$ctype (expected 404 JSON for API-only)"
    fi
  fi
}

check_madsci_cli() {
  section "madsci CLI"
  if ! command -v madsci >/dev/null 2>&1; then
    skip "madsci on PATH" "install madsci-client to get the CLI"
    return
  fi

  # `madsci status` and `madsci doctor` exit non-zero when something is off;
  # capture their output so the user sees it verbatim.
  local status_out doctor_out
  status_out="$(madsci status 2>&1)" && pass "madsci status" || fail "madsci status" "see output below"
  printf "%s%s%s\n" "$DIM" "$status_out" "$RESET"

  doctor_out="$(madsci doctor 2>&1)" && pass "madsci doctor" || fail "madsci doctor" "see output below"
  printf "%s%s%s\n" "$DIM" "$doctor_out" "$RESET"
}

# ---------- run ----------
printf "MADSci install verification (method=%s" "$METHOD"
case "$UI_MODE" in
  with) printf ", expecting dashboard UI at /)" ;;
  no)   printf ", expecting API-only, no UI at /)" ;;
esac
printf "\n"

check_python
check_madsci_importable
check_docker
check_manager_health
check_dashboard
check_dashboard_ui
check_madsci_cli

# ---------- summary ----------
section "Summary"
printf "  %sPassed%s: %d    %sFailed%s: %d    %sSkipped%s: %d\n" \
  "$GREEN" "$RESET" "$PASS_COUNT" \
  "$RED" "$RESET" "$FAIL_COUNT" \
  "$YELLOW" "$RESET" "$SKIP_COUNT"

if (( FAIL_COUNT > 0 )); then
  printf "\n%sInstall verification FAILED.%s Re-run the AskUserQuestion prompts in SKILL.md Step 4 for the specific failure(s) above.\n" "$RED" "$RESET"
  exit 1
fi

printf "\n%s✅ Install verification PASSED.%s\n" "$GREEN" "$RESET"
exit 0
