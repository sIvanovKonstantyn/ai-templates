# Constitution
This repository is spec first for agent work.
1. A task is a folder `.spec/tasks/<id>/`. A person writes its `spec.md`. The spec lists subtasks, and each subtask has a Definition, Recommendations, and a Verification approach.
2. The agent does not write the spec unless the person asks. Without a complete spec, the agent writes no product code for that task.
3. The agent implements all subtasks, or the one subtask the person names. Each subtask has its own file `subtask-N.md` with a status and a progress log, created before the first product edit for that subtask.
4. The agent runs the Verification approach of the subtask and records pass or fail per check. A failing check is fixed in product code. Do not paste command output into the chat, the spec, or the subtask file. The commands, `.spec/docs/reviewer-rules.md`, and a baseline in `.spec/docs/baseline.md` stay as they are.
5. Only the person approves. The agent sets a finished subtask to `ready-for-review`. A subtask is `approved` only after the person says so. A task is done when all its subtasks are `approved`.
6. After the code matches the spec, update the doc files the spec names. Current behavior (keys, the command list, and side effects such as delete) lives only in `.spec/docs/critical.md`.
7. The spec does not change during implementation. The agent proposes a change and waits.
8. Smoke runs only when a subtask's Verification names it, once for that subtask. It follows the HTTP and Event smoke checks in `.cursor/skills/spec-implement/SKILL.md`. A failed check is fixed in product code and run again.
9. Tasks sent in chat, such as review feedback, fixes, and questions, do not use this workflow. The agent does them directly and creates no `.spec` files for them.
