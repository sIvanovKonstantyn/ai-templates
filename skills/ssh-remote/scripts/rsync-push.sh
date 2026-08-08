#!/usr/bin/env bash
# Push local directory to remote path via rsync.
# Usage: rsync-push.sh [local_dir] [remote_path]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

usage() {
  cat <<'EOF'
Usage:
  rsync-push.sh [local_dir] [remote_path]

Config (env overrides .ssh-remote.yml):
  SSH_REMOTE_HOST, SSH_REMOTE_PATH, SSH_REMOTE_LOCAL, SSH_REMOTE_EXCLUDE
  SSH_REMOTE_PRESERVE  — newline-separated paths to exclude (also from yaml preserve:)
  SSH_REMOTE_RSYNC_DELETE=1  — pass --delete (off by default)

Templates:
  ~/.cursor/skills/ssh-remote/templates/deploy.rsync-exclude
  (or templates/ next to this skill when installed in the workspace)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

command -v rsync >/dev/null 2>&1 || ssh_remote_die "rsync not found on laptop (ask before installing)"

ssh_remote_load_config

LOCAL="${1:-${SSH_REMOTE_LOCAL}}"
REMOTE_PATH="${2:-${SSH_REMOTE_PATH}}"

ssh_remote_require_host
[[ -n "${REMOTE_PATH}" ]] || ssh_remote_die "SSH_REMOTE_PATH (or remote_path / arg) is required"
[[ -d "${LOCAL}" ]] || ssh_remote_die "local directory not found: ${LOCAL}"

# Normalize local to end with /
LOCAL="${LOCAL%/}/"

EXCLUDE_ARGS=()
if [[ -n "${SSH_REMOTE_EXCLUDE}" ]]; then
  [[ -f "${SSH_REMOTE_EXCLUDE}" ]] || ssh_remote_die "exclude file not found: ${SSH_REMOTE_EXCLUDE}"
  EXCLUDE_ARGS+=(--exclude-from="${SSH_REMOTE_EXCLUDE}")
else
  DEFAULT_EXCL="${_SSH_REMOTE_SKILL_DIR}/templates/deploy.rsync-exclude"
  if [[ -f "${DEFAULT_EXCL}" ]]; then
    EXCLUDE_ARGS+=(--exclude-from="${DEFAULT_EXCL}")
  fi
fi

# preserve: always exclude from push so remote copies win
if [[ -n "${SSH_REMOTE_PRESERVE}" ]]; then
  while IFS= read -r p; do
    [[ -z "${p}" ]] && continue
    EXCLUDE_ARGS+=(--exclude="${p}")
  done <<< "${SSH_REMOTE_PRESERVE}"
fi

DELETE_ARGS=()
if [[ "${SSH_REMOTE_RSYNC_DELETE:-0}" == "1" ]]; then
  DELETE_ARGS+=(--delete)
fi

RSH="$(ssh_remote_rsync_rsh)"

# Ensure remote directory exists
ssh_remote_run "mkdir -p ${REMOTE_PATH}"

echo "ssh-remote: rsync ${LOCAL} -> ${SSH_REMOTE_HOST}:${REMOTE_PATH}" >&2
rsync -avz \
  "${DELETE_ARGS[@]}" \
  "${EXCLUDE_ARGS[@]}" \
  -e "${RSH}" \
  "${LOCAL}" \
  "${SSH_REMOTE_HOST}:${REMOTE_PATH}/"
