# Java verify

Detect the build and put that command under Tests:

- `./gradlew` means `./gradlew test`
- `./mvnw` means `./mvnw -q test`
- otherwise `mvn -q test` when `pom.xml` exists

Copy `profiles/java/pmd-ruleset.xml` to `.cursor/tools/pmd/ruleset.xml`.

When the root build file is one you can extend without removing existing plugins, bind that ruleset so PMD fails the build. Put `./gradlew pmdMain` or `mvn -q pmd:check` under Style with `required: yes`. When binding it would mean rewriting the build, leave the ruleset on disk, set Style to `required: no`, and say in the runbook that PMD is not bound yet.

Add an ArchUnit test that domain does not depend on web only when both packages exist. Do not add a test that does not compile. The test command then runs it.

`.spec/docs/runbook.md` uses the layers below. Replace the sample test and style commands with the commands this repository runs. A Smoke command is the repository's own smoke script. Leave that fence empty when the only smoke record is `smoke.md`. Set E2E to `required: yes` only when the repository already has an end-to-end command.

## Verify

Run `.cursor/tools/verify-report.py --id <id>`. Read `.spec/tasks/<id>/verify-report.md` and nothing else from that run. Do not paste command output into the chat, the spec, or `verify.json`.

### Tests

required: yes

```
mvn -q test
```

### Style

required: yes

```
mvn -q pmd:check
```

### Smoke

required: when-http

```
```

### E2E

required: no

```
```

`required` is `yes`, `no`, or `when-http`. `when-http` runs the Smoke commands only when `.spec/tasks/<id>/smoke.md` records checks. A single line `HTTP: unchanged` skips Smoke. `yes` always runs the commands. `no` skips the layer.

The report lists only the failing lines. Keep a command in Verify only when it exits 0 on the current tree, or name it in `.spec/docs/baseline.md`. Copy the issue lines from the report into the baseline. Do not copy the command log.
