#!/usr/bin/env python3
"""Allow a product edit only for the id in .spec/tasks/active.

That folder must contain spec.md and exactly one in-progress subtask.
A second in-progress folder is denied. A verify.json receipt with exit 0
is denied unless its package tests pass.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

EDIT_TOOLS = {"Write", "StrReplace", "Delete", "EditNotebook", "ApplyPatch"}
BUILD_FILES = {
    ".gitignore",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradle.properties",
    "go.mod",
    "go.sum",
}
STATUS = re.compile(r"status\s*[:：]\s*\**\s*`?in-progress`?", re.IGNORECASE)
KIND = re.compile(r"kind\s*[:：]\s*\**\s*`?investigation`?", re.IGNORECASE)
RECEIPT = re.compile(r"^\.spec/tasks/([^/]+)/verify\.json$")


def allow() -> None:
    json.dump({"permission": "allow"}, sys.stdout)
    sys.exit(0)


def deny(agent_message: str) -> None:
    json.dump(
        {
            "permission": "deny",
            "user_message": "Spec pipeline blocked a product edit.",
            "agent_message": agent_message,
        },
        sys.stdout,
    )
    sys.exit(0)


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        allow()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        allow()
    tool = str(data.get("tool_name") or data.get("toolName") or "")
    if tool not in EDIT_TOOLS:
        allow()
    tool_input = data.get("tool_input") or data.get("input") or {}
    if not isinstance(tool_input, dict):
        allow()
    target = tool_input.get("path") or tool_input.get("file_path") or tool_input.get("target_file") or ""
    if not isinstance(target, str) or not target:
        allow()
    root = Path(data.get("cwd") or ".").resolve()
    path = Path(target)
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError:
        deny("Write spec.md, set one subtask to in-progress, and write that id in .spec/tasks/active.")
        return
    receipt = RECEIPT.match(relative)
    if receipt:
        check_receipt_write(tool, tool_input, root, receipt.group(1))
        return
    if allowed_without_task(relative):
        allow()
    reason = active_task_problem(root)
    if reason:
        deny(reason)
    allow()


def allowed_without_task(relative: str) -> bool:
    if relative in {"AGENTS.md", "CLAUDE.md"} or relative in BUILD_FILES:
        return True
    return relative.startswith(".spec/") or relative.startswith(".cursor/") or relative == ".cursor/hooks.json"


def check_receipt_write(tool: str, tool_input: dict, root: Path, task_id: str) -> None:
    if tool != "Write":
        deny("Write .spec/tasks/<id>/verify.json as a whole file so the receipt can be checked.")
    text = tool_input.get("contents") or tool_input.get("content") or ""
    if not isinstance(text, str) or not text.strip():
        deny("verify.json needs exit, at, commit, packages, and commands.")
    try:
        receipt = json.loads(text)
    except json.JSONDecodeError:
        deny("verify.json is not valid JSON.")
        return
    if not isinstance(receipt, dict):
        deny("verify.json must be an object.")
    problem = receipt_problem(receipt, root, task_id)
    if problem:
        deny(problem)
    allow()


def receipt_problem(receipt: dict, root: Path, task_id: str) -> str | None:
    stuffed = output_in_receipt(receipt)
    if stuffed:
        return stuffed
    if receipt.get("exit") != 0:
        return None
    missing = [key for key in ("at", "commit", "packages", "commands") if key not in receipt]
    if missing:
        return "verify.json with exit 0 needs " + ", ".join(missing) + "."
    packages = receipt.get("packages")
    commands = receipt.get("commands")
    if not isinstance(packages, list) or not packages or not all(isinstance(item, str) and item.strip() for item in packages):
        return "verify.json packages must list the packages this task's tests live in."
    if not isinstance(commands, list) or not all(isinstance(item, str) and item.strip() for item in commands):
        return "verify.json commands must list the commands that were run."
    if not isinstance(receipt.get("at"), str) or not isinstance(receipt.get("commit"), str):
        return "verify.json at and commit must be strings."
    return report_problem(root, task_id)


def output_in_receipt(receipt: dict) -> str | None:
    def too_long(value: object) -> bool:
        return isinstance(value, str) and len(value) > 200

    for key, value in receipt.items():
        if too_long(value):
            return "verify.json must not contain command output. Read verify-report.md."
        if isinstance(value, list) and any(too_long(item) for item in value):
            return "verify.json must not contain command output. Read verify-report.md."
        if key.lower() in {"output", "stdout", "stderr", "log", "logs"}:
            return "verify.json must not contain command output. Read verify-report.md."
    return None


def report_problem(root: Path, task_id: str) -> str | None:
    script = root / ".cursor" / "tools" / "verify-report.py"
    if not script.is_file():
        return "Missing .cursor/tools/verify-report.py."
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--id", task_id, "--strict"],
            cwd=root,
            timeout=600,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "verify-report.py did not finish."
    if result.returncode != 0:
        report = (result.stdout or result.stderr or "verify-report.py failed").strip()
        return report[:2000]
    return None


def active_task_problem(root: Path) -> str | None:
    tasks = root / ".spec" / "tasks"
    active_file = tasks / "active"
    if not active_file.is_file():
        return "Write the task id into .spec/tasks/active before changing product files."
    task_id = active_file.read_text(encoding="utf-8", errors="replace").strip()
    if not task_id or "/" in task_id or "\\" in task_id or task_id.startswith("."):
        return ".spec/tasks/active must contain one task id."
    counts = in_progress_counts(tasks)
    crowded = [name for name, count in counts.items() if count > 1]
    if crowded:
        return f"{crowded[0]} has more than one in-progress subtask."
    folders = [name for name, count in counts.items() if count == 1]
    if len(folders) > 1:
        return "A second task is in progress. Finish it and clear .spec/tasks/active before editing another."
    if folders != [task_id]:
        return "The in-progress subtask must be in the folder named by .spec/tasks/active."
    folder = tasks / task_id
    if not (folder / "spec.md").is_file():
        return f"Write .spec/tasks/{task_id}/spec.md before changing product files."
    brief = folder / "brief.md"
    if brief.is_file() and KIND.search(brief.read_text(encoding="utf-8", errors="replace")):
        return "An investigation brief cannot change product files."
    if receipt_is_done(folder / "verify.json"):
        return "This task already has verify.json with exit 0. Clear .spec/tasks/active."
    return None


def in_progress_counts(tasks: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    if not tasks.is_dir():
        return found
    for folder in sorted(tasks.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        count = 0
        for sub in folder.glob("subtask-*.md"):
            if STATUS.search(sub.read_text(encoding="utf-8", errors="replace")):
                count += 1
        if count:
            found[folder.name] = count
    return found


def receipt_is_done(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(value, dict) and value.get("exit") == 0


if __name__ == "__main__":
    main()
