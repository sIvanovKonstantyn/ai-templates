#!/usr/bin/env python3
"""Set or clear ASG scale-in protection on EC2 instances in a stack cluster.

Use before shrinking an ASG when hosts are full (one large task per instance):
unprotected scale-in often terminates task hosts and drops running count to 0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _container_instances(env: str, cluster: str, *, region: str | None, brain: dict[str, Any]) -> list[dict[str, Any]]:
    listed = od_aws.run_aws(
        env,
        ["ecs", "list-container-instances", "--cluster", cluster],
        region=region,
        brain=brain,
    ) or {}
    arns = listed.get("containerInstanceArns") or []
    if not arns:
        return []
    described = od_aws.run_aws(
        env,
        ["ecs", "describe-container-instances", "--cluster", cluster, "--container-instances", *arns],
        region=region,
        brain=brain,
    ) or {}
    return described.get("containerInstances") or []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--stack", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=["protect-busy", "unprotect-all"],
        help="protect-busy: protect EC2 instances with running ECS tasks; "
        "unprotect-all: clear protection on every registered instance",
    )
    args = parser.parse_args()
    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()

    cluster = od_aws.stack_cluster(args.stack, brain)
    asg = f"{args.stack}-AutoscalingGroup"
    instances = _container_instances(args.env, cluster, region=args.region, brain=brain)

    if args.mode == "protect-busy":
        targets = [
            i["ec2InstanceId"]
            for i in instances
            if (i.get("runningTasksCount") or 0) > 0 and i.get("ec2InstanceId")
        ]
        protected = True
    else:
        targets = [i["ec2InstanceId"] for i in instances if i.get("ec2InstanceId")]
        protected = False

    if not targets:
        od_aws.emit(
            {
                "env": args.env,
                "asg": asg,
                "mode": args.mode,
                "changed": False,
                "instanceIds": [],
                "mutation_explanation": args.explain,
            }
        )
        return

    od_aws.run_aws(
        args.env,
        [
            "autoscaling",
            "set-instance-protection",
            "--auto-scaling-group-name",
            asg,
            "--instance-ids",
            *targets,
            "--protected-from-scale-in" if protected else "--no-protected-from-scale-in",
        ],
        region=args.region,
        brain=brain,
    )

    od_aws.emit(
        {
            "env": args.env,
            "asg": asg,
            "mode": args.mode,
            "changed": True,
            "protectedFromScaleIn": protected,
            "instanceIds": targets,
            "mutation_explanation": args.explain,
        }
    )


if __name__ == "__main__":
    main()
