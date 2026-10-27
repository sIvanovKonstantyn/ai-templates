# Commands

Send one of these to the agent. The id is the folder name under `.spec/tasks/`.

| Command | When |
| --- | --- |
| `/onboard` | Install the kit on a new or existing Go or Java repo. Writes docs, rules, skills, hooks, and `.spec/onboard.json`. |
| `/refresh` | Run onboard again. Keeps an existing constitution in place and appends the smoke rule when it is missing. Keeps reviewer rules that already have a body. Replaces `implement.md`, `batch.md`, `spec-pipeline.mdc`, and `commands.md` even when those files already exist. |
| `/implement <id>` | One brief. Spec, then code, then `.cursor/tools/verify-report.py`, then docs. The agent reads the short report and does not paste command output. Writes `smoke.md` when the task changes HTTP, then one `verify.json`. |
| `/batch` | Several briefs, in order. Spec, then code, then that id's tests, then docs, for each id. After the last id, writes `smoke.md` for each id that changed HTTP, then one full Verify run and a `verify.json` receipt per id. |
| `/investigate <id>` | The brief exists. The agent writes the finding and does not change product code. |
