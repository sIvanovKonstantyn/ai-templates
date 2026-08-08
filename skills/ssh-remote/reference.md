# SSH Remote — Reference

## SSH options (scripts)

Default non-interactive flags:

```
-o StrictHostKeyChecking=accept-new
-o IdentitiesOnly=yes   # when IdentityFile is set via SSH config
```

| Mode | Behavior |
|------|----------|
| Key auth (preferred) | `ssh` with `-o BatchMode=yes` — fails fast if key missing |
| Password fallback | `SSHPASS` set + `sshpass -e ssh` — **no** BatchMode (password auth would fail) |

Never put passwords in `~/.ssh/config`, skill markdown, `.ssh-remote.yml`, or git.

### known_hosts

`accept-new` adds new host keys without prompting; still refuses changed keys (MITM protection). For a one-time trust:

```bash
ssh-keyscan -H 192.168.x.x >> ~/.ssh/known_hosts
```

### ~/.ssh/config Host aliases

```sshconfig
Host lan-box
  HostName 192.168.x.x
  User deploy
  IdentityFile ~/.ssh/id_ed25519
```

Then onboard with `set-defaults.sh --host lan-box`, or set
`SSH_REMOTE_HOST=lan-box` / `host: lan-box` in `.ssh-remote.yml`.

### Personal defaults vs overrides

| Layer | File / mechanism | Scope |
|-------|------------------|--------|
| Call | `SSH_REMOTE_HOST=...` or `ssh-run.sh <host> ...` | One command |
| Project | `.ssh-remote.yml` | That repo |
| User defaults | `~/.cursor/ssh-remote/defaults.yml` | All projects |

Update personal defaults anytime with `set-defaults.sh` (see Workflow 0).

## Sudo and Docker

Probe whether the user can talk to the daemon without sudo:

```bash
docker info >/dev/null 2>&1 && echo nosudo || sudo -n docker info >/dev/null 2>&1 && echo sudo-nopass || echo sudo-needed
```

Set `compose` / `SSH_REMOTE_COMPOSE` accordingly:

- `docker compose` — Compose V2 plugin
- `docker-compose` — legacy V1 binary
- `sudo docker compose` / `sudo docker-compose` — when group membership is missing

Prefer passwordless sudo for automation (`sudo -n`). If sudo asks for a password interactively, stop and ask the user how to proceed (keys/NOPASSWD) — do not embed sudo passwords.

## rsync

Typical push (scripts add SSH transport):

```bash
rsync -avz --delete --exclude-from=deploy.rsync-exclude \
  -e "ssh <opts>" \
  ./ user@host:~/projects/python/app/
```

### Preserve on update

For paths that must **not** be overwritten from laptop (remote `data/`, `.env`):

1. List them under `preserve:` in `.ssh-remote.yml`, **or**
2. Add them to the exclude file for update deploys.

`--delete` removes remote files absent locally — dangerous with misconfigured excludes. Scripts default to **no** `--delete` unless `SSH_REMOTE_RSYNC_DELETE=1`.

### First-time data bootstrap

Only sync `.env` / `data/` when the user explicitly wants seed data. Otherwise keep them excluded/preserved.

## Compose V1 vs V2

| | V2 | V1 |
|--|----|----|
| Command | `docker compose` | `docker-compose` |
| Typical install | Docker Engine plugin | pip/apt standalone |
| Status | Current | Legacy (e.g. 1.29.x on older boxes) |

Detect:

```bash
docker compose version || docker-compose version
```

### ContainerConfig / KeyError workaround (V1)

Legacy `docker-compose` 1.29.x can fail on recreate with:

```text
KeyError: 'ContainerConfig'
```

Recovery:

```bash
# identify container name from compose ps / docker ps
sudo docker rm -f <container_name>
sudo docker-compose up -d --build
```

Prefer fixing compose/engine versions long-term; use rm+up only when this bug appears.

## Health checks

Remote (from the host):

```bash
curl -sf --max-time 10 http://127.0.0.1:8000/health
```

From laptop (LAN):

```bash
curl -sf --max-time 10 http://192.168.x.x:8000/health
```

Publish ports in compose (`ports:` or host network) or laptop curl will fail while remote curl works.

## Common failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Permission denied (publickey)` | No key / wrong user | Fix `~/.ssh/config`, or temporary `SSHPASS` |
| `sshpass: command not found` | Missing local tool | Ask before `brew install sshpass` / apt |
| `Host key verification failed` | Key changed | Verify host; update `known_hosts` |
| `Cannot connect to Docker daemon` | Need sudo or group | Adjust `SSH_REMOTE_COMPOSE` |
| `ContainerConfig` KeyError | Compose 1.29 bug | `docker rm -f` then `up -d --build` |
| Health fail after up | Wrong port / still starting | Wait, check `docker logs`, confirm bind |
| rsync overwrote `.env` | Not in preserve/exclude | Add to `preserve:` / exclude; restore from backup |

## Missing binaries

**Laptop:** `ssh`, `rsync`; optional `sshpass`, `ping`.  
**Remote:** `docker`; compose v1 or v2; often `curl`.

Report gaps and **ask** before installing (Workflow E).

## Security

- Ephemeral `SSHPASS` only; unset when done.
- Do not rsync private keys or dump files into the skill tree.
- Do not commit real `.ssh-remote.yml` secrets (there should be none — keep passwords out of YAML entirely).
