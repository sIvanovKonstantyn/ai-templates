#!/usr/bin/env python3
"""Update an ECS service (desired count, task def, deploy config, force deploy)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--stack", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--desired-count", type=int, default=None)
    parser.add_argument("--task-definition", default=None)
    parser.add_argument("--force-new-deployment", action="store_true")
    parser.add_argument(
        "--deployment-configuration",
        default=None,
        help='e.g. maximumPercent=200,minimumHealthyPercent=100',
    )
    parser.add_argument(
        "--az-rebalancing",
        choices=["ENABLED", "DISABLED"],
        default=None,
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()
    cluster = od_aws.stack_cluster(args.stack, brain)

    before = od_aws.run_aws(
        args.env,
        ["ecs", "describe-services", "--cluster", cluster, "--services", args.service],
        region=args.region,
        brain=brain,
    )
    b0 = (before.get("services") or [{}])[0]

    cmd = ["ecs", "update-service", "--cluster", cluster, "--service", args.service]
    if args.desired_count is not None:
        cmd.extend(["--desired-count", str(args.desired_count)])
    if args.task_definition:
        cmd.extend(["--task-definition", args.task_definition])
    if args.force_new_deployment:
        cmd.append("--force-new-deployment")
    if args.deployment_configuration:
        cmd.extend(["--deployment-configuration", args.deployment_configuration])
    if args.az_rebalancing:
        cmd.extend(["--availability-zone-rebalancing", args.az_rebalancing])

    if len(cmd) == 6:
        raise SystemExit("Nothing to update: pass at least one mutation flag")

    result = od_aws.run_aws(args.env, cmd, region=args.region, brain=brain)
    s = (result.get("service") or {})

    od_aws.emit(
        {
            "env": args.env,
            "mutation": "ecs.update-service",
            "explanation": args.explain,
            "before": {
                "desired": b0.get("desiredCount"),
                "running": b0.get("runningCount"),
                "pending": b0.get("pendingCount"),
                "taskDef": (b0.get("taskDefinition") or "").rsplit("/", 1)[-1],
            },
            "after": {
                "desired": s.get("desiredCount"),
                "running": s.get("runningCount"),
                "pending": s.get("pendingCount"),
                "taskDef": (s.get("taskDefinition") or "").rsplit("/", 1)[-1],
                "status": s.get("status"),
            },
        }
    )


if __name__ == "__main__":
    main()
