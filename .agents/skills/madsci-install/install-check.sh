#!/usr/bin/env bash
# install-check.sh — inspect a running MADSci stack and report pass/fail per check.
#
# Usage:
#   bash install-check.sh                  # infer goal from environment
#   bash install-check.sh --goal 1         # example lab (docker compose up at repo root)
#   bash install-check.sh --goal 2         # new lab created via `madsci init`
#   bash install-check.sh --goal 3         # per-package pip install
#   bash install-check.sh --goal 4         # dev setup (just init / devbox)
#   bash install-check.sh --managers 8001,8002,8003   # override which managers to check
#   bash install-check.sh --dashboard-port 8000       # override dashboard port
#   bash install-check.sh --no-color
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed
#   2 = usage error

set -u  # keep -e OFF: we want every check to run even if earlier ones fail.

# ---------- args ----------
GOAL=""
MANAGERS="8001,8002,8003,8004,8005,8006"
DASHBOARD_PORT="8000"
USE_COLOR=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --goal)            GOAL="${2:-}"; shift 2 ;;
    --managers)        MANAGERS="${2:-}"; shift 2 ;;
    --dashboard-port)  DASHBOARD_PORT="${2:-}"; shift 2 ;;
    --no-color)        USE_COLOR=0; shift ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "$GOAL" && ! "$GOAL" =~ ^[1-4]$ ]]; then
  echo "--goal must be 1, 2, 3, or 4 (got: $GOAL)" >&2; exit 2
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
    printf "         %s(no VIRTUAL_ENV set — that may be fine for Docker-only goals)%s\n" "$DIM" "$RESET"
  fi
}

check_madsci_importable() {
  section "MADSci Python packages"

  # Common core packages; extend when checking against a per-package install.
  local pkgs=(madsci.common madsci.client)
  case "$GOAL" in
    2|4) pkgs=(madsci.common madsci.client madsci.squid) ;;
    3)   ;; # goal 3 chooses its own set; caller can extend by re-running the script
  esac

  for pkg in "${pkgs[@]}"; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
      pass "import ${pkg}"
    else
      fail "import ${pkg}" "not installed in the active Python environment"
    fi
  done
}

check_docker() {
  # Only meaningful for goals 1, 2 (docker mode), 4 (integration tests).
  case "$GOAL" in
    3) return ;;
  esac
  section "Docker daemon"
  if ! command -v docker >/dev/null 2>&1; then
    skip "docker CLI" "not on PATH (fine if you're on local mode)"
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

check_example_lab_seed() {
  # Only run for goal 1 (example lab).
  [[ "$GOAL" != "1" ]] && return
  section "Example lab seed data"
  if ! command -v madsci >/dev/null 2>&1; then
    skip "madsci resource list" "CLI not on PATH"
    return
  fi
  if madsci resource list >/dev/null 2>&1; then
    pass "madsci resource list"
  else
    fail "madsci resource list" "resource manager unreachable or empty"
  fi
  if madsci location list >/dev/null 2>&1; then
    pass "madsci location list"
  else
    fail "madsci location list" "location manager unreachable or empty"
  fi
}

# ---------- run ----------
printf "MADSci install verification"
[[ -n "$GOAL" ]] && printf " (goal %s)" "$GOAL"
printf "\n"

check_python
check_madsci_importable
check_docker
check_manager_health
check_dashboard
check_madsci_cli
check_example_lab_seed

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
