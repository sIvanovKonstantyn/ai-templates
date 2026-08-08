#!/usr/bin/env bash
# Shared helpers for ssh-remote scripts. Source only — do not execute.
# shellcheck shell=bash
# Note: do not set -euo here; callers set their own options.

_SSH_REMOTE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_SSH_REMOTE_SKILL_DIR="$(cd "${_SSH_REMOTE_LIB_DIR}/.." && pwd)"

ssh_remote_die() {
  echo "ssh-remote: error: $*" >&2
  exit 1
}

ssh_remote_defaults_path() {
  # Host defaults stay in the user home (not in the skill / git tree).
  local home_defaults="${HOME}/.cursor/ssh-remote/defaults.yml"
  printf '%s\n' "${SSH_REMOTE_DEFAULTS_FILE:-${home_defaults}}"
}

ssh_remote_find_config() {
  if [[ -n "${SSH_REMOTE_CONFIG:-}" && -f "${SSH_REMOTE_CONFIG}" ]]; then
    echo "${SSH_REMOTE_CONFIG}"
    return 0
  fi
  local dir="$PWD"
  while true; do
    if [[ -f "${dir}/.ssh-remote.yml" ]]; then
      echo "${dir}/.ssh-remote.yml"
      return 0
    fi
    if [[ "${dir}" == "/" ]]; then
      break
    fi
    dir="$(dirname "${dir}")"
  done
  return 1
}

# Parse simple YAML (flat keys + preserve list). Args: path [VAR_PREFIX]
# Default prefix FILE_ → FILE_HOST, etc. Use DEFAULT_ for personal defaults.
ssh_remote_parse_yaml() {
  local path="$1"
  local prefix="${2:-FILE_}"
  PREFIX="${prefix}" python3 - "$path" <<'PY'
import os, re, sys
path = sys.argv[1]
prefix = os.environ.get("PREFIX", "FILE_")
data = {}
preserve = []
in_preserve = False
with open(path, encoding="utf-8") as f:
    for raw in f:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^preserve:\s*$", line):
            in_preserve = True
            continue
        if in_preserve:
            m = re.match(r"^\s+-\s+(.+)$", line)
            if m:
                preserve.append(m.group(1).strip().strip("\"'"))
                continue
            in_preserve = False
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "preserve":
            continue
        if val.startswith(("'", '"')) and val.endswith(("'", '"')) and len(val) >= 2:
            val = val[1:-1]
        data[key] = val
data["preserve"] = preserve

def sh_escape(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

mapping = {
    "host": "HOST",
    "remote_path": "REMOTE_PATH",
    "local": "LOCAL",
    "exclude_file": "EXCLUDE",
    "compose": "COMPOSE",
    "health_url": "HEALTH_URL",
    "service": "SERVICE",
}
for k, suffix in mapping.items():
    if k in data and data[k] != "":
        print(f"{prefix}{suffix}={sh_escape(data[k])}")
if preserve:
    print(f"{prefix}PRESERVE={sh_escape(chr(10).join(preserve))}")
PY
}

# Precedence (high → low):
#   1. Env / CLI for this call (SSH_REMOTE_*)
#   2. Project .ssh-remote.yml
#   3. Personal defaults.yml (from onboard / set-defaults.sh)
ssh_remote_load_config() {
  DEFAULT_HOST=""
  DEFAULT_REMOTE_PATH=""
  DEFAULT_LOCAL=""
  DEFAULT_EXCLUDE=""
  DEFAULT_COMPOSE=""
  DEFAULT_HEALTH_URL=""
  DEFAULT_SERVICE=""
  DEFAULT_PRESERVE=""

  FILE_HOST=""
  FILE_REMOTE_PATH=""
  FILE_LOCAL=""
  FILE_EXCLUDE=""
  FILE_COMPOSE=""
  FILE_HEALTH_URL=""
  FILE_SERVICE=""
  FILE_PRESERVE=""

  if [[ -f "$(ssh_remote_defaults_path)" ]]; then
    # shellcheck disable=SC1090
    eval "$(ssh_remote_parse_yaml "$(ssh_remote_defaults_path)" "DEFAULT_")"
  fi

  local cfg=""
  if cfg="$(ssh_remote_find_config 2>/dev/null)"; then
    # shellcheck disable=SC1090
    eval "$(ssh_remote_parse_yaml "${cfg}" "FILE_")"
  fi

  SSH_REMOTE_HOST="${SSH_REMOTE_HOST:-${FILE_HOST:-${DEFAULT_HOST:-}}}"
  SSH_REMOTE_PATH="${SSH_REMOTE_PATH:-${FILE_REMOTE_PATH:-${DEFAULT_REMOTE_PATH:-}}}"
  SSH_REMOTE_LOCAL="${SSH_REMOTE_LOCAL:-${FILE_LOCAL:-${DEFAULT_LOCAL:-.}}}"
  SSH_REMOTE_EXCLUDE="${SSH_REMOTE_EXCLUDE:-${FILE_EXCLUDE:-${DEFAULT_EXCLUDE:-}}}"
  SSH_REMOTE_COMPOSE="${SSH_REMOTE_COMPOSE:-${FILE_COMPOSE:-${DEFAULT_COMPOSE:-docker compose}}}"
  SSH_REMOTE_HEALTH_URL="${SSH_REMOTE_HEALTH_URL:-${FILE_HEALTH_URL:-${DEFAULT_HEALTH_URL:-}}}"
  SSH_REMOTE_SERVICE="${SSH_REMOTE_SERVICE:-${FILE_SERVICE:-${DEFAULT_SERVICE:-}}}"
  SSH_REMOTE_PRESERVE="${SSH_REMOTE_PRESERVE:-${FILE_PRESERVE:-${DEFAULT_PRESERVE:-}}}"
}

ssh_remote_require_host() {
  if [[ -z "${SSH_REMOTE_HOST:-}" ]]; then
    ssh_remote_die "no host configured. Run onboard / set-defaults.sh, set host in .ssh-remote.yml, or pass SSH_REMOTE_HOST / ssh-run.sh <host> ..."
  fi
}

ssh_remote_ssh_opts() {
  local opts=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
  if [[ -z "${SSHPASS:-}" ]]; then
    opts+=(-o BatchMode=yes)
  fi
  printf '%s\n' "${opts[@]}"
}

# Build ssh / sshpass invocation as array SSH_REMOTE_SSH_CMD
ssh_remote_build_ssh_cmd() {
  ssh_remote_require_host
  local -a opts=()
  while IFS= read -r line; do
    [[ -n "${line}" ]] && opts+=("${line}")
  done < <(ssh_remote_ssh_opts)

  if [[ -n "${SSHPASS:-}" ]]; then
    command -v sshpass >/dev/null 2>&1 || ssh_remote_die "SSHPASS is set but sshpass is not installed (ask before installing)"
    SSH_REMOTE_SSH_CMD=(sshpass -e ssh "${opts[@]}" "${SSH_REMOTE_HOST}")
  else
    SSH_REMOTE_SSH_CMD=(ssh "${opts[@]}" "${SSH_REMOTE_HOST}")
  fi
}

ssh_remote_run() {
  ssh_remote_build_ssh_cmd
  # -n: no stdin (safe for automation); caller may override by setting SSH_REMOTE_SSH_STDIN=1
  if [[ "${SSH_REMOTE_SSH_STDIN:-0}" == "1" ]]; then
    "${SSH_REMOTE_SSH_CMD[@]}" "$@"
  else
    "${SSH_REMOTE_SSH_CMD[@]}" -n "$@"
  fi
}

ssh_remote_rsync_rsh() {
  local -a opts=()
  while IFS= read -r line; do
    [[ -n "${line}" ]] && opts+=("${line}")
  done < <(ssh_remote_ssh_opts)

  if [[ -n "${SSHPASS:-}" ]]; then
    command -v sshpass >/dev/null 2>&1 || ssh_remote_die "SSHPASS is set but sshpass is not installed"
    printf 'sshpass -e ssh'
    for o in "${opts[@]}"; do
      printf ' %q' "${o}"
    done
  else
    printf 'ssh'
    for o in "${opts[@]}"; do
      printf ' %q' "${o}"
    done
  fi
}

ssh_remote_expand_remote_path() {
  local path="$1"
  if [[ "${path}" == ~* ]]; then
    ssh_remote_run "echo ${path}"
  else
    printf '%s\n' "${path}"
  fi
}
