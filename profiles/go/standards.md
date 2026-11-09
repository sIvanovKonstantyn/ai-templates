# Reviewer rules

- `test -z "$(gofmt -l .)"`, `go vet ./...`, and `go test ./...` exit 0, except for findings copied into `.spec/docs/baseline.md` at onboard. The agent runs `.cursor/tools/verify-report.py` and does not paste command output into the chat or the spec.
- An error return includes the operation that failed. Do not drop an error with `_` unless the spec says the call is best-effort.
- Feature behavior lives in the package the task spec names.
- Exported names that the task spec introduces are documented in the spec, and the doc files named there are updated in the same task.
