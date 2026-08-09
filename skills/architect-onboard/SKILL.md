---
name: architect-onboard
description: >-
  First-time (or refresh) Architect setup: collect product label, artifacts
  directory, architecture reports root, and default stack (java); write
  .cursor/architect/brain.json and CONTEXT.md so architect-analysis works
  without hard-coded company paths. Use when enabling Architect in a new
  workspace.
---

# Architect onboard

Run this **before** a full `architect-analysis` in a new workspace.

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/architect-onboard/scripts' -type d 2>/dev/null | head -n 1)"
```

## Agent workflow

1. Ask the user for:
   - `product_name` / `org_label`
   - `artifacts_dir` (default `artifacts`)
   - `reports_root` (default `docs/architecture`)
   - `default_stack` (v1: `java`)
   - Optional `java_source_hint` (default `src/main/java`)
2. Write brain + context:

```bash
python3 "$SCRIPTS/architect_onboard.py" write \
  --product-name Acme \
  --org-label "Acme Engineering" \
  --artifacts-dir artifacts \
  --reports-root docs/architecture \
  --default-stack java \
  --java-source-hint src/main/java \
  --ensure-dirs
```

3. Show `.cursor/architect/CONTEXT.md` and hand off to `architect-analysis`
   (code evidence) and/or `architect-sad` (ADS Solution Architecture Documents).

## Subcommands

| Command | Purpose |
|---------|---------|
| `write` | Save brain + CONTEXT.md |
| `show` | Print current brain |

## Rules

- Never store secrets in the brain or CONTEXT.md.
- Do not invent a product brand — ask the user.
- Prefer paths the user confirmed over guessing monorepo layout.
