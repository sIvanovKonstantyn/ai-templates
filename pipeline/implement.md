You are implementing one task. The workspace root is your current working directory.
The person sent `/implement <id>`. A list of briefs is `/batch` and follows `batch.md` in this directory, or `../../pipeline/batch.md` in the kit. Do not use this file for a list.

Do these steps in order. Do not start a later step while the current one is unfinished.

1. If `.spec/onboard.json` is missing or `.spec/docs/runbook.md` has no `## Verify` section, stop and say the repository is not onboarded.
2. Read `.spec/constitution.md`, `.spec/docs/reviewer-rules.md`, `.spec/docs/critical.md`, the Verify section, and `.spec/tasks/<id>/brief.md`.
3. If the brief kind is `investigation`, follow `investigate.md` in this directory, or `../../pipeline/investigate.md` in the kit, and stop. Do not change product code.
4. The brief needs a `## Breaks` section with three filled lines: status text and the tests that assert it, keys the change redefines, and filesystem side effects (`HOME`, trash, git). `none` is a filled line. Copy that section into `spec.md`.
5. Write `.spec/tasks/<id>/spec.md` before any product edit. Include the behavior, the acceptance criteria, the Breaks section, and the doc files this change must update. Current behavior (keys, the command list, what delete does) is updated in `.spec/docs/critical.md`. Component docs link there and do not repeat the paragraph. Do not edit another task's `spec.md` after that task has `verify.json` with `"exit": 0`.
6. Write `subtask-1.md` and, for a medium or large change, further `subtask-N.md` files. Each starts as `- **Status:** `open``. A small change is one subtask.
7. When `spec.md` already states requirements a person wrote, keep those requirements. Add acceptance criteria, Breaks, or the doc list only where they are missing.
8. Set the subtask you are about to code to `in-progress` and write the id as the only line of `.spec/tasks/active`. Do not leave another task folder in progress.
9. Change the code. Run `.cursor/tools/verify-report.py --id <id>`. Read `.spec/tasks/<id>/verify-report.md` and nothing else from that run. Do not run the test, style, smoke, or e2e commands yourself. Do not paste their output into the chat, the spec, or `verify.json`. Do not read surefire reports, raw command logs, or `.spec/tasks/<id>/.smoke-raw.md`. On an issue in the report, fix product code and run the tool again. Do not edit reviewer rules, `.cursor/rules/`, the PMD ruleset, ArchUnit tests, or `.spec/docs/baseline.md`. Findings listed in the baseline may remain. New findings may not.
10. Update `.spec/docs/critical.md` when keys, the command list, or a side effect changes. Update the other docs the spec names. A component doc links to `critical.md`.
11. When this task changes an HTTP route, method, request field, response body, or status, start the application the way the `## Smoke` section of `.spec/docs/runbook.md` says and call those routes before writing `verify.json`. Write `.spec/tasks/<id>/smoke.md`. Each check has the three parts below. A failed check is fixed in product code and run again. Do not edit reviewer rules, the PMD ruleset, ArchUnit tests, or `.spec/docs/baseline.md`. The task is not done while a check failed. Skip `smoke.md` only when the task does not change HTTP.

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
12. Run `.cursor/tools/verify-report.py --id <id> --strict` again. Write `.spec/tasks/<id>/verify.json` only after that report has no issues. When the task changed HTTP, also wait until every smoke check passed. `packages` lists the packages this task's tests live in. `commands` lists the commands named in the report, not their output. The hook runs the same tool and rejects `"exit": 0` when the report has an issue.

```json
{
  "exit": 0,
  "at": "<ISO-8601 UTC>",
  "commit": "<git rev-parse HEAD>",
  "packages": ["<package>"],
  "commands": ["<each Verify command>"]
}
```

13. In the same step, set the brief, `spec.md`, and every subtask to `done`, then delete `.spec/tasks/active`. Do not mark the task done while a smoke check failed, or when this task changed HTTP and `smoke.md` is missing.
14. Stop. Report the id, the files changed, and the layer lines from `verify-report.md`. Do not include command output. When the task changed an HTTP route, also report each smoke check: the request, the response, and pass or fail. Do not open another task folder.
