These documents are a map of what the code does today. Do not invent commands, packages, endpoints, or versions. Copy the Go version from `go.mod`.

Write these files:

- `.spec/docs/<module>.md` — the module.
  - What it is responsible for.
  - A filled mermaid `C4Component` diagram of its packages and how they relate. Use the real package names.
  - Technologies, as a markdown table with columns Component, Version, and Role.
  - External systems it calls.
  - Configuration it reads, with the name and where it is defined.

- `.spec/docs/integration-map.json` — external dependencies and the integration points visible in the code.

  ```json
  {
    "service": "<module>",
    "nodes": [
      {
        "name": "billing-service",
        "kind": "service",
        "integrationPoints": [
          { "name": "POST /orders", "kind": "endpoint" }
        ]
      }
    ]
  }
  ```

  `kind` on a node is `service`, `queue`, `topic`, `database`, or `other`.
  `kind` on an integration point is `endpoint`, `topic`, or `queue`.
  Omit a node you cannot see in the code. When several modules are in scope, use a top-level `services` array of `{ "service", "nodes" }` objects.

- `.spec/docs/critical.md` — the only current-behavior page. Keys, the command list, and side effects such as delete live here. When the page is new, leave the body empty except for:

  `<!-- Populate the critical aspects of this service during implementation. -->`

  Component docs link to this page and do not repeat that paragraph.

- `.spec/docs/components/<package>.md` — one file for each first-level package under the module that contains logic. Skip a package that is only generated output.
  Each file includes what the package is responsible for, a JSON dependency map of packages it uses and packages that use it, and mermaid sequence diagrams for behavior it implements. Skip the diagrams when the package has no logic.

- `.spec/docs/runbook.md` — how to build and run the module, plus the Verify section and the terminal-test note from `profiles/go/verify.md`.

- `.spec/docs/reviewer-rules.md` — the body of `profiles/go/standards.md`.
