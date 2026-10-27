# Constitution

This repository is spec first for agent work.

1. A task is a folder `.spec/tasks/<id>/` with a `brief.md` written by a person.
2. When asked to implement that id, write `spec.md` and `subtask-N.md` before changing product code.
3. Implement one subtask at a time. Run `.cursor/tools/verify-report.py --id <id>` and reach a report with no issues before the next subtask. Do not paste command output into the chat, the spec, or `verify.json`.
4. The commands, `.spec/docs/reviewer-rules.md`, and a baseline in `.spec/docs/baseline.md` stay as they are. A failing command is fixed in product code.
5. After the code matches the spec, update the doc files the spec names. Current behavior (keys, the command list, and side effects such as delete) lives only in `.spec/docs/critical.md`. A later task updates that page and its own spec. It does not rewrite a task spec that already has `verify.json` with `"exit": 0`.
6. An investigation brief writes a finding and does not change product code.
7. Product code changes only while `.spec/tasks/active` names the one in-progress task.
8. A task that changes an HTTP route, method, request field, response body, or status calls those routes on the started application before `verify.json`. The task folder gets `smoke.md`. Each check records the request (method, path, headers, body), the response (status, headers, and the body or the excerpt that was checked), and the verification (what was checked, pass or fail). A failed check is fixed in product code and run again. The task is not done while a check failed. Skip `smoke.md` only when the task does not change HTTP. A task that does not change HTTP writes `HTTP: unchanged` as the only line of `smoke.md` when Smoke is `when-http`.
9. Test, style, smoke, and e2e output stays out of the chat, the spec, and `verify.json`. The only verify output an agent reads is `.spec/tasks/<id>/verify-report.md`.
