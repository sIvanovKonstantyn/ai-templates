# Java verify

Detect the build and put that command under Tests:

- `./gradlew` means `./gradlew test`
- `./mvnw` means `./mvnw -q test`
- otherwise `mvn -q test` when `pom.xml` exists

Copy `profiles/java/pmd-ruleset.xml` to `.cursor/tools/pmd/ruleset.xml`, `profiles/java/style-check.py` to `.cursor/tools/style-check.py`, and `profiles/java/style/` to `.cursor/tools/style/`.
For a Maven project, put `python3 .cursor/tools/style-check.py` under Style with `required: yes`, after the Tests command (prefix `JAVA_HOME=...` when the project needs a specific JDK). The tool does not change the build file. It runs PMD with the kit ruleset, with the PMD jars resolved from `style/pmd-pom.xml`, a standalone descriptor that is never built, and `RedundantAnnotationDefaults`, which flags an annotation attribute set to its declared default value. It needs the compiled classes from the Tests command. It reports only findings on lines changed against the upstream merge-base, plus untracked files, one line each as `path:line Rule message`, so legacy findings do not fail a task. `--all` reports every finding; record that count in the baseline. Set `SPEC_MAVEN_SETTINGS` when Maven needs a settings file other than `~/.m2/settings.xml`.
For a Gradle project the style tool does not apply. When the build can be extended without removing existing plugins, bind the ruleset with `./gradlew pmdMain` under Style. Otherwise leave the ruleset on disk, set Style to `required: no`, and say in the runbook that PMD is not bound yet. Do not add PMD, Checkstyle, or other plugins to a Maven build file.

Add an ArchUnit test that domain does not depend on web only when both packages exist. Do not add a test that does not compile. The test command then runs it.

`.spec/docs/runbook.md` uses the layers below. Replace the sample test and style commands with the commands this repository runs. A Smoke command is the repository's own smoke script. Leave that fence empty when the only smoke record is `smoke.md`. Set E2E to `required: yes` only when the repository already has an end-to-end command.

## Verify

Run `.cursor/tools/verify-report.py --id <id>`. Read `.spec/tasks/<id>/verify-report.md` and nothing else from that run. Do not paste command output into the chat or the spec.

### Tests

required: yes

```
mvn -q test
```

### Style
required: yes
```
python3 .cursor/tools/style-check.py
```

### Smoke

required: when-http

```
```

### E2E

required: no

```
```

`required` is `yes`, `no`, or `when-http`. `when-http` runs the Smoke commands only when `.spec/tasks/<id>/smoke.md` records checks. A single line `HTTP: unchanged` skips Smoke. `yes` always runs the commands. `no` skips the layer. A library with no runnable application uses Smoke `required: no`.
Smoke runs only when a subtask's Verification section names it. Without `--strict` the report shows a `when-http` Smoke layer as `deferred to task finish`. `--strict` evaluates `smoke.md`: HTTP checks with `Result: pass`, and at least one Event check when `smoke.md` says `Events: changed`. Manual smoke steps (start, `smoke-http.py`, `smoke-events.py`) are written outside code fences, because Verify runs every fenced command.

The report lists only the failing lines. Keep a command in Verify only when it exits 0 on the current tree, or name it in `.spec/docs/baseline.md`. Copy the issue lines from the report into the baseline. Do not copy the command log.
