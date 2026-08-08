---
name: analyst-onboard
description: >-
  First-time (or refresh) Analyst setup: collect docs roots, product/org label,
  naming conventions, and short context notes; inventory documentation; write
  .cursor/analyst/brain.json and CONTEXT.md so analyst-docs works without
  hard-coded company names. Use when enabling Analyst in a new workspace.
---

# Analyst onboard

Run this **before** deep `analyst-docs` work in a new workspace.

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/analyst-onboard/scripts' -type d 2>/dev/null | head -n 1)"
DOC_SCRIPTS="$(find . -path '*/skills/analyst-docs/scripts' -type d 2>/dev/null | head -n 1)"
```

## Agent workflow

1. Ask the user for:
   - `product_name` / `org_label` (for templates)
   - One or more `docs_roots` (relative to workspace or absolute)
   - Optional `source_roots` (vendor PDFs / specs outside docs)
   - Optional glossary / context bullets (architecture one-liners, glossary terms)
   - Optional filename naming overrides
2. Confirm paths exist (or create empty docs root if the user asks).
3. Write brain + context:

```bash
python3 "$SCRIPTS/analyst_onboard.py" write \
  --product-name Acme \
  --org-label "Acme Engineering" \
  --docs-root docs \
  --source-root specs \
  --note "Primary stack is ECS + RDS" \
  --glossary-term "FF=Fact Find"
```

4. Inventory:

```bash
python3 "$SCRIPTS/analyst_onboard.py" inventory
```

5. Show `.cursor/analyst/CONTEXT.md` and hand off to `analyst-docs`.

## Subcommands

| Command | Purpose |
|---------|---------|
| `write` | Save brain + CONTEXT.md |
| `inventory` | Run docs_index over brain roots; update `indexed_at` |
| `show` | Print current brain |

## Rules

- Never store secrets in the brain or CONTEXT.md.
- Do not invent a product brand — ask the user.
- Prefer paths the user confirmed over guessing monorepo layout.
