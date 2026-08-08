# Analyst doc templates

Use these skeletons when persisting analyses under configured docs roots.
Replace `{product}` with `brain.product_name` from analyst-onboard.

## Spec / vendor analysis

```markdown
# {Vendor / topic}: analysis vs {product}

**Date:** YYYY-MM-DD  
**Scope:** …  
**Inputs:** path to source PDF/doc, related docs  
**Status:** Draft | Reviewed  

---

## Summary

{2–4 sentences: what the doc requires and how it fits {product} today.}

## Requirements digest

1. …
2. …

## System fit

| Requirement | Evidence (path / service) | Status |
|-------------|---------------------------|--------|
| … | `…` | present \| partial \| missing \| unknown |

## Gaps & risks

- …

## Recommended next steps

1. …
```

## Gap analysis (requirements → system)

```markdown
# Gap analysis: {feature / program}

**Date:** YYYY-MM-DD  
**Inputs:** …  
**Compared to:** codebase + docs roots

## Must-have gaps

| ID | Requirement | Gap | Suggested owner |
|----|-------------|-----|-----------------|

## Nice-to-have / later

- …

## Already covered

- … (link docs + code)
```

## Naming reminders

- Prefer updating an existing service doc section over a near-duplicate file
- Postmortems stay dated; analyses may omit date in the filename if evergreen,
  but always put **Date:** in the body
- Cross-link related docs instead of copying them
