# Cursor agent kit (generic)

Company-agnostic Cursor **roles**, **skills**, and **prepared tools** for:

- **Devops** — safe AWS ops via scripts (after onboard)
- **Analyst** — documentation inventory and analysis notes (after onboard)

No credentials, hostnames, bucket names, or SSM paths are hard-coded in skills.
Those live only in **brain files** written by the onboard skills (or filled by you).

## Install into a workspace

From this kit root:

```bash
KIT="$(pwd)"
WS="/path/to/your/project"   # must contain or create .cursor/

mkdir -p "$WS/.cursor/skills" "$WS/.cursor/rules" "$WS/.cursor/devops" "$WS/.cursor/analyst"

cp "$KIT/rules/"*.mdc "$WS/.cursor/rules/"
cp -R "$KIT/skills/"* "$WS/.cursor/skills/"
cp "$KIT/schemas/devops-brain.example.json" "$WS/.cursor/devops/brain.example.json"
cp "$KIT/schemas/analyst-brain.example.json" "$WS/.cursor/analyst/brain.example.json"
```

Symlinks work too if you prefer a single source of truth.

## First-time onboard

| Role | Skill | Writes |
|------|--------|--------|
| Devops | `devops-onboard` | `.cursor/devops/brain.json`, `ONBOARD_REPORT.md` |
| Analyst | `analyst-onboard` | `.cursor/analyst/brain.json`, `CONTEXT.md` |

1. Enable the role rule in Cursor (or `@`-mention the `.mdc`).
2. Ask the agent to run the matching onboard skill.
3. Then use `devops-aws` / `analyst-docs`.

## Auth (Devops)

Supported via brain `auth_mode`:

- `aws-vault` (default) — `vault_command` (e.g. `aws-vault`)
- `aws-profile` — AWS CLI `--profile` only
- `env` — ambient credentials (`AWS_ACCESS_KEY_ID` / role on the host)

Prod-class profiles listed in `prod_profiles` require chat approval before any AWS call, and mutates need `--approve-prod`.

## Layout

```
rules/           devops-role.mdc, analyst-role.mdc
schemas/         example brains
skills/
  devops-onboard/
  devops-aws/
  analyst-onboard/
  analyst-docs/
```

## Optional: Cursor Auto-review

You can add a workspace `.cursor/permissions.json` that allows non-prod script runs and blocks prod-class profiles. This kit does not ship one — keep that policy in your company workspace.

## Out of scope (v1)

Company deploy CLIs, CRM/email vendors, CI/CD IAM onboarding, and monitor CRUD. Extend with your own skills that read the same brains.
