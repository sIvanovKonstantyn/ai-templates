# Project Analysis Report

## System Overview

Describe the service: name, version, language, framework, purpose.

Graph summary: total nodes, total edges, breakdown by component type (SERVICE, COMPONENT, REST_CONTROLLER, REPOSITORY, CONFIGURATION, UNKNOWN) with counts and key class names per type.

---

## Technology Stack

List dependencies by category directly from `bundle.libraries` keys:

Frameworks:
- (groupId:artifactId vVersion — scope)

Data stores:
- (groupId:artifactId vVersion — what they store)

Security:
- (groupId:artifactId vVersion)

Caching:
- (groupId:artifactId vVersion)

Integration:
- (groupId:artifactId vVersion)

Testing:
- (groupId:artifactId vVersion — scope)

Utilities:
- (groupId:artifactId vVersion)

---

## Configuration & Deployment

Profiles: list all Spring profiles and their purpose.

Feature flags:
- (flag name — description, per-profile values)

Infrastructure:
- (databases: type, name, connection details)
- (messaging: type, host, consumer groups)
- (cache: type, config)
- (FHIR/CDR: base URL)
- (auth: provider, realm, endpoints)

External services (from HTTP dependencies):
- (client class — call count, methods, target service if resolved)

Deployment environments table:

| Environment | Replicas | CPU (req/limit) | Memory (req/limit) | Autoscaling |
|---|---|---|---|---|
| env1 | min-max | req / limit | req / limit | on/off |

---

## Flows

Most complex flows table (from flowComplexity — only entries with depth > 0 are included):

| Endpoint | Depth | Fan-out |
|---|---|---|
| METHOD path (class) | N | N |

Top fan-out hotspots (from topFanOut):
1. (node — count, what it does)

Top fan-in dependency magnets (from topFanIn):
1. (node — count)

Recursive calls (from recursiveEdges):
- (from → to, explanation)

---

## APIs

Total endpoint count, total controller count.

Per controller:
- ControllerName (N endpoints):
  - `METHOD /path` — description
  - ...

---

## Events

If events detected:
- Map producers and consumers
- List channels/topics
- Describe async chains

If no standard events detected but event-like patterns exist in AST:
- List event producer/consumer classes found in the graph
- Note the messaging transport (Kafka, Redis Streams, etc.) from config
- List consumer groups

---

## Issues

Numbered list. Each issue should include:
1. Short title — description with supporting data (fan-out count, recursive edge, version number, etc.)

Focus on:
- God classes (high fan-out)
- Multi-store consistency risks
- Recursive/circular calls without guards
- Unresolved HTTP targets
- Outdated dependencies
- Security concerns
- Missing caching/resilience patterns

---

## Recommendations

Numbered list. Each recommendation should:
- Reference a specific issue number
- Propose a concrete action
- Be actionable (not vague)
