#!/usr/bin/env python3
"""Check an ECS task definition for critical app env vars (read-only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def env_map(task_def: dict, app_name: str) -> dict[str, str]:
    for c in task_def.get("containerDefinitions") or []:
        if c.get("name") == app_name:
            return {e["name"]: e.get("value") or "" for e in c.get("environment") or []}
    raise SystemExit(f"App container {app_name!r} not found in task definition")


def image_for(task_def: dict, app_name: str) -> str | None:
    for c in task_def.get("containerDefinitions") or []:
        if c.get("name") == app_name:
            return c.get("image")
    return None


def validate_env_map(env: dict[str, str], *, critical: list[str], min_count: int) -> dict:
    missing = [k for k in critical if not (env.get(k) or "").strip()]
    count = len(env)
    return {
        "ok": not missing and count >= min_count,
        "envCount": count,
        "minEnvCount": min_count,
        "criticalKeys": critical,
        "missingCritical": missing,
        "belowMinCount": count < min_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--app", required=True, help="App container / family name")
    parser.add_argument(
        "--task-definition",
        required=True,
        help="Task def family, family:rev, or ARN",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Optional healthy task def to compare (reports keys missing vs baseline)",
    )
    parser.add_argument(
        "--min-env-count",
        type=int,
        default=0,
        help="Minimum app env var count (default 0; override or set via brain)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when validation fails",
    )
    args = parser.parse_args()
    brain = od_aws.load_brain()
    critical = od_aws.critical_env_keys(brain)
    min_count = args.min_env_count
    if min_count == 0:
        configured = (brain.get("ecs") or {}).get("min_env_count")
        if isinstance(configured, int):
            min_count = configured

    td = od_aws.run_aws(
        args.env,
        ["ecs", "describe-task-definition", "--task-definition", args.task_definition],
        region=args.region,
        brain=brain,
    )["taskDefinition"]
    env = env_map(td, args.app)
    validation = validate_env_map(env, critical=critical, min_count=min_count)

    result = {
        "env": args.env,
        "app": args.app,
        "taskDef": f"{td.get('family')}:{td.get('revision')}",
        "image": image_for(td, args.app),
        "validation": validation,
        "sampleNames": sorted(env)[:25],
    }

    if args.baseline:
        base = od_aws.run_aws(
            args.env,
            ["ecs", "describe-task-definition", "--task-definition", args.baseline],
            region=args.region,
            brain=brain,
        )["taskDefinition"]
        base_env = env_map(base, args.app)
        result["missingVsBaseline"] = sorted(k for k in base_env if k not in env)
        result["baselineTaskDef"] = f"{base.get('family')}:{base.get('revision')}"

    od_aws.emit(result)
    if args.strict and not validation["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
