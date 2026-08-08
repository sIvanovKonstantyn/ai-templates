#!/usr/bin/env python3
"""Application Auto Scaling targets/policies for an ECS service."""

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
    parser.add_argument("--service", required=True)
    args = parser.parse_args()
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
    policies = od_aws.run_aws(
        args.env,
        [
            "application-autoscaling",
            "describe-scaling-policies",
            "--service-namespace",
            "ecs",
            "--resource-id",
            resource_id,
        ],
        region=args.region,
        brain=brain,
    )

    od_aws.emit(
        {
            "env": args.env,
            "resourceId": resource_id,
            "targets": [
                {
                    "min": t.get("MinCapacity"),
                    "max": t.get("MaxCapacity"),
                    "suspended": t.get("SuspendedState"),
                    "dimension": t.get("ScalableDimension"),
                }
                for t in targets.get("ScalableTargets") or []
            ],
            "policies": [
                {
                    "name": p.get("PolicyName"),
                    "type": p.get("PolicyType"),
                    "targetValue": (
                        (p.get("TargetTrackingScalingPolicyConfiguration") or {}).get("TargetValue")
                    ),
                }
                for p in policies.get("ScalingPolicies") or []
            ],
        }
    )


if __name__ == "__main__":
    main()
