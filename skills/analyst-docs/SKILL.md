---
name: analyst-docs
description: >-
  Read PDFs and text docs, inventory configured docs roots, and write analysis
  notes. Use when the Analyst role is active; when analyzing vendor PDFs, specs,
  or requirements against the codebase; or when producing gap/fit analyses.
  Requires analyst-onboard brain for default roots and product label.
---

# Analyst docs

Follow the workspace `analyst-role` rule. Prefer scripts under this skill’s
`scripts/` for PDF extraction and docs inventory. Defaults come from
`.cursor/analyst/brain.json` (**analyst-onboard**).

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/analyst-docs/scripts' -type d 2>/dev/null | head -n 1)"
```

## 1. Bootstrap PDF deps (first use)

```bash
python3 -m venv "$SCRIPTS/.venv"
"$SCRIPTS/.venv/bin/pip" install -r "$SCRIPTS/requirements.txt"
```

## 2. Inventory existing docs

```bash
python3 "$SCRIPTS/docs_index.py"
python3 "$SCRIPTS/docs_index.py" --query billing
python3 "$SCRIPTS/docs_index.py" --json
```

Uses `brain.docs_roots` unless `--root` is passed. With no brain,
`--allow-missing-brain` falls back to `./docs` (prefer running onboard).

## 3. Read source material

| Tool | Purpose |
|------|---------|
| `pdf_extract.py PATH [--pages N-M] [--json]` | Extract PDF text (pypdf) |
| `read_doc.py PATH [--pages N-M] [--max-chars N]` | Unified reader |

**v1 formats:** PDF, Markdown, plain text, JSON, YAML, CSV, `.log`.  
**Not yet:** OCR, `.docx` / `.xlsx`.

## 4. Analyse against the system

1. Inventory docs roots for related notes
2. Extract the external doc
3. Grep the codebase for evidence
4. Fit/gap table: requirement → evidence → status
5. Persist under a configured docs root (see naming)

Use `brain.product_name` in headings (“analysis vs {product}”).

## 5. Write docs

See [reference-templates.md](reference-templates.md). Filename patterns come from
`brain.naming` when set; otherwise:

| Kind | Pattern |
|------|---------|
| Analysis | `{topic}-analysis.md` |
| Review | `{topic}-review-YYYY-MM-DD.md` |
| Post-mortem | `{topic}-YYYY-MM-DD-postmortem.md` |
| Service | `{service}-service.md` |
| Guide | `{topic}-guide.md` |

Ask before overwriting a non-trivial existing file.

## Out of scope

OCR, Office binaries, auto-commit, AWS mutations (→ Devops).
