#!/usr/bin/env python3
"""Delete an ECS service (usually after desired=0).

Some deploy systems keep the *previous* release service at desired=0 for rollback (n+1
pattern). Do not delete that service unless the user explicitly confirms they
no longer need rollback to that version — see devops-aws SKILL.md §5b.
"""

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
        "--force",
        action="store_true",
        help="Pass --force to aws ecs delete-service",
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
    if (b0.get("desiredCount") or 0) != 0 and not args.force:
        raise SystemExit(
            f"REFUSED: service desiredCount={b0.get('desiredCount')} (scale to 0 first, or pass --force)"
        )

    cmd = ["ecs", "delete-service", "--cluster", cluster, "--service", args.service]
    if args.force:
        cmd.append("--force")
    result = od_aws.run_aws(args.env, cmd, region=args.region, brain=brain)
    s = result.get("service") or {}

    od_aws.emit(
        {
            "env": args.env,
            "mutation": "ecs.delete-service",
            "explanation": args.explain,
            "before": {
                "desired": b0.get("desiredCount"),
                "running": b0.get("runningCount"),
                "status": b0.get("status"),
            },
            "after": {"status": s.get("status")},
        }
    )


if __name__ == "__main__":
    main()
