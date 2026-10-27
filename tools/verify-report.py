#!/usr/bin/env python3
"""Run the runbook layers and write a short report.

A command may contain `<id>`. It is replaced with `--id` before the command runs.

Stdout and the report file contain the layer results and the failing lines only.
Command logs are not printed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SUB = re.compile(r"^###\s+(Tests|Style|Smoke|E2E)\s*$", re.I | re.M)
REQUIRED = re.compile(r"^required:\s*(yes|no|when-http)\s*$", re.I | re.M)
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
ISSUE = re.compile(
    r"(FAIL|ERROR|FAILURE|Exception|violation|panic:|undefined:|--- FAIL|BUILD FAILURE|There are \d+ errors|\berror:)",
    re.I,
)
HTTP_UNCHANGED = re.compile(r"^HTTP:\s*unchanged\s*$", re.I | re.M)
RESULT_FAIL = re.compile(r"Result:\s*fail\b", re.I)
RESULT_PASS = re.compile(r"Result:\s*pass\b", re.I)
DEFAULTS = {"tests": "yes", "style": "yes", "smoke": "when-http", "e2e": "no"}


def verify_body(text: str) -> str:
    match = re.search(r"^## Verify\s*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end() :]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def commands_in(body: str) -> list[str]:
    found: list[str] = []
    for block in FENCE.findall(body):
        for line in block.splitlines():
            command = line.strip()
            if command and not command.startswith("#"):
                found.append(command)
    return found


def parse_layers(text: str) -> list[dict]:
    body = verify_body(text)
    if not body.strip():
        return []
    marks = list(SUB.finditer(body))
    if not marks:
        return [{"name": "tests", "required": "yes", "commands": commands_in(body)}]
    layers = []
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(body)
        chunk = body[mark.end() : end]
        name = mark.group(1).lower()
        required_match = REQUIRED.search(chunk)
        required = required_match.group(1).lower() if required_match else DEFAULTS[name]
        layers.append({"name": name, "required": required, "commands": commands_in(chunk)})
    return layers


def highlight(text: str, limit: int = 40) -> list[str]:
    lines = text.splitlines()
    chosen: list[str] = []
    for index, line in enumerate(lines):
        if not ISSUE.search(line):
            continue
        for extra in lines[index : min(len(lines), index + 3)]:
            stripped = extra.rstrip()
            if stripped and stripped not in chosen:
                chosen.append(stripped)
        if len(chosen) >= limit:
            break
    if not chosen:
        chosen = [line.rstrip() for line in lines if line.strip()][-12:]
    return chosen[:limit]


def baselined(root: Path, command: str) -> bool:
    path = root / ".spec" / "docs" / "baseline.md"
    if not path.is_file():
        return False
    return command in path.read_text(encoding="utf-8", errors="replace")


def run_command(root: Path, command: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=root,
            timeout=300,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return 124, "timed out after 300s"
    except OSError as error:
        return 127, str(error)
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return result.returncode, combined


def smoke_note(root: Path, task_id: str) -> str | None:
    path = root / ".spec" / "tasks" / task_id / "smoke.md"
    if not path.is_file():
        return "smoke.md is missing. Write the checks, or a single line `HTTP: unchanged`."
    text = path.read_text(encoding="utf-8", errors="replace")
    if HTTP_UNCHANGED.search(text):
        if RESULT_FAIL.search(text):
            return "smoke.md says HTTP unchanged and also has a failed check."
        return ""
    if RESULT_FAIL.search(text):
        return "smoke.md has a check with Result: fail."
    if not RESULT_PASS.search(text):
        return "smoke.md has no check with Result: pass."
    return ""


def evaluate(root: Path, task_id: str, strict: bool) -> tuple[list[dict], list[str]]:
    runbook = root / ".spec" / "docs" / "runbook.md"
    if not runbook.is_file():
        return [], ["missing"]
    layers = parse_layers(runbook.read_text(encoding="utf-8", errors="replace"))
    rows: list[dict] = []
    issues: list[str] = []
    for layer in layers:
        name = layer["name"]
        required = layer["required"]
        if required == "no":
            rows.append({"name": name, "result": "not required", "commands": []})
            continue
        if name == "smoke" and required == "when-http":
            if not task_id:
                issues.append("Smoke is when-http. Pass --id.")
                rows.append({"name": name, "result": "fail", "commands": []})
                continue
            note = smoke_note(root, task_id)
            if note and note.startswith("smoke.md is missing") and not strict:
                rows.append({"name": name, "result": "not run", "commands": []})
                continue
            if note is None:
                rows.append({"name": name, "result": "fail", "commands": []})
                continue
            if note == "":
                unchanged = HTTP_UNCHANGED.search(
                    (root / ".spec" / "tasks" / task_id / "smoke.md").read_text(encoding="utf-8", errors="replace")
                )
                if unchanged:
                    rows.append({"name": name, "result": "not required", "commands": []})
                    continue
            elif note:
                issues.append(f"### Smoke\n\n- {note}")
                rows.append({"name": name, "result": "fail", "commands": []})
                continue
        if required == "yes" and not layer["commands"]:
            issues.append(f"### {name.title()}\n\n- required, and the runbook has no command.")
            rows.append({"name": name, "result": "fail", "commands": []})
            continue
        failed = False
        ran: list[str] = []
        for command in layer["commands"]:
            if task_id:
                command = command.replace("<id>", task_id)
            ran.append(command)
            if baselined(root, command):
                continue
            code, output = run_command(root, command)
            if code == 0:
                continue
            failed = True
            excerpt = highlight(output)
            block = [f"### {name.title()} — `{command}` — exit {code}", ""]
            block.extend(f"- {line}" for line in excerpt)
            issues.append("\n".join(block))
        rows.append({"name": name, "result": "fail" if failed else "pass", "commands": ran})
    return rows, issues


def render(rows: list[dict], issues: list[str]) -> str:
    lines = ["# Verify report", ""]
    if not rows and issues == ["missing"]:
        lines.append("- Runbook: fail")
        lines.extend(["", "## Issues", "", "- .spec/docs/runbook.md is missing.", ""])
        return "\n".join(lines)
    for row in rows:
        lines.append(f"- {row['name'].title()}: {row['result']}")
    lines.extend(["", "## Issues", ""])
    if not issues:
        lines.append("none")
    else:
        lines.append("\n\n".join(issues))
    lines.extend(["", "## Commands", ""])
    commands = [command for row in rows for command in row["commands"]]
    if commands:
        lines.extend(f"- `{command}`" for command in commands)
    else:
        lines.append("none")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Verify layers and write a short report.")
    parser.add_argument("--id", default="", help="Task id, the folder under .spec/tasks/")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--strict", action="store_true", help="Fail when a when-http smoke file is missing")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    task_id = args.id.strip()
    if task_id and ("/" in task_id or "\\" in task_id or task_id.startswith(".")):
        sys.stdout.write("# Verify report\n\n- Task: fail\n\n## Issues\n\n- --id must be one task folder name.\n")
        sys.exit(1)
    rows, issues = evaluate(root, task_id, args.strict)
    report = render(rows, issues)
    spec = root / ".spec"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "verify-report.md").write_text(report, encoding="utf-8")
    if task_id:
        destination = spec / "tasks" / task_id / "verify-report.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report, encoding="utf-8")
    sys.stdout.write(report)
    failed = any(row["result"] == "fail" for row in rows) or issues == ["missing"] or bool(issues)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
