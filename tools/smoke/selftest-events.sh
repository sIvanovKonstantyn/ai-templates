#!/bin/sh
# Self-test for smoke-events.py against the local Redis in docker-compose.redis.yml.
# Publishes records whose stream field `body` holds the event JSON, as many producers write them
# and checks pass, fail, absent-field, exact-count, and auth-error paths. Prints one line per check.
set -u
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../../.." && pwd)
tools=${here%/smoke}
tools=${tools#"$root"/}
cd "$root"
compose="docker compose -f $tools/smoke/docker-compose.redis.yml"
tool="$tools/smoke-events.py"
id="zz-smoke-events-selftest"
stream="spec-smoke-selftest"
failures=0

export SPEC_SMOKE_REDIS_ENV_FILE="$root/$tools/smoke/smoke-redis.local.env"
chmod 600 "$SPEC_SMOKE_REDIS_ENV_FILE"

cleanup() {
    rm -rf ".spec/tasks/$id" "target/spec-smoke/$id"
    [ "${KEEP_REDIS:-0}" = "1" ] || $compose down -v >/dev/null 2>&1
}
trap cleanup EXIT

check() {
    expected=$1; label=$2; shift 2
    output=$("$@" 2>&1); code=$?
    if [ "$code" -eq "$expected" ]; then
        printf 'ok   %s\n' "$label"
    else
        printf 'FAIL %s: exit %s, expected %s: %s\n' "$label" "$code" "$expected" "$output"
        failures=$((failures + 1))
    fi
}

xadd() {
    $compose exec -T redis redis-cli -a local-smoke-password --no-auth-warning \
        XADD "$stream" '*' body "$1" topic "$stream" version 1.1 >/dev/null
}

$compose up -d --wait >/dev/null 2>&1 || { echo "FAIL cannot start local Redis"; exit 2; }
$compose exec -T redis redis-cli -a local-smoke-password --no-auth-warning DEL "$stream" >/dev/null

xadd '{"application":"app","profile":"dev","changeType":"CREATE_CONFIG","changedBy":"before-mark"}'
check 0 "ping" python3 "$tool" ping
check 0 "mark" python3 "$tool" mark --id "$id"

xadd '{"application":"app","profile":"dev","changeType":"UPDATE_CONFIG","changedBy":"u","changedKeys":[{"key":"a.b"},{"key":"c","tenantId":"t1"}]}'
xadd '{"application":"app","profile":"dev","changeType":"ROLLBACK_CONFIG","changedBy":"u"}'

check 0 "event with changedKeys" python3 "$tool" expect --id "$id" --name "update has changedKeys" \
    --where body.changeType=UPDATE_CONFIG --where 'body.changedKeys[*].key=a.b' \
    --where 'body.changedKeys[1].tenantId=t1' --count 1 --timeout 5
check 0 "rollback omits changedKeys" python3 "$tool" expect --id "$id" --name "rollback omits changedKeys" \
    --where body.changeType=ROLLBACK_CONFIG --absent body.changedKeys --timeout 3
check 1 "record before mark is ignored" python3 "$tool" expect --id "$id" --name "before mark" \
    --where body.changedBy=before-mark --timeout 1
check 1 "absent field present fails" python3 "$tool" expect --id "$id" --name "absent violated" \
    --where body.changeType=UPDATE_CONFIG --absent body.changedKeys --timeout 1
check 1 "exact count mismatch fails" python3 "$tool" expect --id "$id" --name "count mismatch" \
    --where body.application=app --count 1 --timeout 1
check 2 "wrong password is a tool error" env SMOKE_REDIS_PASSWORD=wrong python3 "$tool" ping

smoke=".spec/tasks/$id/smoke.md"
passes=$(grep -c '^- Result: pass' "$smoke" 2>/dev/null || echo 0)
fails=$(grep -c '^- Result: fail' "$smoke" 2>/dev/null || echo 0)
if [ "$passes" -eq 2 ] && [ "$fails" -eq 3 ]; then
    printf 'ok   smoke.md records 2 pass and 3 fail blocks\n'
else
    printf 'FAIL smoke.md records %s pass and %s fail blocks\n' "$passes" "$fails"
    failures=$((failures + 1))
fi
if grep -q 'local-smoke-password' "$smoke"; then
    printf 'FAIL smoke.md contains the password\n'
    failures=$((failures + 1))
fi

[ "$failures" -eq 0 ] && echo "selftest: pass" || echo "selftest: $failures failure(s)"
[ "$failures" -eq 0 ]
