#!/usr/bin/env python3
"""Diff app-container env vars between two task definition revisions/ARNs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws

# Names matching these substrings (case-insensitive) are redacted in diffs.
REDACT_SUBSTR = ("KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL")


def env_map(task_def: dict, app_name: str) -> dict[str, str]:
    for c in task_def.get("containerDefinitions") or []:
        if c.get("name") == app_name:
            return {e["name"]: e.get("value") or "" for e in c.get("environment") or []}
    raise SystemExit(f"App container {app_name!r} not found in task definition")


def redact(name: str, value: str) -> str:
    if any(s in name.upper() for s in REDACT_SUBSTR) and value:
        return "***REDACTED***"
    return value


def load_td(env: str, ref: str, region: str | None, brain: dict) -> dict:
    return od_aws.run_aws(
        env,
        ["ecs", "describe-task-definition", "--task-definition", ref],
        region=region,
        brain=brain,
    )["taskDefinition"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--app", required=True, help="App container name (usually stack name)")
    parser.add_argument("--current", required=True, help="Current task def family:rev or ARN")
    parser.add_argument("--planned", required=True, help="Planned/other task def family:rev or ARN")
    args = parser.parse_args()
    brain = od_aws.load_brain()

    cur_td = load_td(args.env, args.current, args.region, brain)
    new_td = load_td(args.env, args.planned, args.region, brain)
    cur = env_map(cur_td, args.app)
    new = env_map(new_td, args.app)

    names = sorted(set(cur) | set(new))
    missing_in_planned = []
    added_in_planned = []
    changed = []
    for name in names:
        in_cur = name in cur
        in_new = name in new
        if in_cur and not in_new:
            missing_in_planned.append(name)
        elif in_new and not in_cur:
            added_in_planned.append(name)
        elif cur[name] != new[name]:
            changed.append(
                {
                    "name": name,
                    "current": redact(name, cur[name]),
                    "planned": redact(name, new[name]),
                }
            )

    od_aws.emit(
        {
            "env": args.env,
            "app": args.app,
            "current": {
                "taskDef": f"{cur_td.get('family')}:{cur_td.get('revision')}",
                "image": next(
                    (
                        c.get("image")
                        for c in cur_td.get("containerDefinitions") or []
                        if c.get("name") == args.app
                    ),
                    None,
                ),
                "envCount": len(cur),
            },
            "planned": {
                "taskDef": f"{new_td.get('family')}:{new_td.get('revision')}",
                "image": next(
                    (
                        c.get("image")
                        for c in new_td.get("containerDefinitions") or []
                        if c.get("name") == args.app
                    ),
                    None,
                ),
                "envCount": len(new),
            },
            "missingInPlanned": missing_in_planned,
            "addedInPlanned": added_in_planned,
            "changed": changed,
            "warning": (
                f"Planned task def is missing {len(missing_in_planned)} env var(s) present on current"
                if missing_in_planned
                else None
            ),
        }
    )


if __name__ == "__main__":
    main()
