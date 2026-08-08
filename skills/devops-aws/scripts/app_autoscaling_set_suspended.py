#!/usr/bin/env python3
"""Suspend or resume ECS service Application Auto Scaling."""

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
    parser.add_argument(
        "--mode",
        required=True,
        choices=["suspend", "resume"],
        help="suspend = freeze dynamic scaling; resume = allow it",
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()
    cluster = od_aws.stack_cluster(args.stack, brain)
    resource_id = f"service/{cluster}/{args.service}"

    targets = od_aws.run_aws(
        args.env,
        [
            "application-autoscaling",
            "describe-scalable-targets",
            "--service-namespace",
            "ecs",
            "--resource-ids",
            resource_id,
        ],
        region=args.region,
        brain=brain,
    )
    tlist = targets.get("ScalableTargets") or []
    if not tlist:
        raise SystemExit(f"No scalable target for {resource_id}")
    t0 = tlist[0]
    suspended = args.mode == "suspend"

    od_aws.run_aws(
        args.env,
        [
            "application-autoscaling",
            "register-scalable-target",
            "--service-namespace",
            "ecs",
            "--scalable-dimension",
            "ecs:service:DesiredCount",
            "--resource-id",
            resource_id,
            "--min-capacity",
            str(t0["MinCapacity"]),
            "--max-capacity",
            str(t0["MaxCapacity"]),
            "--suspended-state",
            (
                f"DynamicScalingInSuspended={str(suspended).lower()},"
                f"DynamicScalingOutSuspended={str(suspended).lower()},"
                f"ScheduledScalingSuspended={str(suspended).lower()}"
            ),
        ],
        region=args.region,
        brain=brain,
    )

    after = od_aws.run_aws(
        args.env,
        [
            "application-autoscaling",
            "describe-scalable-targets",
            "--service-namespace",
            "ecs",
            "--resource-ids",
            resource_id,
        ],
        region=args.region,
        brain=brain,
    )

    od_aws.emit(
        {
            "env": args.env,
            "mutation": "application-autoscaling.register-scalable-target",
            "resourceId": resource_id,
            "mode": args.mode,
            "explanation": args.explain,
            "before": {"min": t0.get("MinCapacity"), "max": t0.get("MaxCapacity"), "suspended": t0.get("SuspendedState")},
            "after": {
                "min": (after.get("ScalableTargets") or [{}])[0].get("MinCapacity"),
                "max": (after.get("ScalableTargets") or [{}])[0].get("MaxCapacity"),
                "suspended": (after.get("ScalableTargets") or [{}])[0].get("SuspendedState"),
            },
        }
    )


if __name__ == "__main__":
    main()
