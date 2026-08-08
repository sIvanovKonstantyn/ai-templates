---
name: devops-onboard
description: >-
  First-time (or refresh) Devops setup: configure AWS auth (aws-vault / profile /
  env), classify prod profiles, probe IAM capabilities, sample infrastructure,
  and write .cursor/devops/brain.json plus ONBOARD_REPORT.md so devops-aws tools
  work without hard-coded company names. Use when enabling Devops in a new
  workspace or after AWS account/layout changes.
---

# Devops onboard

Run this **before** `devops-aws` in a new workspace (or when brain is stale).

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/devops-onboard/scripts' -type d 2>/dev/null | head -n 1)"
AWS_SCRIPTS="$(find . -path '*/skills/devops-aws/scripts' -type d 2>/dev/null | head -n 1)"
```

Uses `aws_lib` from `devops-aws` (sibling skill).

## Agent workflow

1. Confirm workspace has `.cursor/` and the kit skills installed.
2. Ask the user:
   - Auth mode: `aws-vault` | `aws-profile` | `env`
   - Which discovered profiles are **prod-class**
   - Region default
   - ECS cluster name template containing `{stack}` (e.g. `{stack}-cluster`)
   - Optional: CDN bucket name or tag; OpenSearch domain; Datadog SSM param paths
3. Run discovery (non-prod profile first; wait for chat `approve`/`yes` before any
   prod-class AWS call):

```bash
python3 "$SCRIPTS/devops_onboard.py" discover --env dev \
  --auth-mode aws-vault --region us-east-1
```

4. Apply confirmed values:

```bash
python3 "$SCRIPTS/devops_onboard.py" write \
  --env dev \
  --auth-mode aws-vault \
  --region us-east-1 \
  --prod-profiles prod \
  --cluster-template '{stack}-cluster' \
  --opensearch-domain my-domain \
  --cdn-bucket-tag Name=WebOriginBucket \
  --datadog-api-param /path/to/api-key \
  --datadog-app-param /path/to/app-key \
  --datadog-site-param /path/to/site
```

5. Show the user `.cursor/devops/ONBOARD_REPORT.md` and which tools are ready.
6. Hand off to `devops-aws`.

## Subcommands

| Command | Purpose |
|---------|---------|
| `discover` | List profiles, STS identity, probe capabilities, sample resources |
| `write` | Merge flags + optional discover snapshot into brain + report |
| `readiness` | Print which devops-aws tool groups are configured |

## Rules

- Never store credentials in the brain — only profile names, paths, and templates.
- Never invent org-specific defaults; if the user does not know a value, leave it
  null and mark the related tools blocked in the report.
- Prod-class probes require chat approval first (same as devops-role).
