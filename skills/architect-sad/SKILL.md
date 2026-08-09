---
name: architect-sad
description: >-
  Author Solution Architecture Documents (SADs) following the Architecture
  Description Standard (ADS) v1 structure used by the Medwick Healthcare
  example. Use when writing or scaffolding a SAD, solution architecture doc,
  ADS document, architecture description, or when the Architect role needs a
  governance-ready design document (content may be filled later; template must
  be followed).
---

# Architect SAD (ADS)

Produce **Solution Architecture Documents** that follow the
[Architecture Description Standard (ADS) v1](https://archstandard.org/v1/)
section structure, as demonstrated by
[Medwick Healthcare — MyMedwick Patient Portal](https://archstandard.org/v1/examples/medwick-healthcare/).

This skill is about **document structure and fidelity**, not inventing
architecture facts. Prefer `architect-analysis` when extracting evidence from
code; then map evidence into this SAD template.

Follow the workspace `architect-role` rule when that role is active.

## Resolve paths

```bash
SAD_SKILL="$(find . -path '*/skills/architect-sad' -type d 2>/dev/null | head -n 1)"
TEMPLATE="$SAD_SKILL/assets/sad-template.md"
# Optional scaffold:
python3 "$SAD_SKILL/scripts/scaffold_sad.py" --solution "My Solution" --out path/to/sad.md
```

## Hard rules

1. **Never delete ADS headings** from the template. Keep the numbered outline
   (0–7 + Compliance Scoring). Use `TBD`, `N/A (justify briefly)`, or
   `Unknown — pending input` instead of removing sections.
2. **Do not invent** systems, costs, regulators, or approvals. If content is not
   available yet, leave placeholders and list open questions at the end of the
   draft (or in CRAIDS Assumptions/Issues).
3. **Copy the template first**, then fill. Do not free-form a different SAD
   outline unless the user explicitly requests a non-ADS document.
4. **Preserve table shapes** from the template (column headers). Add rows as
   needed; do not collapse required tables into prose unless a section is truly
   N/A (still keep the heading + one N/A row or sentence).
5. **Diagrams**: use mermaid/ASCII stubs or `![...](path)` links; never claim a
   diagram exists without creating or linking it.
6. **Secrets**: redact credentials, tokens, connection strings, and patient/PII
   samples. Prefer classifications and references over raw data.
7. **Depth**: ask (or use brain) for ADS depth — `minimum` / `recommended` /
   `comprehensive`. Shallower depth may leave more TBD, but **headings stay**.
8. **Output location**: write under brain `reports_root` (default
   `docs/architecture`) unless the user names a path. Suggested name:
   `{solution-slug}-sad.md`.

## Workflow

### A — Scaffold (empty / sparse SAD)

1. Confirm solution name, org label, output path, and depth.
2. Run `scaffold_sad.py` **or** copy `assets/sad-template.md`.
3. Replace `{{SOLUTION_NAME}}`, `{{ORG_NAME}}`, metadata fields if known.
4. Stop and show the path + list of sections still TBD (do not fabricate).

### B — Fill from known inputs

When the user (or prior analysis) provides facts:

1. Start from the scaffolded SAD (Workflow A).
2. Map inputs into the matching ADS section (see [reference.md](reference.md)).
3. Leave unmatched sections as TBD; record gaps in **6.1 Assumptions/Issues**.
4. Update **0.2 Change History** when revising.

### C — Fill from `architect-analysis` artifacts

When a Java analysis bundle exists:

1. Use bundle summary/config/libraries/issuesHints as **evidence only**.
2. Map into Logical / Integration / Data / Scenarios / CRAIDS as appropriate.
3. Do **not** invent Physical/Security/Cost/Compliance details not in evidence;
   mark TBD and ask.
4. Reference artifact paths under Appendices / Reference Documents.

### D — Review pass

Before calling a SAD “complete for review”:

- [ ] All top-level sections 0–7 present
- [ ] Metadata table filled or explicitly TBD
- [ ] No fabricated approvals or compliance claims
- [ ] Diagrams present or explicitly TBD
- [ ] Compliance Scoring left blank or filled only after human review

## Template

Canonical blank document (Medwick/ADS outline):

[`assets/sad-template.md`](assets/sad-template.md)

Section intent, table expectations, and code→SAD mapping:
[`reference.md`](reference.md)

## Related skills

| Skill | Use for |
|-------|---------|
| `architect-onboard` | Brain: `reports_root`, product/org labels |
| `architect-analysis` | Deterministic code evidence (Java v1) |
| `analyst-docs` | Requirements/PDF notes (not SAD structure) |
