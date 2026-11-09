# Agent kit

Two kinds of files live here.

The service pipeline is what `/onboard` and `/refresh` copy into a backend. Spec IDE does not send these files. It reads the copies in the target repo. A person writes `.spec/tasks/<id>/spec.md` with subtasks. Asking the agent to implement that id (or one subtask) runs the rest, and the person approves each subtask.

Role skills, the scripts those skills run, and the role rules are not part of service onboarding. Other pipelines install them on their own. Service onboard must not copy them.

## Service pipeline

| Path | Role |
| --- | --- |
| `pipeline/commands.md` | `/onboard`, `/refresh`, `/implement <id> [N]`, `/prepare-mr` |
| `pipeline/spec-template.md` | Shape of the spec a person writes: goal and subtasks, each with Definition, Recommendations, and Verification |
| `pipeline/brief.md` | Optional short request that may sit next to the spec (no Breaks section) |
| `pipeline/constitution.md` | Pipeline law, copied to `.spec/constitution.md` |
| `pipeline/onboard.md` | Onboard procedure |
| `pipeline/implement.md` | Implement all subtasks or one; per-subtask file and review states |
| `pipeline/tasks-readme.md` | Copied to `.spec/tasks/README.md` |
| `rules/spec-pipeline.mdc` | Always-on Cursor rule |
| `rules/go-standards.mdc` | Go file rule |
| `rules/java-standards.mdc` | Java file rule |
| `skills/spec-onboard/SKILL.md` | Onboard when asked |
| `skills/spec-implement/SKILL.md` | Implement a spec; HTTP and Event smoke checks |
| `skills/prepare-mr/SKILL.md` | Bump the version, add the changelog entry, commit, and print the MR link |
| `tools/verify-report.py` | Runs the runbook Verify layers and writes the short report. A spec's Verification section can name it; Smoke is deferred until `--strict` |
| `tools/smoke-http.py` | One HTTP smoke check; appends it to `smoke.md` with the token redacted |
| `tools/smoke-events.py` | Event smoke checks on a Redis stream (`ping`, `mark`, `expect`) |
| `tools/smoke/` | Redis env template, local Redis compose file, event tool self-test, token script |
| `tools/prepare-mr.py` | Version bump (`pom.xml` or `package.json`), changelog entry, and GitLab MR link |
| `profiles/go/` | Go docs, standards, and verify commands |
| `profiles/java/` | Java docs, standards, PMD ruleset, verify commands, and the style tool (`style-check.py`, `style/`) |

| `model-learning/` | Reference material for teaching agents: spec writing rules and worked brief-to-spec examples per language (`java/` now). Not copied by `/onboard` |
Profiles are `go` (a `go.mod`) and `java` (a `pom.xml` or `build.gradle`). Commit `.spec`. A gitignored spec folder has no spec commit, so Spec IDE cannot call the spec actual.

## Roles

These are not installed by service `/onboard` or `/refresh`. Prepared tools are the scripts inside each skill. Brain examples live in `schemas/`. No credentials, hostnames, bucket names, or SSM paths are hard-coded. AWS and org specifics live in brain files written by that role's onboard. SSH host defaults live in `~/.cursor/ssh-remote/defaults.yml`, outside git.

| Role | Rule | Skills | Tools |
| --- | --- | --- | --- |
| Devops | `rules/devops-role.mdc` | `devops-onboard`, `devops-aws`, `ssh-remote` | `skills/devops-aws/scripts/`, `skills/devops-onboard/scripts/`, `skills/ssh-remote/scripts/` |
| Analyst | `rules/analyst-role.mdc` | `analyst-onboard`, `analyst-docs` | `skills/analyst-docs/scripts/`, `skills/analyst-onboard/scripts/` |
| Architect | `rules/architect-role.mdc` | `architect-onboard`, `architect-analysis`, `architect-sad` | `skills/architect-analysis/scripts/`, `skills/architect-onboard/scripts/`, `skills/architect-sad/scripts/` |

| Role | Onboard writes |
| --- | --- |
| Devops | `.cursor/devops/brain.json`, `ONBOARD_REPORT.md`; may also set `~/.cursor/ssh-remote/defaults.yml` |
| Analyst | `.cursor/analyst/brain.json`, `CONTEXT.md` |
| Architect | `.cursor/architect/brain.json`, `CONTEXT.md` |

1. Copy only that role's rule and skills into the workspace `.cursor/` directory. Leave `spec-pipeline.mdc`, the Go and Java standard rules, and `spec-onboard` / `spec-implement` out of a role install.
2. Copy the matching `schemas/<role>-brain.example.json` to `.cursor/<role>/brain.example.json`.
3. Enable the role rule, or `@`-mention the `.mdc`.
4. Ask the agent to run that role's onboard skill.
5. Then use `devops-aws` and `ssh-remote`, `analyst-docs`, or `architect-analysis` and `architect-sad`.

`architect-analysis` is Java only. `devops-aws` calls its scripts rather than a raw AWS CLI. Prod-class profiles in `prod_profiles` need chat approval before any AWS call, and mutations need `--approve-prod`. SSH prefers keys. `SSHPASS` is session-only and is never committed.

SSH remote config precedence:

1. This call — `SSH_REMOTE_*` or `ssh-run.sh <host> ...`
2. Project — `.ssh-remote.yml` (no secrets)
3. User defaults — `~/.cursor/ssh-remote/defaults.yml` (from onboard / `set-defaults.sh`)

Devops auth comes from the brain `auth_mode`:

- `aws-vault` (default) — `vault_command` (for example `aws-vault`)
- `aws-profile` — AWS CLI `--profile` only
- `env` — ambient credentials (`AWS_ACCESS_KEY_ID` / role on the host)

A workspace may add `.cursor/permissions.json` that allows non-prod script runs and blocks prod-class profiles. This kit does not ship that file.

Company deploy CLIs, CRM/email vendors, CI/CD IAM onboarding, and monitor CRUD are out of scope. Cloud Kubernetes and AWS deploy CLIs are separate from LAN `ssh-remote` Compose workflows. Non-Java architect stacks are not shipped. Extend `architect-analysis` when one is needed.
