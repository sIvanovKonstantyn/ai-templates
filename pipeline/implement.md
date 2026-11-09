You are implementing a user-written spec. The user approves the result, not you.
The workspace root is your current working directory.
## Start
1. If `.spec/onboard.json` is missing or `.spec/docs/runbook.md` has no `## Verify` section, stop and say the repository is not onboarded.
2. Read `.spec/tasks/<id>/spec.md` and every file the subtask's Recommendations name. Read `.spec/constitution.md` and `.spec/docs/critical.md` when they exist.
3. Check each subtask you will implement for Definition, Recommendations, and Verification. When `spec.md` is missing or a part is missing, stop. Name the gap. Do not write the spec.
4. Select subtasks. `/implement <id>` selects all, in order. `/implement <id> N` selects N only. Skip a subtask whose status is `approved`.
## Each subtask
1. Create `.spec/tasks/<id>/subtask-N.md` (shape below), or reopen it when it exists. Set `Status: in-progress`.
2. Change code only for that subtask. Follow its Recommendations.
3. Run the Verification approach from the spec. Run each automated check. Do each manual or smoke check. Record the result per check in the subtask file: pass or fail, and one line of evidence. Do not paste raw test, style, smoke, or e2e output. For automated checks you may use `.cursor/tools/verify-report.py --id <id>` and read only `.spec/tasks/<id>/verify-report.md`.
4. Fix product code when a check fails, and run it again. When a check cannot run, record why. Do not mark it pass.
5. Update the docs the Recommendations name.
6. Append to the progress log as you work. Each entry has the date and one or two lines.
7. When every check passes, set `Status: ready-for-review` and list the changed files. Stop and report to the user: subtask id, what changed, check results, deviations, open questions.
When running all subtasks, report after each subtask and continue with the next. Do not wait for approval between subtasks. A subtask that depends on a failed or blocked one stops the run.
## Subtask file
```markdown
# <id> / subtask N: <title>
Status: todo | in-progress | ready-for-review | changes-requested | approved
## Definition
<copied from spec.md>
## Progress log
- <date> <what was done or decided>
## Verification
- <check from the spec>: pass | fail | not run (<reason>)
## Changed files
- <path>
## Deviations and open questions
- <none, or what and why>
```
A subtask file that already exists may hold notes about code written before the spec (`Existing drift`). Keep those notes, check the code against the spec, and finish only what is missing.
## Smoke
Run smoke only when a subtask's Verification section names it. Follow "When smoke runs", "HTTP smoke checks", and "Event smoke checks" in `SKILL.md`.
## Review
- Only the user sets a subtask to `approved`. Set it when the user says so, naming the subtask or the task.
- When the user asks for changes in chat, make them. Set `Status: changes-requested` while you work and `ready-for-review` when done. Add a log entry. Do not edit the spec.
- The task is done when every subtask is `approved`. Report that to the user. Do not report a task as done before that.
