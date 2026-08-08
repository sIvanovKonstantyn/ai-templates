#!/usr/bin/env python3
"""Apply (or plan) a service's deploy/aws/<env> Terraform stack.

Used for QA capacity bumps (e.g. instance_type for Datadog sidecars) when CI
only applies on master. Optional ASG instance refresh after apply — launch
config / LT changes do not replace running EC2s by themselves.

Examples:
  python3 tf_apply.py --env qa --service frontend-disco --plan-only \\
    --explain "Preview t2.small -> t3.medium for Datadog memory"
  python3 tf_apply.py --env qa --service frontend-disco --auto-approve \\
    --refresh-asg --explain "Apply t3.medium + refresh ASG for Datadog sidecars"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _service_tf_dir(service: str, env: str) -> Path:
    root = od_aws.repo_root()
    # Prefer nested service repo layout: <root>/<service>/deploy/aws/<env>
    candidates = [
        root / service / "deploy" / "aws" / env,
        root / "deploy" / "aws" / env,  # unlikely monorepo root
    ]
    for path in candidates:
        if (path / "qa.tf").is_file() or (path / f"{env}.tf").is_file() or list(path.glob("*.tf")):
            if path.is_dir() and any(path.glob("*.tf")):
                return path
    raise SystemExit(
        f"No terraform dir for service={service!r} env={env!r}. Tried:\n"
        + "\n".join(f"  - {c}" for c in candidates)
    )


def _terraform_env(env: str, region: str, brain: dict) -> dict[str, str]:
    """Env for terraform subprocess (profile fallback when vault has no creds)."""
    out = os.environ.copy()
    out["AWS_PROFILE"] = env
    out["AWS_REGION"] = region
    out["AWS_DEFAULT_REGION"] = region
    # Keep TF state/modules outside workspace when possible (sandbox .git/hooks).
    out.setdefault("TF_DATA_DIR", f"/tmp/cursor-tfdata-{env}-{os.getpid()}")
    # Prefer HTTPS for github.com module sources when a token is available via
    # the ambient git credential helper (set by caller or CI).
    return out


def _run_tf(tf_dir: Path, args: list[str], env: dict[str, str]) -> int:
    cmd = ["terraform", *args]
    print(f"cwd: {tf_dir}", file=sys.stderr)
    print(f"cmd: {' '.join(cmd)}", file=sys.stderr)
    print(f"TF_DATA_DIR={env.get('TF_DATA_DIR')}", file=sys.stderr)
    proc = subprocess.run(cmd, cwd=tf_dir, env=env)
    return proc.returncode


def _refresh_asg(env: str, stack: str, region: str, brain: dict) -> dict:
    asg = f"{stack}-AutoscalingGroup"
    started = od_aws.run_aws(
        env,
        [
            "autoscaling",
            "start-instance-refresh",
            "--auto-scaling-group-name",
            asg,
            "--preferences",
            "MinHealthyPercentage=50,InstanceWarmup=90",
        ],
        region=region,
        brain=brain,
    )
    refresh_id = (started or {}).get("InstanceRefreshId")
    # Poll up to ~15 minutes
    deadline = time.time() + 900
    last: dict = {}
    while time.time() < deadline:
        desc = od_aws.run_aws(
            env,
            [
                "autoscaling",
                "describe-instance-refreshes",
                "--auto-scaling-group-name",
                asg,
                "--instance-refresh-ids",
                refresh_id,
            ],
            region=region,
            brain=brain,
        )
        items = (desc or {}).get("InstanceRefreshes") or []
        last = items[0] if items else {}
        status = last.get("Status")
        print(f"instance-refresh {refresh_id}: {status}", file=sys.stderr)
        if status in {"Successful", "Failed", "Cancelled", "RollbackSuccessful", "RollbackFailed"}:
            break
        time.sleep(20)
    return {"asg": asg, "refreshId": refresh_id, "refresh": last}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument(
        "--service",
        required=True,
        help="Service directory name under workspace root (e.g. frontend-disco)",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="terraform plan instead of apply",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Pass -auto-approve to terraform apply",
    )
    parser.add_argument(
        "--refresh-asg",
        action="store_true",
        help="After apply, start ASG instance refresh and wait for completion",
    )
    parser.add_argument(
        "--stack",
        default=None,
        help="ASG stack name (default: --service). Used with --refresh-asg",
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()
    region = args.region or od_aws.region_for(brain)
    tf_dir = _service_tf_dir(args.service, args.env)
    env = _terraform_env(args.env, region, brain)
    Path(env["TF_DATA_DIR"]).mkdir(parents=True, exist_ok=True)

    # Init (modules + backend)
    rc = _run_tf(tf_dir, ["init", "-input=false", "-no-color"], env)
    if rc != 0:
        return rc

    if args.plan_only:
        rc = _run_tf(tf_dir, ["plan", "-input=false", "-no-color"], env)
        od_aws.emit(
            {
                "env": args.env,
                "service": args.service,
                "tf_dir": str(tf_dir),
                "action": "plan",
                "exit": rc,
                "explanation": args.explain,
            }
        )
        return rc

    apply_args = ["apply", "-input=false", "-no-color"]
    if args.auto_approve:
        apply_args.append("-auto-approve")
    rc = _run_tf(tf_dir, apply_args, env)
    result: dict = {
        "env": args.env,
        "service": args.service,
        "tf_dir": str(tf_dir),
        "action": "apply",
        "exit": rc,
        "explanation": args.explain,
    }
    if rc != 0:
        od_aws.emit(result)
        return rc

    if args.refresh_asg:
        stack = args.stack or args.service
        result["instanceRefresh"] = _refresh_asg(args.env, stack, region, brain)

    od_aws.emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
