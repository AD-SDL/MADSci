#!/usr/bin/env bash
# install-check.sh — inspect a running MADSci Docker stack and report pass/fail per check.
#
# Certifies only that the stack is up and answering correctly. It does NOT check
# what the lab contains (resources / nodes / locations) or which kind of lab it is.
#
# Usage:
#   bash install-check.sh                                 # stack running under Docker Compose
#   bash install-check.sh --with-ui                       # explicitly expect the dashboard UI at /
#   bash install-check.sh --no-ui                         # explicitly expect API-only at /
#   bash install-check.sh --managers 8001,8002,8003       # override which manager ports to check
#   bash install-check.sh --dashboard-port 8000           # override dashboard port
#   bash install-check.sh --install-dir <path>            # probe the madsci CLI venv at <path>/.venv
#   bash install-check.sh --no-color
#
# --with-ui is the default (compose deployments typically use the madsci_dashboard
# image, which bakes in the built UI); pass --no-ui for a slim base-image compose.
#
# --install-dir points at the install directory whose .venv/ holds `madsci-client`,
# so the CLI/import checks probe that venv rather than system python3/madsci —
# both of which may be absent on a Docker-only install.
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed
#   2 = usage error

set -u  # keep -e OFF: we want every check to run even if earlier ones fail.

# ---------- args ----------
MANAGERS="8001,8002,8003,8004,8005,8006"
DASHBOARD_PORT="8000"
USE_COLOR=1
UI_MODE="with"      # "with" or "no" (default: expect UI mounted)
INSTALL_DIR=""      # path to the stack install dir (holds .venv/ with madsci-client)

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
    --managers)        need_value "$1" "$#"; MANAGERS="$2"; shift 2 ;;
    --dashboard-port)  need_value "$1" "$#"; DASHBOARD_PORT="$2"; shift 2 ;;
    --install-dir)     need_value "$1" "$#"; INSTALL_DIR="$2"; shift 2 ;;
    --with-ui)         UI_MODE="with"; shift ;;
    --no-ui)           UI_MODE="no"; shift ;;
    --no-color)        USE_COLOR=0; shift ;;
    -h|--help)
      sed -n '2,26p' "$0"; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Resolve the venv python & madsci binary once up-front. When --install-dir is
# passed, prefer the venv's interpreter (which is where the host-side madsci
# packages were installed). Otherwise fall back to system python3/madsci.
VENV_PY=""
VENV_MADSCI=""
if [[ -n "$INSTALL_DIR" ]]; then
  if [[ -x "$INSTALL_DIR/.venv/bin/python" ]]; then
    VENV_PY="$INSTALL_DIR/.venv/bin/python"
  fi
  if [[ -x "$INSTALL_DIR/.venv/bin/madsci" ]]; then
    VENV_MADSCI="$INSTALL_DIR/.venv/bin/madsci"
  fi
fi
HOST_PY="${VENV_PY:-$(command -v python3 || true)}"
HOST_MADSCI="${VENV_MADSCI:-$(command -v madsci || true)}"

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

# Returns 0 if the given JSON body reports {"healthy": true}, 1 otherwise.
# Uses jq when available; falls back to python3 so the script works on bare hosts.
is_healthy_json() {
  local body="$1"
  if command -v jq >/dev/null 2>&1; then
    # Strict: boolean true, not the string "true".
    [[ "$(jq -r 'if .healthy == true then "yes" else "no" end' <<<"$body" 2>/dev/null)" == "yes" ]]
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$body" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
sys.exit(0 if d.get("healthy") is True else 1)
' 2>/dev/null
  else
    # Last resort — grep. Accepts "healthy": true (and "healthy":true).
    grep -qE '"healthy"[[:space:]]*:[[:space:]]*true' <<<"$body"
  fi
}

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
    printf "         %s(no VIRTUAL_ENV set — expected for a Docker-only install)%s\n" "$DIM" "$RESET"
  fi
}

check_madsci_importable() {
  # MADSci manager code lives inside containers. The host-side `madsci-client`
  # was installed via `uv pip install` into $INSTALL_DIR/.venv/ — probe that
  # venv (if --install-dir given) and a running manager container
  # (authoritative).
  section "MADSci Python packages"

  local pkgs=(madsci.common madsci.client madsci.squid)

  local probe_label="host"
  if [[ -n "$VENV_PY" ]]; then
    probe_label="venv at $INSTALL_DIR/.venv"
  fi

  # Host side — informational; don't fail the whole run on it.
  local host_has_madsci=0
  if [[ -n "$HOST_PY" ]] && "$HOST_PY" -c "import madsci.common" 2>/dev/null; then
    host_has_madsci=1
  fi
  if [[ $host_has_madsci -eq 1 ]]; then
    for pkg in "${pkgs[@]}"; do
      if "$HOST_PY" -c "import ${pkg}" 2>/dev/null; then
        pass "import ${pkg} (${probe_label})"
      else
        skip "import ${pkg} (${probe_label})" "not in ${probe_label} — checking containers"
      fi
    done
  elif [[ -n "$VENV_PY" ]]; then
    skip "import madsci.* (${probe_label})" "venv exists but madsci.common not importable; re-run 'uv pip install madsci-client' from $INSTALL_DIR"
  fi

  if ! command -v docker >/dev/null 2>&1; then
    if [[ $host_has_madsci -eq 0 ]]; then
      fail "MADSci packages" "not importable on host and docker CLI not on PATH — cannot verify"
    fi
    return
  fi

  # Authoritative: at least one manager container must import madsci.* —
  # proves the running Docker stack is MADSci, not just something on 8001.
  # `docker compose exec` addresses a SERVICE, not a container. Matching the NAME
  # column only lines up when the compose pins `container_name:` (the example lab
  # does); anywhere Docker auto-names `<project>-<service>-N` the grep matches a
  # container name that `exec` then rejects, and the failure gets misreported as
  # a broken import. Enumerate services directly instead.
  local running_services service=""
  running_services="$(docker compose ps --services --status running 2>/dev/null)"
  for candidate in event_manager lab_manager experiment_manager resource_manager \
                   data_manager workcell_manager location_manager; do
    if grep -qx "$candidate" <<<"$running_services"; then
      service="$candidate"
      break
    fi
  done
  if [[ -z "$service" ]]; then
    local detail="no running MADSci manager service found via 'docker compose ps --services --status running'"
    if [[ -n "$running_services" ]]; then
      detail="$detail (running services: $(tr '\n' ' ' <<<"$running_services"))"
    fi
    if [[ $host_has_madsci -eq 0 ]]; then
      fail "container MADSci import" "$detail"
    else
      skip "container MADSci import" "$detail; host imports covered above"
    fi
    return
  fi
  for pkg in madsci.common madsci.client; do
    if docker compose exec -T "$service" python3 -c "import ${pkg}" >/dev/null 2>&1; then
      pass "import ${pkg} (in service '$service')"
    else
      fail "import ${pkg}" "not importable inside service '$service'"
    fi
  done
}

check_docker() {
  section "Docker daemon"
  if ! command -v docker >/dev/null 2>&1; then
    fail "docker CLI" "not on PATH (required for Docker install)"
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
    local tmp body code
    tmp="$(mktemp)"
    code="$(curl -sS -o "$tmp" -w '%{http_code}' --max-time 3 "$url" 2>/dev/null)"
    code="${code:-000}"
    body="$(cat "$tmp" 2>/dev/null)"
    rm -f "$tmp"
    if [[ "$code" != "200" ]]; then
      fail "GET $url" "HTTP $code (is that manager running?)"
      continue
    fi
    if is_healthy_json "$body"; then
      pass "GET $url → 200 {\"healthy\":true}"
    else
      fail "GET $url" "HTTP 200 but body does not report healthy=true: ${body:0:200}"
    fi
  done
}

check_dashboard() {
  section "Dashboard (Squid / Lab Manager)"
  local url="http://localhost:${DASHBOARD_PORT}/health"
  local tmp body code
  tmp="$(mktemp)"
  code="$(curl -sS -o "$tmp" -w '%{http_code}' --max-time 3 "$url" 2>/dev/null)"
  code="${code:-000}"
  body="$(cat "$tmp" 2>/dev/null)"
  rm -f "$tmp"
  if [[ "$code" != "200" ]]; then
    fail "GET $url" "HTTP $code — dashboard not up on port ${DASHBOARD_PORT}"
    return
  fi
  if is_healthy_json "$body"; then
    pass "GET $url → 200 {\"healthy\":true}"
  else
    fail "GET $url" "HTTP 200 but body does not report healthy=true: ${body:0:200}"
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
  read -r code ctype < <(
    curl -sS -L -o "$tmp" -w '%{http_code} %{content_type}\n' --max-time 3 "$url" 2>/dev/null || echo "000 -"
  )
  code="${code:-000}"
  ctype="${ctype:-unknown}"

  local is_html=0 is_json=0
  case "$ctype" in
    text/html*)         is_html=1 ;;
    application/json*)  is_json=1 ;;
  esac
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
Confirm your compose uses ghcr.io/ad-sdl/madsci_dashboard:*, \
or re-run with --no-ui if you meant to skip the dashboard."
    else
      fail "GET $url" "HTTP $code content-type=$ctype (expected HTML for a mounted dashboard)"
    fi
  else  # UI_MODE == "no"
    if [[ "$code" == "404" && $is_json -eq 1 ]]; then
      pass "GET $url → 404 JSON (API-only, as expected — no dashboard bundle mounted)"
    elif [[ "$code" == "200" && $is_html -eq 1 ]]; then
      skip "GET $url → 200 HTML" "UI is mounted despite --no-ui; re-run with --with-ui or switch to the slim madsci image"
    else
      fail "GET $url" "HTTP $code content-type=$ctype (expected 404 JSON for API-only)"
    fi
  fi
}

check_madsci_cli() {
  section "madsci CLI"
  if [[ -z "$HOST_MADSCI" ]]; then
    if [[ -n "$INSTALL_DIR" ]]; then
      skip "madsci CLI" "not found at $INSTALL_DIR/.venv/bin/madsci — re-run 'uv venv' + 'uv pip install madsci-client' in $INSTALL_DIR"
    else
      skip "madsci CLI" "not on PATH; pass --install-dir to probe the venv the install created"
    fi
    return
  fi
  printf "         %sCLI: %s%s\n" "$DIM" "$HOST_MADSCI" "$RESET"

  # `madsci status` and `madsci doctor` exit 0 whether a stack is up or not — the
  # real pass/fail lives on the /health checks above. Keep these as INFORMATIONAL
  # prints so the user sees the output, and only fail on the direct health curls.
  printf "         %s(informational — real pass/fail is on /health above)%s\n" "$DIM" "$RESET"

  local status_out doctor_out
  status_out="$("$HOST_MADSCI" status 2>&1 || true)"
  printf "%s--- madsci status ---\n%s%s\n" "$DIM" "$status_out" "$RESET"

  doctor_out="$("$HOST_MADSCI" doctor 2>&1 || true)"
  printf "%s--- madsci doctor ---\n%s%s\n" "$DIM" "$doctor_out" "$RESET"
}

# ---------- run ----------
printf "MADSci install verification ("
case "$UI_MODE" in
  with) printf "expecting dashboard UI at /)" ;;
  no)   printf "expecting API-only, no UI at /)" ;;
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
  printf "\n%sInstall verification FAILED.%s Re-run the AskUserQuestion prompts in SKILL.md Step 6 for the specific failure(s) above.\n" "$RED" "$RESET"
  exit 1
fi

printf "\n%s✅ Install verification PASSED.%s\n" "$GREEN" "$RESET"
exit 0
