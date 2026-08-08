# Hosts inventory (example — no secrets)

Template for documenting LAN targets. Use **your** aliases and addresses — nothing
here is read by the skill. Real default host lives in
`~/.cursor/ssh-remote/defaults.yml` (via onboard).

| Alias | Address | User | Notes |
|-------|---------|------|-------|
| lan-box | `192.168.x.x` / `.local` name | `deploy` | Compose V2 |
| lab-pi | `192.168.x.y` | `pi` | Often needs `sudo docker` |

## Per-host SSH config (laptop)

```sshconfig
Host lan-box
  HostName 192.168.x.x
  User deploy
  IdentityFile ~/.ssh/id_ed25519
```

Then onboard with `--host lan-box` or set `host: lan-box` in a project file.

## Per-project deploy file

```yaml
# host: optional — omit to use personal defaults.yml
remote_path: ~/projects/python/my-app
exclude_file: deploy.rsync-exclude
compose: docker compose
health_url: http://127.0.0.1:8000/health
preserve:
  - data/
  - .env
```

Auth: SSH keys via `~/.ssh/config`, or session-only `SSHPASS` (never written here).
