#!/usr/bin/env python3
"""Update ASG desired/min/max for a stack."""

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
    parser.add_argument("--desired", type=int, default=None)
    parser.add_argument("--min", type=int, default=None)
    parser.add_argument("--max", type=int, default=None)
    args = parser.parse_args()

    if args.desired is None and args.min is None and args.max is None:
        raise SystemExit("Pass at least one of --desired/--min/--max")

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()
    asg_name = f"{args.stack}-AutoscalingGroup"

    before = od_aws.run_aws(
        args.env,
        ["autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", asg_name],
        region=args.region,
        brain=brain,
    )
    g0 = (before.get("AutoScalingGroups") or [{}])[0]

    cmd = ["autoscaling", "update-auto-scaling-group", "--auto-scaling-group-name", asg_name]
    if args.desired is not None:
        cmd.extend(["--desired-capacity", str(args.desired)])
    if args.min is not None:
        cmd.extend(["--min-size", str(args.min)])
    if args.max is not None:
        cmd.extend(["--max-size", str(args.max)])

    od_aws.run_aws(args.env, cmd, region=args.region, brain=brain)

    after = od_aws.run_aws(
        args.env,
        ["autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", asg_name],
        region=args.region,
        brain=brain,
    )
    g1 = (after.get("AutoScalingGroups") or [{}])[0]

    def snap(g: dict) -> dict:
        inst = g.get("Instances") or []
        return {
            "desired": g.get("DesiredCapacity"),
            "min": g.get("MinSize"),
            "max": g.get("MaxSize"),
            "inService": sum(1 for i in inst if i.get("LifecycleState") == "InService"),
            "total": len(inst),
        }

    od_aws.emit(
        {
            "env": args.env,
            "mutation": "autoscaling.update-auto-scaling-group",
            "asg": asg_name,
            "explanation": args.explain,
            "before": snap(g0),
            "after": snap(g1),
        }
    )


if __name__ == "__main__":
    main()
