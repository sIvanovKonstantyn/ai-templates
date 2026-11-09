# Tasks
One folder per task: `.spec/tasks/<id>/`.
A person writes `.spec/tasks/<id>/spec.md`. Use `.cursor/skills/spec-implement/spec-template.md`. Each subtask has a Definition, Recommendations, and a Verification approach. A `brief.md` may sit next to it as the short request.
`/implement <id>` implements all subtasks. `/implement <id> N` implements subtask N. The agent writes `subtask-N.md` with the status and progress log for each subtask.
The agent sets a finished subtask to `ready-for-review`. Only the user sets `approved`. A task is done when all its subtasks are `approved`.
Tasks sent in chat (review feedback, fixes, questions) do not need a folder here.
