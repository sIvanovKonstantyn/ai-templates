You are onboarding a repository for agent implementation. The workspace root is your current working directory.
Write files with your file tools. Printing a file is not a substitute for writing it.
Do not implement a product feature. Do not add `.spec/` to `.gitignore`. The spec folder must be committed so Spec IDE can compare it with later commits.

The kit root is the directory that contains this file's sibling folders `rules/`, `skills/`, `hooks/`, and `profiles/`. From a checkout of this workspace that is `spec-ide/templates`.

This procedure is service onboarding only. Do not copy role rules (`devops-role.mdc`, `analyst-role.mdc`, `architect-role.mdc`), `schemas/`, or any skill other than `spec-onboard` and `spec-implement`. Those skills, their scripts, and those roles belong to other pipelines.

## Detect the profile

- `go.mod` at the root, or the module you were asked to onboard, means profile `go`.
- `pom.xml`, `build.gradle`, or `build.gradle.kts` means profile `java`.
- Both means ask which module to onboard. Neither means stop. The kit has Go and Java profiles only.

Read `profiles/<profile>/docs.md`, `profiles/<profile>/verify.md`, and `profiles/<profile>/standards.md`.

## Write the spec

Create `.spec/` if it is missing.

- Copy `pipeline/constitution.md` to `.spec/constitution.md` when that file is missing. When `.spec/constitution.md` already exists, leave it in place. If it does not already contain the live HTTP smoke rule, append that rule from `pipeline/constitution.md` as the next numbered rule. Do not rewrite the rest of that file.
- Write the docs `profiles/<profile>/docs.md` describes. Map the code that is there. Do not invent services, endpoints, packages, or versions.
- Write `.spec/docs/reviewer-rules.md` from `profiles/<profile>/standards.md` when the file is missing, empty, or only the comment `Populate on demand with rules for AI reviewers`. Leave real rules in place.
- Write `.spec/docs/runbook.md`, including a `## Verify` section, from `profiles/<profile>/verify.md`. Use commands the repository can run. Add a `## Smoke` section. It says to start the app the way that runbook's local-run section already says, call the changed routes, and write `.spec/tasks/<id>/smoke.md`. Each check has three parts: the request (method, path, headers, body), the response (status, headers, and the body or the excerpt that was checked), and the verification (what was checked, pass or fail). Do not invent a server command the repository does not already use. When the runbook already exists, add `## Smoke` if that section is missing, and do not rewrite the rest of the file.
- Copy `pipeline/tasks-readme.md` to `.spec/tasks/README.md` when that file is missing. Do not put a task brief there.

## Install the agent files

On `/onboard` and `/refresh`, replace these kit procedure files from the kit even when they already exist:

- `rules/spec-pipeline.mdc` to `.cursor/rules/spec-pipeline.mdc`
- `pipeline/implement.md` to `.cursor/skills/spec-implement/implement.md`
- `pipeline/batch.md` to `.cursor/skills/spec-implement/batch.md`
- `pipeline/commands.md` to `.spec/docs/commands.md`

Copy the remaining files, and do not overwrite a file that already has local edits you did not just write:

- `rules/<profile>-standards.mdc` to `.cursor/rules/<profile>-standards.mdc`
- `skills/spec-onboard/` to `.cursor/skills/spec-onboard/`
- `pipeline/onboard.md` to `.cursor/skills/spec-onboard/PROCEDURE.md`
- `skills/spec-implement/` to `.cursor/skills/spec-implement/`
- `pipeline/investigate.md` to `.cursor/skills/spec-implement/investigate.md`
- `hooks/hooks.json` to `.cursor/hooks.json`
- `hooks/guard-product-writes.py` and `hooks/verify-stamp.sh` to `.cursor/hooks/`
- `tools/verify-report.py` to `.cursor/tools/verify-report.py`
- For Java, `profiles/java/pmd-ruleset.xml` to `.cursor/tools/pmd/ruleset.xml`

Write `AGENTS.md` at the repository root when it is missing:

```markdown
# Agent work

Send `/onboard`, `/refresh`, `/implement <id>`, `/batch`, or `/investigate <id>`.

Implement one task only by following `.cursor/skills/spec-implement/implement.md`.
A list of briefs follows `.cursor/skills/spec-implement/batch.md`.
The task id is the folder name under `.spec/tasks/`.
Onboard or refresh this repository by following `.cursor/skills/spec-onboard/SKILL.md`.
```

Make the hook scripts and `.cursor/tools/verify-report.py` executable.

## Verify and record

Run `.cursor/tools/verify-report.py`. Read `.spec/verify-report.md` when `--id` was omitted, or the task report when it was passed. Do not paste command output into the chat or the spec.

- When the report shows a layer pass, keep its commands.
- When the report shows an issue, append the command name and those issue lines to `.spec/docs/baseline.md`. Do not copy the command log. Remove that command from the required layer and add a line that new output must not add findings beyond the baseline. Do not fix the legacy code during onboard.

Write `.spec/onboard.json`:

```json
{
  "onboarded": true,
  "profile": "<go or java>",
  "commit": "<git rev-parse HEAD>"
}
```

Use an empty string for `commit` when the folder is not a git repository, and say so in the summary.

Stop. Summarize the profile, the Verify commands, and whether a baseline was written.
