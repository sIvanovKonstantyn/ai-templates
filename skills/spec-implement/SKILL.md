---
name: spec-implement
description: Implement a user-written spec under .spec/tasks/<id>/spec.md, all subtasks or one. Use only for /implement or when the user names a task id or spec to implement. Not for review feedback or other chat tasks.
---
# Implement a spec
Read and follow `implement.md` in this directory, or `../../pipeline/implement.md` in the kit, before editing product code.
- `/implement <id>`: all subtasks of `.spec/tasks/<id>/spec.md`, in order.
- `/implement <id> N`: subtask N only.
- `spec-template.md` in this directory, or `../../pipeline/spec-template.md` in the kit, is the shape of a spec. The user writes the spec. Do not write it unless the user asks.
- Review feedback and other chat tasks do not use this skill.
The id is the folder name under `.spec/tasks/`. Verification comes from the subtask's Verification section in the spec. The tools below are available when a Verification section names them.
## When smoke runs
Smoke is long-running and can use shared resources (database, cache, event stream). Run it only when a subtask's Verification section names it. Start the application once, run every HTTP and Event check of the task, clean up the smoke data, and stop the application. Never run smoke inside a subtask, and never write a subtask for smoke work. Rerun it only when a later edit changes code the checks cover. The runbook `## Smoke` section names how to start the application and which test data to use.
## HTTP smoke checks
Record each HTTP check with `.cursor/tools/smoke-http.py`. It sends one request, prints one `PASS`/`FAIL` line, and appends the request, response, verification, and result to `smoke.md`:
```shell
.cursor/tools/smoke-http.py --id <id> [--auth] --name "<check>" --method POST --path /api/... \
    --json '{...}' --expect-status 201 --expect-body <text>
```
- `--json` sends a JSON body. `--multipart-json` sends it as one multipart part (`--part`, default `request`). `--base` sets the base URL (default `http://localhost:8080`).
- `--auth` sends `Authorization: Bearer <token>` from `SMOKE_TOKEN`, or from `.cursor/tools/smoke/service-token.sh`, which runs `SMOKE_TOKEN_COMMAND`. The token is never recorded: `smoke.md` shows `Bearer <redacted>`.
- Writes to shared data use throwaway test data that the runbook names. Delete what the smoke test created. The last check confirms nothing is left.
## Event smoke checks
When the task changes a published event (payload fields, event version, stream, or when the event is sent), the smoke test also checks the event in the Redis stream, even when HTTP is unchanged.
1. Write `Events: changed` in `smoke.md`. When HTTP is unchanged, the file starts with `HTTP: unchanged` and `Events: changed`.
2. Fill the connection in `~/.config/spec-kit/smoke-redis.env` (mode 600), or the file named by `SPEC_SMOKE_REDIS_ENV_FILE`, from `.cursor/tools/smoke/smoke-redis.env.example`. Set `SMOKE_EVENT_STREAM` to the stream the runbook names. Never put the password in a task file.
3. Run `.cursor/tools/smoke-events.py ping`. Exit 2 means a connection or configuration problem, not a product failure. Report it and do not mark the task done.
4. Start the application, then run `.cursor/tools/smoke-events.py mark --id <id>` before each call that should publish an event.
5. Call the route, then run `.cursor/tools/smoke-events.py expect --id <id> --name "<check>" --where body.<field>=<value> ...`. Add `--where` for each new or changed field, `--absent` for fields that must be omitted, and `--count 1` when the event must be sent once. Paths start with the stream field (often `body`); `[*]` matches any list element.
6. Read only the one-line `PASS`/`FAIL` output. `expect` appends the Event check block to `smoke.md`. A `FAIL` is fixed in product code, then `mark`, the call, and `expect` run again.
Filter on the test's own data (application, tenant, or id). A shared stream also carries events from other services and instances.
To try the tool without a shared Redis, run `.cursor/tools/smoke/selftest-events.sh`. It starts the local Redis from `.cursor/tools/smoke/docker-compose.redis.yml`, checks the tool's pass and fail paths, and stops the container.
