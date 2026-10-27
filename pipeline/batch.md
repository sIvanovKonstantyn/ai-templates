You are implementing several tasks in order. The workspace root is your current working directory.
The person sent `/batch`, or a list of briefs. Follow this file. Do not switch to a looser path because there is more than one id.

`/implement <id>` is for one id and runs the full Verify suite for that id. This procedure does not replace those steps with a bulk edit.

For each id, in the order given, finish steps 1–4 before the next id:

1. Read `.spec/tasks/<id>/brief.md`. The `## Breaks` section must name the status text and tests, the keys the change redefines, and the filesystem side effects. `none` is an answer. Copy that section into `spec.md`.
2. Write `spec.md` and `subtask-N.md` before any product edit for this id. Do not edit a task spec that already has `verify.json` with `"exit": 0`. Behavior changes (keys, the command list, what delete does) go in `.spec/docs/critical.md` and in this spec. Component docs link to `critical.md` and do not repeat that paragraph.
3. Set one subtask to `in-progress` and write that id into `.spec/tasks/active`. No other task folder may have an in-progress subtask.
4. Change the code. Run `.cursor/tools/verify-report.py --id <id>` after the packages this id touches are covered by the Tests layer. Read only `.spec/tasks/<id>/verify-report.md`. Do not run the layer commands yourself and do not paste their output into the chat, the spec, or `verify.json`. Fix product code until the report has no issues. Update `critical.md` when behavior changes. Set that subtask to `done` only after that report. Clear `.spec/tasks/active` before the next id.

After the last id, and before the one Verify run:

5. When an id changed an HTTP route, method, request field, response body, or status, start the application the way the `## Smoke` section of `.spec/docs/runbook.md` says. Run the changed routes once. Write `.spec/tasks/<id>/smoke.md` for each such id. Each check has the three parts below. A failed check is fixed in product code and run again. Do not edit reviewer rules, the PMD ruleset, ArchUnit tests, or `.spec/docs/baseline.md`. Do not write `verify.json` or mark that id done while a check failed. Skip `smoke.md` for an id that does not change HTTP.

```markdown
## <check>

### Request

- Method:
- Path:
- Headers:
- Body:

### Response

- Status:
- Headers:
- Body:

### Verification

- Checked:
- Result: pass
```

`Body` under Response is the response body, or the excerpt that was checked. `Result` is `pass` or `fail`.

6. Run `.cursor/tools/verify-report.py --id <id> --strict` once for each id. Read only that id's `verify-report.md`. Do not paste command output.
7. For each id, write `.spec/tasks/<id>/verify.json` from that run:

```json
{
  "exit": 0,
  "at": "<ISO-8601 UTC>",
  "commit": "<git rev-parse HEAD>",
  "packages": ["<package this id's tests live in>"],
  "commands": ["<the Verify commands just run>"]
}
```

`commit` is HEAD before you commit the work. `packages` is not a copy of the same list for every id. Set the brief, `spec.md`, and the subtasks of each id to `done` in that same step. Do not mark an id done while its `smoke.md` has a failed check, or when that id changed HTTP and `smoke.md` is missing.

8. Stop. Report each id, the layer lines from its `verify-report.md`, and the smoke checks for each id that changed HTTP. Do not include command output. Do not leave `.spec/tasks/active` in place.
