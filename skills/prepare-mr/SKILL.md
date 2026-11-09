---
name: prepare-mr
description: Prepare a merge request for the current review/<ticket> branch. Bumps the version, adds the changelog entry, commits, pushes, and prints a GitLab link to open the MR against the default target branch. Use for /prepare-mr, "prepare the MR", "make the MR link", or "commit and open MR".
---
# Prepare the MR
Helper: `.cursor/tools/prepare-mr.py`. It prints one line per command and never pushes.
The helper finds the version in `pom.xml` (the project's own `<version>`) or `package.json` (and keeps `package-lock.json` in sync). It writes the entry to the first changelog that already lists the current version among `documentation/CHANGELOG.yml`, `documentation/CHANGELOG.md`, and `CHANGELOG.md`. The runbook names the version file and the changelog when the repository has more than one.
`.spec/`, `.cursor/`, and `AGENTS.md` are internal. Never stage them, and never name or link them in the commit, the changelog, or the MR description.
## 1. Check the branch
1. Run `.cursor/tools/prepare-mr.py ticket`. It prints the ticket from `review/<TICKET-123>`. When it fails, stop and ask for the ticket. Do not guess one.
2. Run `.cursor/tools/prepare-mr.py target`. It prints the target branch `origin/HEAD` points to. Use it as `<target>` below. When the user names another target, pass `--target <branch>` to `bump` and `link`.
3. Check `.spec/tasks/*/subtask-*.md`. When a subtask is not `approved`, tell the user and ask before continuing.
4. Run `git fetch origin --tags`, so the helper sees released tags and the current `origin/<target>`. When the fetch cannot reach the remote, stop and ask the user to fix access. Without the remote state the helper can treat a released version as unreleased.
## 2. Write the short description
1. Read `git diff origin/<target>...HEAD`, `git diff --cached`, and `git diff`, plus the untracked files from `git status --short`.
2. For context, read `spec.md` and `subtask-*.md` in the task folders under `.spec/tasks/` that changed after `git merge-base HEAD origin/<target>`. Do not read raw logs.
3. Write one line in the style of the changelog: imperative, says what changed for a user of the service or library, at most 100 characters, no trailing period. The entry is `<TICKET> | <description>`.
4. When the branch has several unrelated changes, ask whether to use one entry or several. The commit message and the MR title use the first entry.
## 3. Bump the version and the changelog
```shell
.cursor/tools/prepare-mr.py bump --entry "<TICKET> | <description>" [--level patch|minor|major]
```
- Use `patch` by default. Use `minor` only when the user asks or the change adds a new API, configuration property, or event field that a client can rely on, and say which level you chose.
- A version counts as released when a tag `<version>` or `v<version>` exists, or when `origin/<target>` already has that version. A released version is bumped (`bumped=yes`), keeping a suffix such as `-SNAPSHOT`. Otherwise the entry goes under the current version (`bumped=no`).
- Running it again with the same entry adds nothing. `files=` lists what changed. Check `git diff` on those files: only the version and the changelog entry changed.
## 4. Commit
1. Run `git status --short`. Stage the product files by name, plus the files `bump` listed. Never stage `.spec/`, `.cursor/`, `AGENTS.md`, `.DS_Store`, build output, or credential files.
2. Show the user the staged list (`git diff --cached --stat`). When a file looks unrelated to the ticket, ask before committing.
3. Commit with the changelog entry as the only message line: `git commit -m "<TICKET> | <description>"`. Do not use `--no-verify` or `--amend`.
## 5. Write the MR description
Write it to `target/prepare-mr/description.md`, or another path git ignores. Keep it short and in this order:
```markdown
## Summary
<2 to 5 bullets: what changed and why, in product terms>
## Changes
- <component or file area>: <what changed>
- Configuration: <new or changed property and its default>, only when there is one
- Event / API: <payload, route, or status change>, only when there is one
## Smoke test
| Check | Request | Result |
|-------|---------|--------|
| <check name> | `<METHOD> <path>` or `event <stream>` | pass |
```
- Build the Smoke test table from the `smoke.md` files read in step 2. Leave out headers, bodies, record ids, and anything that looks like a token or a password.
- When no folder has a smoke check, or every `smoke.md` says only `HTTP: unchanged`, write `Not run: no HTTP or event changes.` under the heading. A library without smoke writes a `## Tests` section with the main tests instead.
- Do not mention `.spec`, task ids, verify reports, or the agent workflow.
## 6. Print the link
1. Push the branch with `git push -u origin <branch>`. Never force-push. When the push fails, say so plainly and do not present the link as ready.
2. Run `.cursor/tools/prepare-mr.py link --title "<TICKET> | <description>" --description-file <description file>`.
3. In the chat, give the new version, the commit hash and message, and the link. The user opens the link and creates the MR. Do not create the MR through an API unless the user asks.
