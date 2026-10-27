# Go verify

From the module root, `.spec/docs/runbook.md` has a `## Verify` section with four layers. Copy the shape below. Keep a command only when this repository can run it.

## Verify

Run `.cursor/tools/verify-report.py --id <id>`. Read `.spec/tasks/<id>/verify-report.md` and nothing else from that run. Do not paste command output into the chat, the spec, or `verify.json`.

### Tests

required: yes

```
go test ./...
```

### Style

required: yes

```
test -z "$(gofmt -l .)"
go vet ./...
```

### Smoke

required: when-http

```
```

### E2E

required: no

```
```

`required` is `yes`, `no`, or `when-http`. `when-http` runs the Smoke commands only when `.spec/tasks/<id>/smoke.md` records checks. A single line `HTTP: unchanged` skips Smoke. `yes` always runs the commands. `no` skips the layer. An end-to-end suite this module already has goes under E2E with `required: yes`. Leave E2E at `required: no` when the module has none.

`gofmt -l` prints paths and still exits 0. The `test -z` form exits 1 when any file needs formatting.

When a command fails on the existing tree, record its name and the issue lines from the report in `.spec/docs/baseline.md`. Do not copy the command log. Remove that command from the required layer. The task rule is then: rerun the report and add no finding that the baseline does not already contain.

## Terminal tests

Put this next to the Verify section of `.spec/docs/runbook.md`.

A pipe does not follow an Esc byte. `\x1b` is Esc immediately, and a following `q` is not consumed as part of a sequence. `bytes.Reader` does follow that sequence. A script that must end the session sends `\x03` or `/q`. On a pipe, do not assume `q` will return.
