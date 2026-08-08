# SSH Remote — Examples

```bash
SCRIPTS="$(find . -path '*/skills/ssh-remote/scripts' -type d 2>/dev/null | head -n 1)"
```

## Onboard default host

```bash
"$SCRIPTS/set-defaults.sh" --host 'user@192.168.x.x' --compose 'docker compose'
"$SCRIPTS/set-defaults.sh" --show
```

Change the default later:

```bash
"$SCRIPTS/set-defaults.sh" --host 'user@other-host'
```

## Override for one call

```bash
SSH_REMOTE_HOST=user@other-host "$SCRIPTS/ssh-run.sh" 'hostname'
"$SCRIPTS/ssh-run.sh" user@other-host 'hostname'
```

## Project config (inherits user default host if omitted)

`.ssh-remote.yml`:

```yaml
# host: omitted → use ~/.cursor/ssh-remote/defaults.yml
remote_path: ~/projects/python/my-app
exclude_file: deploy.rsync-exclude
compose: sudo docker-compose
health_url: http://127.0.0.1:8000/health
preserve:
  - data/
  - .env
```

```bash
cp "$(dirname "$SCRIPTS")/templates/deploy.rsync-exclude" ./deploy.rsync-exclude
```

## Probe

```bash
"$SCRIPTS/ssh-run.sh" 'hostname; whoami; pwd; docker compose version 2>/dev/null || docker-compose version; docker info >/dev/null 2>&1 && echo docker:ok || (sudo -n docker info >/dev/null 2>&1 && echo docker:sudo || echo docker:fail)'
```

## First deploy / update / logs

```bash
export SSH_REMOTE_PATH=~/projects/python/my-app
export SSH_REMOTE_EXCLUDE=./deploy.rsync-exclude
export SSH_REMOTE_COMPOSE='sudo docker-compose'
export SSH_REMOTE_HEALTH_URL=http://127.0.0.1:8000/health

"$SCRIPTS/deploy-compose.sh"
"$SCRIPTS/remote-logs.sh" web 200
"$SCRIPTS/ssh-run.sh" 'df -h'
```

## Example: ask-before-extend (Workflow E)

User: *On the remote, run `ncdu` and save a report.*

Agent: *This isn’t covered yet (no disk-usage helper / `ncdu` recipe). Can I add a script under `scripts/` and update the skill docs?*
