#!/usr/bin/env python3
"""Summarize recent STOPPED ECS tasks (crash-loop diagnosis)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--stack", required=True)
    parser.add_argument("--service", required=True, help="ECS service name")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    brain = od_aws.load_brain()
    cluster = od_aws.stack_cluster(args.stack, brain)

    stopped = od_aws.run_aws(
        args.env,
        [
            "ecs",
            "list-tasks",
            "--cluster",
            cluster,
            "--service-name",
            args.service,
            "--desired-status",
            "STOPPED",
        ],
        region=args.region,
        brain=brain,
    ) or {}
    arns = (stopped.get("taskArns") or [])[: args.limit]
    running = od_aws.run_aws(
        args.env,
        [
            "ecs",
            "list-tasks",
            "--cluster",
            cluster,
            "--service-name",
            args.service,
            "--desired-status",
            "RUNNING",
        ],
        region=args.region,
        brain=brain,
    ) or {}

    tasks = []
    if arns:
        desc = od_aws.run_aws(
            args.env,
            ["ecs", "describe-tasks", "--cluster", cluster, "--tasks", *arns],
            region=args.region,
            brain=brain,
        )
        for t in desc.get("tasks") or []:
            tasks.append(
                {
                    "id": (t.get("taskArn") or "").rsplit("/", 1)[-1],
                    "taskDef": (t.get("taskDefinitionArn") or "").rsplit("/", 1)[-1],
                    "lastStatus": t.get("lastStatus"),
                    "stopCode": t.get("stopCode"),
                    "stoppedReason": t.get("stoppedReason"),
                    "startedAt": t.get("startedAt"),
                    "stoppedAt": t.get("stoppedAt"),
                    "containers": [
                        {
                            "name": c.get("name"),
                            "exit": c.get("exitCode"),
                            "reason": c.get("reason"),
                            "status": c.get("lastStatus"),
                        }
                        for c in t.get("containers") or []
                    ],
                }
            )
        tasks.sort(key=lambda x: x.get("stoppedAt") or "", reverse=True)

    od_aws.emit(
        {
            "env": args.env,
            "cluster": cluster,
            "service": args.service,
            "runningTaskCount": len(running.get("taskArns") or []),
            "stoppedSampleCount": len(tasks),
            "stoppedTasks": tasks,
        }
    )


if __name__ == "__main__":
    main()
