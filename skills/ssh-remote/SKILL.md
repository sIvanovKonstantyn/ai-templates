---
name: ssh-remote
description: >-
  Operate remote Linux hosts over SSH/rsync: probe connectivity, sync project
  trees, run remote commands, manage Docker Compose deploys, check health/logs.
  Use when the user asks to deploy, SSH, rsync to a server, restart a remote
  container, inspect remote logs, or update a LAN/Linux host over SSH.
---

# SSH Remote

**Host-agnostic** skill for Linux hosts over SSH: probe, sync, remote shell,
Docker Compose, health, logs, and safe update deploys. No hostname is baked
into this skill — defaults come from onboard; overrides are per-project or
per-call.

Follow the workspace `devops-role` when that role is active.

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/ssh-remote/scripts' -type d 2>/dev/null | head -n 1)"
```

## Config precedence (high → low)

1. **This call** — `SSH_REMOTE_*` env and/or `ssh-run.sh <host> ...`
2. **Project** — `.ssh-remote.yml` in the app repo (no secrets)
3. **User defaults** — `~/.cursor/ssh-remote/defaults.yml` (from onboard; outside git)

If host is still missing: **ask** (or run onboard). Never invent credentials or hosts.

## Workflow 0 — Onboard (default server)

Run once (or whenever the user wants a new default). **Ask** — do not guess:

1. Default SSH target: `user@host` **or** a `~/.ssh/config` Host alias
2. Optional: default compose command (`docker compose` / `sudo docker-compose`)
3. Optional: default `remote_path` prefix, `health_url`, exclude file
4. Auth method: keys (preferred) vs session `SSHPASS` (never write password to disk)

Write defaults:

```bash
"$SCRIPTS/set-defaults.sh" --host 'user@host' --compose 'docker compose'
"$SCRIPTS/set-defaults.sh" --show
```

**Change default later:** run `set-defaults.sh` again (partial flags merge).  
**Override one call:** `SSH_REMOTE_HOST=other@host ...` or `ssh-run.sh other@host '...'`.  
**Clear defaults:** `set-defaults.sh --clear`.

Also run this step when devops onboard reaches SSH/LAN setup, if defaults are missing.

## Config details

**Env (session / one call):**

| Variable | Meaning |
|----------|---------|
| `SSH_REMOTE_HOST` | `user@host` or SSH config Host alias |
| `SSH_REMOTE_PATH` | Remote project directory |
| `SSH_REMOTE_LOCAL` | Local root (default `.`) |
| `SSH_REMOTE_EXCLUDE` | rsync exclude file path |
| `SSH_REMOTE_COMPOSE` | e.g. `docker compose` or `sudo docker-compose` |
| `SSH_REMOTE_HEALTH_URL` | e.g. `http://127.0.0.1:8000/health` (run on remote) |
| `SSH_REMOTE_SERVICE` | Optional compose service / container name for logs |
| `SSHPASS` | Password fallback only — never commit or put in skill files |

**Optional project file** `.ssh-remote.yml` (no secrets):

```yaml
host: user@192.168.x.x   # omit to inherit user defaults
remote_path: ~/projects/python/my-app
exclude_file: deploy.rsync-exclude
compose: sudo docker-compose
health_url: http://127.0.0.1:8000/health
preserve:
  - data/
  - .env
```

Default exclude template: [templates/deploy.rsync-exclude](templates/deploy.rsync-exclude).

## Auth & shell

- Prefer **SSH keys** + `BatchMode=yes`.
- Password: `export SSHPASS='...'` then scripts use `sshpass -e`. Remind user to switch to keys. Never echo or write passwords into markdown/git.
- SSH: `StrictHostKeyChecking=accept-new`. Non-interactive only.
- If sandbox blocks LAN/SSH, use Shell `required_permissions: ["all"]`.

## Scripts (run these)

| Script | Usage |
|--------|--------|
| `set-defaults.sh` | Onboard / change / show / clear user default host |
| `ssh-run.sh` | `ssh-run.sh [host] '<remote cmd>'` |
| `rsync-push.sh` | Push local → remote with excludes + preserve |
| `deploy-compose.sh` | Sync + remote compose up/build + health curl |
| `remote-logs.sh` | `remote-logs.sh [service] [tail_lines]` |

`--help` on each script. Shared loader: `_lib.sh` (sourced, not run directly).

## Workflow A — Probe

Before mutating:

1. Resolve/ping host if needed.
2. Remote probe via `ssh-run.sh`:
   `hostname; whoami; pwd; command -v docker; docker compose version 2>/dev/null || docker-compose version 2>/dev/null; docker info >/dev/null 2>&1 || sudo docker info >/dev/null 2>&1; echo exit:$?`
3. Report: user, docker/compose flavor, whether `sudo` is required. Stop if SSH fails.

## Workflow B — First deploy

1. Confirm ports if user cares about conflicts.
2. `ssh-run.sh 'mkdir -p <remote_path>'`
3. `rsync-push.sh` (include `.env` / `data/` only if user explicitly wants bootstrap).
4. Remote: `$SSH_REMOTE_COMPOSE up -d --build` (via `deploy-compose.sh` or `ssh-run.sh`).
5. Health: remote `curl -sf "$SSH_REMOTE_HEALTH_URL"` and/or laptop → `http://<lan-ip>:<port>/health`.
6. Summarize URL, containers, remote path.

## Workflow C — Update deploy (code only)

1. Rsync **preserving** `preserve:` paths (`data/`, `.env`, …) unless user asks to overwrite.
2. Compose rebuild/restart (`deploy-compose.sh` or equivalent).
3. If legacy compose errors with `KeyError: 'ContainerConfig'` (or similar): `docker rm -f <container>` then `up -d --build` again. See [reference.md](reference.md).
4. Re-check health + recent logs (`remote-logs.sh`).

## Workflow D — Remote ops (not full copy)

Prefer scripts; same SSH options for raw `ssh`/`rsync`/`scp` fallbacks.

Examples: list `data/…`, `docker logs`, restart one service, one-off migration/pytest, `df -h`, single-file `rsync`/`scp`.

## Workflow E — Extensibility (missing commands / tools)

**Follow this every time:**

1. Prefer existing skill scripts and documented recipes.
2. If the user asks for an action that has **no matching script**, no documented workflow, or needs a **new remote/local command** the skill does not cover:
   - **Stop and ask** before inventing a permanent helper.
   - Ask something like: *“This isn’t covered yet (missing X). Can I add a script under `scripts/` and update the skill docs?”*
   - Wait for explicit yes/no.
3. If the user **approves**:
   - Add a thin script under this skill’s `scripts/` (create the tool).
   - Update `SKILL.md` (and `examples.md` / `reference.md` if needed) so the next run discovers it.
   - Keep the same config/auth/safety conventions as existing scripts.
4. If the user **declines**:
   - Do a one-off `ssh`/`rsync` for this session only; do **not** silently grow the skill.
5. Never silently rewrite the skill for convenience. Never add secrets into skill files while extending.

**Host tooling gaps:** if a required binary is missing on the laptop (`sshpass`, `rsync`) or on the remote (`docker`, `curl`), report what is missing and ask whether to install / document a workaround — do not install packages without approval.

## Workflow F — Safety

- Never commit `.env`, passwords, private keys, or production DB dumps into the skill or into git because of a deploy.
- Prefer key-based SSH; if user pastes a password, use `SSHPASS` for the session and remind them to switch to keys.
- Do not `rm -rf` remote `data/` unless the user explicitly requests destructive reset.
- Request Shell `required_permissions: ["all"]` (or equivalent) when sandbox blocks SSH/LAN.
- Do not force-push or change git config as part of deploy.
- Do not hard-code machine names into this skill; use user defaults / project config / call overrides only.

## Verification

```bash
SCRIPTS="$(find . -path '*/skills/ssh-remote/scripts' -type d 2>/dev/null | head -n 1)"
"$SCRIPTS/set-defaults.sh" --help
"$SCRIPTS/ssh-run.sh" --help
"$SCRIPTS/set-defaults.sh" --show   # or onboard if missing
"$SCRIPTS/ssh-run.sh" 'echo ok && hostname'
```

## More detail

- Recipes: [examples.md](examples.md)
- SSH/rsync/compose pitfalls: [reference.md](reference.md)
- Documenting hosts (no secrets): [hosts.example.md](hosts.example.md)
