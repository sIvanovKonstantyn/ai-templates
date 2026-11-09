# Spec writing rules (Java services)

These rules describe how we write specs. They come from one worked example, `examples/file-setting-attachments/` (a design brief for file attachments turned into a 7-subtask spec), and from the gaps found when a spec was checked against code that already existed.

Each rule has a tag:
- **[observed]** the example spec does this.
- **[lesson]** a gap found while implementing and reviewing a spec of this kind. The rule closes it.

An agent writes a spec only when the person asks for one. The person reviews and approves it. The shape of the file is `pipeline/spec-template.md`.

## 1. Before writing

1. **[observed]** Read the whole brief, then the code it touches. Name the classes, methods, and packages that exist today. A spec that names no real class is not ready.
2. **[observed]** A brief (a ticket, a design document) is wider than one change. Pick the slice that this change delivers. Keep the slice small enough to review in one pass.
3. **[lesson]** List what the brief asks for and the spec does not deliver. Show this list to the person before the spec is final. In the example the brief describes metadata tables, rollback, cache and events, client libraries, idempotency, and virus scanning. The first spec dropped them without saying so. The spec needs an `## Out of scope` section for this.
4. **[lesson]** When the brief and the code or an external contract disagree, ask. Do not choose silently. Examples: the brief names two client interfaces, the spec uses one concrete client class and a Feign client. The brief describes one endpoint of another service, the real contract is a different internal endpoint.
5. **[lesson]** Close open questions in the spec text. Do not leave "decide whether" or "TBD". If the person has not answered, the spec stays `Status: draft`.

## 2. File shape

6. **[observed]** The file is `.spec/tasks/<task-id>/spec.md`. The first line is `# <task-id>: <title>`. The second line is `Status: draft` or `Status: ready`. The person sets `ready`.
7. **[observed]** Sections in order: `## Goal`, `## Out of scope`, a scope diagram, `## Subtasks`.
8. **[observed]** Goal is 2 to 4 plain sentences. It states the user-visible result, not the implementation. Example: "let an administrator attach an uploaded file to a setting" and "let an administrator read the setting with a temporary download link".
9. **[observed]** The scope diagram is a Mermaid C4 component diagram of the service. New components are green, changed ones are orange, everything else is grey or external. Each component description starts with the subtask number. Two short "Flows" paragraphs follow the diagram.
10. **[observed]** Subtasks are `### N. <title>`, numbered 1 to N without gaps or repeats.
11. **[lesson]** `## Out of scope` lists the brief items this spec does not deliver.

## 3. Splitting into subtasks

12. **[observed]** Order subtasks bottom up, so each one compiles and can be verified when the earlier ones are done. Example order: enum, request model and validators, outbound client, facade integration, second outbound client, facade read method, REST endpoint.
13. **[observed]** One subtask is one layer or one small cluster of classes with their tests. Typical size: one to three production classes.
14. **[observed]** Tests belong to the subtask that changes the code. There is no separate "write tests" subtask.
15. **[observed]** Documentation changes belong to the subtask that changes the behavior: `.spec/docs`, sequence diagrams, `openapi.yaml`.
16. **[observed]** Never write a subtask for smoke testing. Name smoke in the Verification of the subtask that needs it.
17. **[observed]** A trivial subtask (one enum value) is allowed to stand alone when later subtasks depend on it.
18. **[lesson]** State a dependency when a subtask needs another one ("depends on subtask 3") so the agent can run subtasks separately.

## 4. Writing each subtask

Every subtask has three parts, in this order, with these bold labels.

### Definition
19. **[observed]** 1 to 3 sentences. Say what must be true when the subtask is done. Name the exact classes, methods, fields, and enum values in backticks.
20. **[observed]** State the behavior for the main case. Put edge cases and failure behavior in Recommendations when they are not obvious from the code.

### Recommendations
21. **[observed]** Where to put the code: the package path (`src/main/java/.../client`).
22. **[observed]** What to copy from: a real class, method, or test in the repository or a sister service. Name it. Paste a short reference snippet when the pattern is not in this repository.
23. **[observed]** Paste external contracts in the spec: the OpenAPI of the endpoint to call, an example response, the Maven dependency block, the YAML properties. The agent must not guess them.
24. **[observed]** Give explicit negatives: "do not rate limit", "do not use any caching", "use the wrapper bean, never the plain Feign client", "admin use only, say so in a comment".
25. **[observed]** State error behavior: which exception is thrown, what is logged, and "follow the logging approach of `<class>`".
26. **[observed]** Say which existing test class to extend and what cases to add, including the exceptional ones. Name the style reference.
27. **[observed]** List docs to update by path.
28. **[lesson]** The reference snippet must agree with the contract. If the snippet uses a different path or body, say so: "take the structure only; path, body, and authentication come from the contract below".
29. **[lesson]** Name every new configuration property: key, example value, and where it comes from (`application.yml`, environment, a library). A property with no default stops the service from starting. Say so, and say where the value is defined.
30. **[lesson]** Name the exception and error code for a new integration failure (class, `ErrorCode` entry, HTTP status), and the constants for new log fields.
31. **[lesson]** For a validator or a mapper, list the negative inputs: null, empty, blank, wrong type. A validator that returns "valid" for a null value hides a missing field.
32. **[lesson]** When a class gets a new constructor dependency, name the Spring test setup that must provide it (for example the shared REST test base class with `@MockitoBean`).
33. **[lesson]** When a change alters an enum, a message, or a list of accepted values, name the existing tests that assert it. Search the tests for the old text.
34. **[lesson]** When a subtask adds a bean of the same type as another bean, define a wrapper interface in the spec (`ExtendedGatewayClient extends GatewayClient`) so injection is unambiguous.

### Verification
35. **[observed]** Each subtask has a Verification section with a runnable command and a pass condition.
36. **[observed]** Trivial type or enum change: the compile command. Anything with logic or tests: the verify tool (`.cursor/tools/verify-report.py --id <task-id>`, or the `.kiro/tools/` copy). Pass when the exit code is 0 and `verify-report.md` shows `Issues: none`.
37. **[lesson]** The default test run excludes `*ITest` classes. When a subtask changes a REST resource, a Spring test setup, or an `ITest`, add the explicit command for those classes.
38. **[lesson]** Say what is not verified ("Not covered: ...") when the gap is deliberate.

## 5. Java and Spring conventions the spec relies on

The spec does not repeat these. It points to them, and the agent follows them.
- Package roles: `client` (outbound HTTP), `dto`, `exception`, `facade`, `rest`, `validation`, `model`, `util` (log key constants).
- One concrete `@Component` client per downstream service, named after the service plus `Client`. Constructor injection through Lombok. No interface plus implementation when one implementation exists.
- The shared HTTP client with timeout and retry, a service token from the identity provider, the base URL from a service-registry property, the service's own settings under `app.<service>.*`.
- One exception per integration that extends the service base exception, with its own error code and HTTP 502 for downstream failures.
- Fluent SLF4J logging with constants for the keys. No tokens, headers, or bodies in logs.
- Tests: JUnit 5, Mockito, AssertJ, `InOrder` for call order, parameterized tests for repeated cases, test class named `<Class>Test` in the same package, extend the existing test class instead of adding one per task.
- Read-modify-write flows stay in the facade. Controllers stay thin.

Project-specific detail lives in the repository's coding rules (`.kiro/steering/` or `.cursor/rules/`). Cite that file in the spec instead of copying it.

## 6. Self-check before handing the spec over

The agent runs this list and fixes the spec until every line is true.
- [ ] The title has the task id. `Status` is `draft` until the person sets `ready`.
- [ ] Goal is short and names the result, not the code.
- [ ] `Out of scope` lists the brief items that are not delivered.
- [ ] The diagram marks new and changed components and matches the subtasks.
- [ ] Subtasks are numbered 1 to N, bottom up, and each depends only on earlier ones.
- [ ] Every subtask has Definition, Recommendations, and Verification.
- [ ] Every Definition names exact classes or methods.
- [ ] Every Recommendations names where the code goes and what to copy from.
- [ ] External contracts, payload examples, dependency blocks, and properties are in the spec.
- [ ] Negative constraints and error behavior are written down.
- [ ] Tests, docs, and test-setup changes are named in the subtask that causes them.
- [ ] Every Verification has a runnable command and a pass condition. `ITest` classes are named when needed.
- [ ] No open question is left in the text.
- [ ] No class, method, property, or path in the spec is invented. Each one exists, or the spec says it is new.

## 7. Adding a new example

1. Create `examples/<slug>/` with `brief.md`, `spec.md`, and `analysis.md`.
2. Remove company, product, and ticket names. Use neutral names (`example.com`, `settings-service`) and a task id that is not a ticket number.
3. In `analysis.md` map each brief section to a subtask, list what was dropped, and list what the review of the implementation found.
4. Add or change a rule here. Tag it **[observed]** or **[lesson]** and name the example.
