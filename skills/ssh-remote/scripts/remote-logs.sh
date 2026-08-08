#!/usr/bin/env bash
# Tail remote docker / compose logs.
# Usage: remote-logs.sh [service_or_container] [tail_lines]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

usage() {
  cat <<'EOF'
Usage:
  remote-logs.sh [service_or_container] [tail_lines]

Uses SSH_REMOTE_COMPOSE when a compose project path is set:
  cd $SSH_REMOTE_PATH && $SSH_REMOTE_COMPOSE logs --tail=N [service]

If no service and no path, falls back to: docker logs --tail=N (needs container name).

Env: SSH_REMOTE_HOST, SSH_REMOTE_PATH, SSH_REMOTE_COMPOSE, SSH_REMOTE_SERVICE
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ssh_remote_load_config
ssh_remote_require_host

SERVICE="${1:-${SSH_REMOTE_SERVICE:-}}"
TAIL_LINES="${2:-100}"

# Derive docker binary prefix from compose setting (sudo docker-compose → sudo docker)
DOCKER_BIN="docker"
case "${SSH_REMOTE_COMPOSE}" in
  sudo\ *) DOCKER_BIN="sudo docker" ;;
esac

if [[ -n "${SSH_REMOTE_PATH}" ]]; then
  if [[ -n "${SERVICE}" ]]; then
    REMOTE="cd ${SSH_REMOTE_PATH} && ${SSH_REMOTE_COMPOSE} logs --tail=${TAIL_LINES} $(printf '%q' "${SERVICE}")"
  else
    REMOTE="cd ${SSH_REMOTE_PATH} && ${SSH_REMOTE_COMPOSE} logs --tail=${TAIL_LINES}"
  fi
else
  [[ -n "${SERVICE}" ]] || ssh_remote_die "service/container name required when SSH_REMOTE_PATH unset"
  REMOTE="${DOCKER_BIN} logs --tail=${TAIL_LINES} $(printf '%q' "${SERVICE}")"
fi

ssh_remote_run "${REMOTE}"
