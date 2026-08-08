#!/usr/bin/env python3
"""Cluster instance capacity + matching ASG snapshot."""

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
    args = parser.parse_args()
    brain = od_aws.load_brain()
    cluster = od_aws.stack_cluster(args.stack, brain)
    asg_name = f"{args.stack}-AutoscalingGroup"

    listed = od_aws.run_aws(
        args.env,
        ["ecs", "list-container-instances", "--cluster", cluster],
        region=args.region,
        brain=brain,
    ) or {}
    arns = listed.get("containerInstanceArns") or []
    instances = []
    if arns:
        desc = od_aws.run_aws(
            args.env,
            ["ecs", "describe-container-instances", "--cluster", cluster, "--container-instances", *arns],
            region=args.region,
            brain=brain,
        )
        for ci in desc.get("containerInstances") or []:
            remaining = {r["name"]: r.get("integerValue") for r in ci.get("remainingResources") or []}
            instances.append(
                {
                    "ec2": ci.get("ec2InstanceId"),
                    "status": ci.get("status"),
                    "agentConnected": ci.get("agentConnected"),
                    "runningTasks": ci.get("runningTasksCount"),
                    "pendingTasks": ci.get("pendingTasksCount"),
                    "cpuFree": remaining.get("CPU"),
                    "memFree": remaining.get("MEMORY"),
                }
            )

    asg = None
    try:
        asg_desc = od_aws.run_aws(
            args.env,
            ["autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", asg_name],
            region=args.region,
            brain=brain,
        )
        groups = asg_desc.get("AutoScalingGroups") or []
        if groups:
            g = groups[0]
            instances_meta = g.get("Instances") or []
            asg = {
                "name": g.get("AutoScalingGroupName"),
                "desired": g.get("DesiredCapacity"),
                "min": g.get("MinSize"),
                "max": g.get("MaxSize"),
                "totalInstances": len(instances_meta),
                "inService": sum(1 for i in instances_meta if i.get("LifecycleState") == "InService"),
            }
    except SystemExit as exc:
        asg = {"name": asg_name, "error": str(exc)}

    od_aws.emit(
        {
            "env": args.env,
            "cluster": cluster,
            "instanceCount": len(instances),
            "agentsOk": sum(1 for i in instances if i.get("agentConnected")),
            "emptyHosts": sum(
                1
                for i in instances
                if (i.get("runningTasks") or 0) == 0 and (i.get("pendingTasks") or 0) == 0
            ),
            "instances": instances,
            "asg": asg,
        }
    )


if __name__ == "__main__":
    main()
