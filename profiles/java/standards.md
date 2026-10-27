# Reviewer rules

- Every required command under `## Verify` in `.spec/docs/runbook.md` exits 0, except for findings copied into `.spec/docs/baseline.md` at onboard. The agent runs `.cursor/tools/verify-report.py` and does not paste command output into the chat, the spec, or `verify.json`.
- Do not add an empty catch, an unused local, an unused private field, or an unnecessary import. The PMD ruleset at `.cursor/tools/pmd/ruleset.xml` checks those four.
- A package named `domain` does not depend on a package named `web`.
- Do not swallow an exception. Add context and rethrow, or handle the case the spec names.
