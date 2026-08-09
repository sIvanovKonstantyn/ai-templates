# ADS SAD — Reference

Based on the [Architecture Description Standard (ADS) v1](https://archstandard.org/v1/)
and the worked example
[Medwick Healthcare Trust — MyMedwick Patient Portal](https://archstandard.org/v1/examples/medwick-healthcare/).

## Document spine (do not reorder)

| # | Section | Intent |
|---|---------|--------|
| 0 | Document Control | Metadata, history, contributors, purpose |
| 1 | Executive Summary | Overview, drivers, strategy, scope, as-is, decisions, project, criticality |
| 2 | Stakeholders & Concerns | Register, concerns matrix, compliance/regulatory context |
| 3 | Architecture Views | Logical, Integration & Data Flow, Physical, Data, Security, Scenarios/ADRs |
| 4 | Quality Attributes | Operational excellence, reliability, performance, cost, sustainability |
| 5 | Lifecycle Management | CI/CD, transition/6R, test & release, ops, skills, exit |
| 6 | Decision Making & Governance | CRAIDS, guardrail exceptions (6.3), ADR log, compliance traceability |
| 7 | Appendices | Glossary, references, standards, sign-off |
| — | Compliance Scoring | Optional 0–5 per section for governance reviews |

Note: the Medwick example has **no §6.2** (jumps 6.1 → 6.3). Keep that numbering
unless ADS later publishes a different official template.

## Documentation depths (ADS)

| Depth | Expectation in this skill |
|-------|---------------------------|
| `minimum` | All headings present; core narrative + key tables filled; many TBD OK |
| `recommended` | Most tables and views filled; open questions explicit |
| `comprehensive` | Medwick-like completeness; N/A only with justification |

RFC-style SHALL/SHOULD/MAY tagging is defined by ADS; when unsure, keep the
section and mark TBD rather than omitting.

## Mapping from `architect-analysis` bundle

| Bundle field | Prefer SAD section(s) |
|--------------|------------------------|
| `summary.entrypoints` / REST | 3.1 Logical, 3.2 Integration, 3.6 Scenarios |
| `summary.httpDependencies` / `eventDependencies` | 3.2 Integration & Data Flow |
| `summary.graph` (fan-in/out, cycles) | 3.1 patterns/impact; 6.1 Risks |
| `config.profiles` / infra / deployment | 3.3 Physical, 3.4 Data, 4.x ops |
| `libraries` | 3.1 technology; 1.3 shared services |
| `issuesHints` | 6.1 Risks/Issues; 3.6 ADRs candidates |

Physical hosting, cost, legal, and approval rows usually need human input even
when code analysis is complete.

## Scaffold placeholders

`assets/sad-template.md` uses `{{LIKE_THIS}}` for scalars and `TBD` in tables.
`scripts/scaffold_sad.py` substitutes common metadata keys; remaining
placeholders stay for later fills.

## Attribution

ADS is published as open documentation (see archstandard.org). The Medwick
document is a **fictional example** used only to derive structure — do not copy
its healthcare narrative into customer SADs.
