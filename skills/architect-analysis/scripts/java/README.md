# Architect analysis — Java tools

Scripts live next to this README. Prefer `python3`.

## Requirements

- Python 3.8+
- Java 17+ (for `ast_scanner.py` / `ast-engine.jar`)
- Maven (only when rebuilding the engine from source)

## Build AST engine

```bash
cd ast-engine
mvn package -q
cp target/ast-engine.jar ../ast-engine.jar
```

A prebuilt `ast-engine.jar` ships with the skill. Rebuild after changing Java sources under `ast-engine/src/`.

## Scripts

| Script | Purpose |
|--------|---------|
| `ast_scanner.py` | Spoon AST: call graph, REST entrypoints, HTTP/event deps |
| `libs_kb_parser.py` | Maven `pom.xml` → `libs-metadata.json` (+ optional stubs) |
| `gradle_libs_parser.py` | Groovy `build.gradle` → `libs-metadata.json` (text-based) |
| `parse_configs.py` | Spring/deploy config → `*-config.json` (secrets redacted) |
| `summarize_ast.py` | Compact metrics from AST artifacts |
| `generate_issues_hints.py` | Deterministic issue hints |
| `bundle_artifacts.py` | Single `*-analysis-bundle.json` for the report step |

See the parent `SKILL.md` for the full STEPs 1–7 orchestration.

## Note

Legacy `rest_scanner.py` (javap / compiled classes) is **not** included. REST
entrypoints come from `ast_scanner.py` on source. Do not look for `rest_scanner.py`.
