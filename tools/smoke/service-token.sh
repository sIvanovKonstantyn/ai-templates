#!/bin/sh
# Prints a short-lived access token for smoke calls, and nothing else.
# Runs the command in SMOKE_TOKEN_COMMAND (for example a team token generator); its stdout is the token.
# Extra arguments are passed through. Set SMOKE_TOKEN instead to skip this script.
# Never write the token into a task file. Use it only in the Authorization header.
# Usage: SMOKE_TOKEN=$(<tools>/smoke/service-token.sh)
set -eu
[ -n "${SMOKE_TOKEN_COMMAND:-}" ] || { echo "service-token: set SMOKE_TOKEN_COMMAND or SMOKE_TOKEN" >&2; exit 1; }
token=$(sh -c "$SMOKE_TOKEN_COMMAND \"\$@\"" service-token "$@" 2>/dev/null) || { echo "service-token: token command failed" >&2; exit 1; }
[ -n "$token" ] || { echo "service-token: token command printed nothing" >&2; exit 1; }
printf '%s\n' "$token"
