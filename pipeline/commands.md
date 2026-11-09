# Commands
Send one of these to the agent. The id is the folder name under `.spec/tasks/`.
| Command | When |
| --- | --- |
| `/onboard` | Install the kit on a new or existing Go or Java repo. Writes docs, rules, skills, tools, and `.spec/onboard.json`. Installs no hooks. |
| `/refresh` | Run onboard again. Keeps reviewer rules that already have a body. Replaces `implement.md`, `spec-template.md`, `spec-pipeline.mdc`, `commands.md`, and the constitution when it still holds the old pipeline rules. Removes the files of the old hook pipeline. |
| `/implement <id>` | Implement all subtasks of the user-written `.spec/tasks/<id>/spec.md`, in order. Each subtask gets `subtask-N.md`, runs the Verification from the spec, and stops at `ready-for-review`. |
| `/implement <id> N` | Implement subtask N only. |
| `/prepare-mr` | On a `review/<TICKET>` branch: bump the version, add the changelog entry, commit, push, and print the merge request link. Never stages `.spec/`, `.cursor/`, or `AGENTS.md`. |
The user writes the spec (shape: `pipeline/spec-template.md`). The agent writes it only when asked. Only the user sets a subtask to `approved`.
Messages in chat, such as review feedback, fixes, and questions, are not commands and do not use the spec workflow.
