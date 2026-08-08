#!/usr/bin/env bash
# Sync project then remote compose up -d --build and optional health check.
# Usage: deploy-compose.sh [--skip-sync] [--no-build]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

usage() {
  cat <<'EOF'
Usage:
  deploy-compose.sh [--skip-sync] [--no-build]

Steps:
  1. rsync-push.sh (unless --skip-sync)
  2. remote: cd remote_path && $SSH_REMOTE_COMPOSE up -d [--build]
  3. optional remote curl of SSH_REMOTE_HEALTH_URL

Env / .ssh-remote.yml: host, remote_path, compose, health_url, exclude, preserve
EOF
}

SKIP_SYNC=0
NO_BUILD=0
for arg in "$@"; do
  case "${arg}" in
    -h|--help) usage; exit 0 ;;
    --skip-sync) SKIP_SYNC=1 ;;
    --no-build) NO_BUILD=1 ;;
    *) ssh_remote_die "unknown arg: ${arg}" ;;
  esac
done

ssh_remote_load_config
ssh_remote_require_host
[[ -n "${SSH_REMOTE_PATH}" ]] || ssh_remote_die "SSH_REMOTE_PATH / remote_path is required"

if [[ "${SKIP_SYNC}" != "1" ]]; then
  "${SCRIPT_DIR}/rsync-push.sh"
fi

BUILD_FLAG="--build"
if [[ "${NO_BUILD}" == "1" ]]; then
  BUILD_FLAG=""
fi

COMPOSE_CMD="${SSH_REMOTE_COMPOSE} up -d ${BUILD_FLAG}"
# trim double spaces if no build
COMPOSE_CMD="$(echo "${COMPOSE_CMD}" | tr -s ' ')"

echo "ssh-remote: remote compose: ${COMPOSE_CMD}" >&2
ssh_remote_run "cd ${SSH_REMOTE_PATH} && ${COMPOSE_CMD}"

if [[ -n "${SSH_REMOTE_HEALTH_URL}" ]]; then
  echo "ssh-remote: health check ${SSH_REMOTE_HEALTH_URL}" >&2
  # Retry a few times while containers start
  ok=0
  for i in 1 2 3 4 5 6; do
    if ssh_remote_run "curl -sf --max-time 10 $(printf '%q' "${SSH_REMOTE_HEALTH_URL}")" >/dev/null 2>&1; then
      echo "ssh-remote: health OK" >&2
      ok=1
      break
    fi
    sleep 2
  done
  if [[ "${ok}" != "1" ]]; then
    echo "ssh-remote: warning: health check failed after retries" >&2
    echo "ssh-remote: tip: if compose failed with ContainerConfig, docker rm -f <container> then up again (see reference.md)" >&2
    exit 1
  fi
fi

echo "ssh-remote: deploy finished" >&2
