These documents are a map of what the code does today. Do not invent services, endpoints, topics, queues, packages, or configuration. Copy versions and property names from the build and configuration files. Do not guess a version.

If the repository has more than one deployable service, write one service document per service. A deployable service is a module with its own application entry point. Use the module or application name as `<service-name>`.

Write these files:

- `.spec/docs/<service-name>.md` — the service.
  - What the service is responsible for.
  - A filled mermaid `C4Component` diagram of its components and how they relate. Use the real package and class names.
  - Technologies, as a markdown table with columns Component, Version, and Role.
  - External dependencies: services it calls, queues, topics, and other systems outside this service.
  - Configuration properties the service reads, with the property name and where it is defined.

- `.spec/docs/integration-map.json` — external dependencies and the integration points visible in the code.

  ```json
  {
    "service": "<service-name>",
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
  `name` is the called endpoint, topic, or queue as the code names it.
  Omit a node you cannot see in the code. When there are several services, use a top-level `services` array of `{ "service", "nodes" }` objects.

- `.spec/docs/critical.md` — the only current-behavior page. Keys, the command list, and side effects live here. When the page is new, leave the body empty except for:

  `<!-- Populate the critical aspects of this service during implementation. -->`

  Component docs link to this page and do not repeat that paragraph.

- `.spec/docs/components/<component-name>.md` — one file for each high-level package in the service. A high-level package is the first package under the service's main source tree, such as `order` in `com.example.billing.order`. Do not write a component document for a `dto` package.
  Each file includes what the package is responsible for, a JSON dependency map of the packages or types it uses and the packages or types that use it, and mermaid sequence diagrams for behavior it implements. Skip the diagrams when the package has no logic.

- `.spec/docs/runbook.md` — how to run the service locally, plus the Verify section from `profiles/java/verify.md`.

- `.spec/docs/reviewer-rules.md` — the body of `profiles/java/standards.md`.
