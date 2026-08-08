#!/usr/bin/env bash
# Run a remote command over SSH.
# Usage:
#   ssh-run.sh <host> <remote-command>
#   SSH_REMOTE_HOST=user@host ssh-run.sh <remote-command>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

usage() {
  cat <<'EOF'
Usage:
  ssh-run.sh <host> <remote-command...>
  SSH_REMOTE_HOST=user@host ssh-run.sh <remote-command...>

Reads optional .ssh-remote.yml (host) and env SSH_REMOTE_HOST.
Password fallback: export SSHPASS='...' (requires sshpass; never commit).

Examples:
  ssh-run.sh lan-box 'hostname; whoami'
  SSH_REMOTE_HOST=user@192.168.x.x ssh-run.sh 'df -h'
  # host from defaults.yml / .ssh-remote.yml:
  ssh-run.sh 'hostname'
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ssh_remote_load_config

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

if [[ $# -ge 2 ]]; then
  SSH_REMOTE_HOST="$1"
  shift
fi

REMOTE_CMD="$*"
[[ -n "${REMOTE_CMD}" ]] || ssh_remote_die "remote command is required"
ssh_remote_require_host

ssh_remote_run "bash -lc $(printf '%q' "${REMOTE_CMD}")"
