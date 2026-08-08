---
name: architect-analysis
description: >-
  Run deterministic architecture analysis (flows, APIs, events, libs, config)
  via prepared Java AST scripts and produce a structured report with minimal
  console output. Use when the Architect role is active; when analyzing an
  unknown service; or when mapping coupling, REST/events, or config/deploy
  topology. Requires architect-onboard brain for default paths.
---

# Architect analysis

Follow the workspace `architect-role` rule. Prefer scripts under this skill’s
`scripts/java/`. Defaults for artifacts/reports come from
`.cursor/architect/brain.json` (**architect-onboard**).

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/architect-analysis/scripts/java' -type d 2>/dev/null | head -n 1)"
ASSETS="$(dirname "$(dirname "$SCRIPTS")")/assets"
# Or fixed install path when present:
# SCRIPTS=.cursor/skills/architect-analysis/scripts/java
```

Ensure `ast-engine.jar` exists next to the Python scripts (build instructions below).

## Purpose

This skill orchestrates deterministic analysis scripts to extract architectural insights from the codebase.

It ensures:
- minimal token usage
- deterministic data collection via scripts
- structured and consistent reporting

---

## When to use

Use this skill when:

- analyzing a new or unknown codebase
- generating architecture overview
- investigating flows, APIs, or event-driven systems
- identifying coupling and system boundaries
- preparing technical documentation

---

## High-Level Strategy

1. Execute deterministic analysis scripts (AST, libs, config)
2. Summarize AST artifacts via `summarize_ast.py`
3. Generate issue hints via `generate_issues_hints.py`
4. Bundle all artifacts into single `analysis-bundle.json` via `bundle_artifacts.py`
5. Read ONLY the bundle (single file read) for analysis
6. Produce structured report

---

## Execution Rules (STRICT)

- ALWAYS prefer scripts over manual reasoning
- NEVER infer flows/APIs/events if artifacts exist
- DO NOT print raw artifacts (JSON, logs)
- MINIMIZE token usage
- PRINT ONLY step names during execution
- DO NOT explain intermediate steps
- Prefer `python3` when invoking scripts (some environments do not provide `python`)

---

## Console Output Rules (CRITICAL)

During execution, output ONLY:

```
STEP 1: Flow & dependency analysis
STEP 2: Technology stack
STEP 3: Configuration analysis
STEP 4: Summarization
STEP 5: Issue hints generation
STEP 6: Bundle artifacts
STEP 7: Final report
```

DO NOT output:
- script logs
- JSON content
- intermediate explanations

---

## Scripts Reference (Java)

> **IMPORTANT — Script Location:**
> All scripts are bundled with this skill. Resolve with `SCRIPTS` above, or use:
> ```
> .cursor/skills/architect-analysis/scripts/java/
> ```
> Do NOT look for scripts at `scripts/java/` in the workspace root.

| Script | Purpose | Input | Output |
|---|---|---|---|
| `ast_scanner.py` | Call graph, HTTP & event deps, REST entrypoints via Spoon AST | Java source root | `<svc>-ast.json`, `<svc>-http-dependencies.json`, `<svc>-event-dependencies.json` |
| `libs_kb_parser.py` | Maven dependency extraction | `pom.xml` | `libs-metadata.json` (+ optional `.md` stubs) in `<kb_dir>` |
| `gradle_libs_parser.py` | Gradle (Groovy) dependency extraction (deterministic, text-based) | `build.gradle` | `libs-metadata.json` (+ optional `.md` stubs) in `<kb_dir>` |
| `summarize_ast.py` | Compact metrics from AST artifacts | AST + HTTP + event JSONs | `<svc>-summary.json` |
| `parse_configs.py` | Spring profiles, feature flags, infra, deployment topology | Project root | `<svc>-config.json` |
| `generate_issues_hints.py` | Pre-generate deterministic issue hints from summary + config | summary + config JSONs | `<svc>-issues-hints.json` |
| `bundle_artifacts.py` | Merge summary + config + libs + issues-hints into single file | All artifact files | `<svc>-analysis-bundle.json` |

> `ast-engine.jar` must exist alongside the scripts. Build it with:
> ```bash
> cd "$SCRIPTS/ast-engine" && mvn package -q && cp target/ast-engine.jar ../ast-engine.jar
> ```

---

## Steps

### STEP 1: Flow & Dependency Analysis

Run:

```bash
python3 "$SCRIPTS/ast_scanner.py" \
  --source <path-to-java-sources> \
  --output artifacts/
```

Expected output:

* `artifacts/<service>-ast.json` — call graph (nodes + edges) + REST entrypoints with httpMethod/path
* `artifacts/<service>-http-dependencies.json` — outgoing HTTP calls
* `artifacts/<service>-event-dependencies.json` — event producers/consumers (Kafka, RabbitMQ, Spring ApplicationEvents, Redis Streams, custom EventProducer/EventConsumer, @EventAttributes, ApplicationListener)

The AST scanner detects REST endpoints directly from source annotations — no compiled `.class` files needed. Each REST entrypoint includes `httpMethod`, `path`, `class`, and `method`.

The scanner resolves `static final String` constants in annotation path values (e.g., `RestConstant.ID_PATH_VARIABLE_API + RestConstant.PDF_URI` → `/{id}/pdf`). This includes recursive resolution of concatenated constants and nested field references.

Node `type` values: `SERVICE`, `COMPONENT`, `REST_CONTROLLER`, `CONFIGURATION`, `REPOSITORY`, `UNKNOWN`

Entrypoint `type` values: `REST`, `EVENT`, `SCHEDULED`

Optional flags:

```bash
  --entrypoints com.example.OrderService   # limit to specific classes
  --depth 5                                # max call-graph depth
  --include-tests                          # include test sources
  --engine-jar "$SCRIPTS/ast-engine.jar"  # default location
```

---

### STEP 2: Technology Stack

This step depends on the build tool.

#### Maven projects (`pom.xml`)

Run:

```bash
python3 "$SCRIPTS/libs_kb_parser.py" <path-to-pom.xml> artifacts/libs-kb/
```

Expected output:

* `artifacts/libs-kb/<groupId>.<artifactId>.md` — one stub per Maven dependency
* `artifacts/libs-kb/libs-metadata.json` — categorized dependency metadata with version, scope, and category

The parser extracts version numbers (resolving `${property}` references from `<properties>`) and scopes from the POM. Dependencies are auto-classified into categories: `frameworks`, `datastores`, `security`, `caching`, `testing`, `integration`, `utilities`.

Use the categorized metadata directly in the Technology Stack section — no manual classification needed.

#### Gradle projects (`build.gradle`, Groovy)

Run:

```bash
python3 "$SCRIPTS/gradle_libs_parser.py" <path-to-build.gradle> artifacts/libs-kb/ --no-stubs
```

Expected output:

* `artifacts/libs-kb/libs-metadata.json` — categorized dependency metadata with version, scope (Gradle configuration), and category

Notes / constraints:
- This parser is intentionally **deterministic** and **text-based** (no Gradle execution).
- It supports common patterns: `ext { key = 'value' }` interpolation and `dependencies { implementation("g:a:v") ... }`.
- If the Gradle file uses advanced constructs (version catalogs, Kotlin DSL, custom functions), the output may have missing versions; still bundle and report that versions are unknown rather than inferring them.

---

### STEP 3: Configuration Analysis

Run:

```bash
python3 "$SCRIPTS/parse_configs.py" \
  --source <project-root> \
  --output artifacts/<service>-config.json
```

Expected output:

* `artifacts/<service>-config.json` — structured config data using diff-based format:
  - `configFiles` — discovered config files by category (spring, deployment, docker)
  - `profiles` — list of Spring profiles
  - `config.baseProfile` — name of the base profile (typically "default")
  - `config.base` — flattened key-value pairs for the base profile
  - `config.overrides` — per-profile diffs containing ONLY keys that differ from base (no redundant repetition)
  - `featureFlags` — feature flags with per-profile values
  - `infrastructure` — databases, cache, messaging config
  - `deployment` — per-environment deployment topology (replicas, resources)

Sensitive values (passwords, secrets, tokens, keys) are automatically redacted.

The diff-based format reduces token usage by avoiding repetition of shared config across profiles. Only overridden values appear in the `overrides` section.

---

### STEP 4: Summarization

Run:

```bash
python3 "$SCRIPTS/summarize_ast.py" \
  --ast artifacts/<service>-ast.json \
  --http-deps artifacts/<service>-http-dependencies.json \
  --event-deps artifacts/<service>-event-dependencies.json \
  --output artifacts/<service>-summary.json
```

Expected output:

* `artifacts/<service>-summary.json` — compact metrics including:
  - `entrypoints` — total count, grouped by type (REST/EVENT/SCHEDULED), with endpoint details
  - `graph.totalNodes`, `graph.totalEdges` — graph size
  - `graph.nodesByType` — count per component type, with up to 5 representative class names each
  - `graph.topFanOut` — top 10 nodes with most outgoing edges (coupling hotspots)
  - `graph.topFanIn` — top 10 nodes with most incoming edges (dependency magnets)
  - `graph.recursiveEdges` — self-referencing calls
  - `graph.bidirectionalPairs` — potential circular dependencies
  - `httpDependencies` — outgoing HTTP calls grouped by client class
  - `eventDependencies` — event producers/consumers summary
  - `flowComplexity` — top 15 entrypoints ranked by max flow depth (depth-0 entries are excluded to save tokens)

---

### STEP 5: Issue Hints Generation

Run:

```bash
python3 "$SCRIPTS/generate_issues_hints.py" \
  --summary artifacts/<service>-summary.json \
  --config artifacts/<service>-config.json \
  --output artifacts/<service>-issues-hints.json
```

Expected output:

* `artifacts/<service>-issues-hints.json` — pre-computed issue hints sorted by severity, including:
  - `totalHints` — total count
  - `bySeverity` — counts per severity level (high, medium, low)
  - `hints[]` — each hint has `type`, `severity`, `message`, and type-specific data

Detected issue types:
  - `god_class` — nodes with fan-out ≥ 15
  - `dependency_magnet` — nodes with fan-in ≥ 20
  - `get_state_changing` — GET endpoints with state-mutating method names (add, create, send, delete, etc.)
  - `unresolved_http_targets` — outgoing HTTP calls with no resolved target service
  - `high_unknown_ratio` — UNKNOWN-typed nodes ≥ 25% of total
  - `recursive_call` — self-referencing edges in call graph
  - `circular_dependency` — bidirectional call pairs
  - `deep_flow` — entrypoints with flow depth ≥ 6
  - `multi_store_risk` — multiple data store types detected without coordination
  - `missing_resilience` — 3+ HTTP dependencies with no circuit breaker/retry config
  - `deployment_risk` — autoscaling off + resources disabled
  - `deployment_misconfiguration` — autoscaling off but high maxReplicas

These hints are deterministic and should be used directly in the Issues section of the report. The LLM should add context and recommendations but NOT re-derive these issues from raw data.

---

### STEP 6: Bundle Artifacts

Run:

```bash
python3 "$SCRIPTS/bundle_artifacts.py" \
  --summary artifacts/<service>-summary.json \
  --config artifacts/<service>-config.json \
  --issues-hints artifacts/<service>-issues-hints.json \
  --libs-dir artifacts/libs-kb/ \
  --output artifacts/<service>-analysis-bundle.json
```

Expected output:

* `artifacts/<service>-analysis-bundle.json` — single file containing:
  - `summary` — full contents of summary.json
  - `config` — full contents of config.json (diff-based format)
  - `issuesHints` — full contents of issues-hints.json
  - `libraries{}` — categorized dependency map from libs-metadata.json, keyed by category (frameworks, datastores, security, caching, testing, integration, utilities). Each entry includes groupId, artifactId, version, and scope.

This is the ONLY file that needs to be read for STEP 7. Do NOT read individual artifact files separately.

Validation: the bundle MUST exist and contain all four top-level keys. If any section is missing, report it explicitly.

---

### STEP 7: Analysis & Report

Read ONLY `artifacts/<service>-analysis-bundle.json` (single file read).

Analyze the bundle contents:
- Use `bundle.summary` for graph metrics, entrypoints, flows, HTTP/event dependencies
- Use `bundle.config` for profiles, feature flags, infrastructure, deployment
- Use `bundle.libraries` for technology stack (already categorized — use keys directly as section headers)
- Use `bundle.issuesHints` as the primary source for the Issues section

For the Issues section: use the pre-generated hints directly. Add context and explanations but do NOT re-derive issues from raw metrics. The hints are deterministic and authoritative.

For Recommendations: reference specific issue hint types and propose concrete actions.

---

## Analysis Guidelines

### System Overview

* identify main modules from graph node types and their representative classes (from `nodesByType.*.classes`)
* define responsibilities from entrypoint groupings
* detect boundaries from fan-out/fan-in patterns

---

### Flow Analysis

* use `flowComplexity` to identify critical execution paths
* use `recursiveEdges` and `bidirectionalPairs` to detect cyclic dependencies
* use `topFanOut` to highlight bottleneck classes

---

### API Analysis (from AST entrypoints)

* list all REST endpoints from `entrypoints.byType.REST`
* group by controller class
* detect tight coupling from fan-out of controller methods
* identify inconsistencies in HTTP method usage

---

### Event Analysis

* map producers and consumers from `eventDependencies`
* detect async chains
* identify potential race conditions

---

### Technology Stack (from libs-kb)

* use `bundle.libraries` directly — dependencies are pre-categorized by the parser
* list each category with its dependencies, versions, and scopes
* flag outdated or potentially problematic dependencies based on version info

---

### Configuration & Deployment

* list Spring profiles from `bundle.config.profiles`
* use `bundle.config.config.base` for shared configuration and `bundle.config.config.overrides` for per-profile differences
* document feature flags from `bundle.config.featureFlags`
* map infrastructure from `bundle.config.infrastructure` (databases, cache, messaging)
* compare deployment environments from `bundle.config.deployment` (resources, scaling)

---

### Architecture Issues

Use `bundle.issuesHints.hints[]` as the primary source. For each hint:
* include the hint's `message` as the core finding
* add architectural context explaining why this matters
* reference specific data (fan-out count, node name, etc.) from the hint

The hints already detect:
* tight coupling (god_class hints)
* dependency magnets (dependency_magnet hints)
* recursive/circular calls (recursive_call, circular_dependency hints)
* REST anti-patterns (get_state_changing hints)
* unresolved dependencies (unresolved_http_targets hints)
* multi-store risks (multi_store_risk hints)
* missing resilience (missing_resilience hints)
* deployment issues (deployment_risk, deployment_misconfiguration hints)

You MAY add additional issues discovered during analysis that the hints don't cover (e.g., unclear boundaries, missing abstractions), but prioritize hint-based issues.

---

### Recommendations

Provide:

* refactoring suggestions
* decomposition strategies
* risk mitigation ideas

---

## Output Format (STRICT)

The report MUST follow the exact structure defined in `assets/report-template.md`.

Load the template before writing the report:

```
"$ASSETS/report-template.md"
```

The template defines:
- exact section order and headings
- what data to include in each section
- which artifact fields map to which sections
- table formats for deployment and flow complexity
- guidelines for issues and recommendations

DO NOT deviate from the template structure. Fill in each section using the corresponding artifact data.

---

## Constraints

* DO NOT re-run scripts if artifacts already exist (unless explicitly requested)
* DO NOT hallucinate missing data
* DO NOT analyze source code if artifacts are present
* DO NOT read raw ast.json — use the bundle instead
* DO NOT read individual summary/config/libs files — use the bundle instead
* DO NOT re-derive issues that are already in issuesHints — use them directly
* KEEP output concise and structured

---

## Optimization Rules

* Read ONLY `analysis-bundle.json` for the report step — do NOT read individual artifact files
* Prefer reading summary (inside bundle) over raw ast.json
* Use `issuesHints` from the bundle as the primary source for the Issues section — do NOT re-derive issues
* Prefer reading files over recomputation
* Avoid redundant analysis
* Summarize aggressively
* Use artifacts as single source of truth

---

## Optional Modes (if specified by user)

### Quick Mode

* high-level summary only
* skip deep analysis

### Deep Mode

* full analysis
* include detailed insights
* include edge cases

---

## Partial Execution (IMPORTANT)

If user requests specific analysis:

* "analyze APIs" → run STEP 1 + STEP 4, read `summary.json` entrypoints
* "analyze events" → run STEP 1 + STEP 4, read `summary.json` eventDependencies
* "analyze flows" → run STEP 1 + STEP 4, read `summary.json` flowComplexity + graph
* "analyze dependencies" → run STEP 1 + STEP 4, read `summary.json` httpDependencies
* "analyze libraries" → run STEP 2, read `libs-kb/` listing
* "analyze config" → run STEP 3, read `config.json`
* "analyze issues" → run STEPs 1–5, read `issues-hints.json`

For full analysis, always run STEPs 1–6 to produce the bundle, then read ONLY the bundle for STEP 7.

Still follow:

* execution rules
* output format
