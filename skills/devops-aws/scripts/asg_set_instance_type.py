#!/usr/bin/env python3
"""Set an ASG's EC2 instance type via a new launch configuration + optional refresh.

For stacks that still use classic Launch Configurations (not Launch Templates).
Clones the current LC with a new InstanceType, points the ASG at it, then
optionally starts an instance refresh so running hosts are replaced.

Example:
  python3 asg_set_instance_type.py --env qa --stack frontend-disco \\
    --instance-type t3.medium --refresh \\
    --explain "Bump hosts so Datadog agent + app fit (1900+256 > t2.small)"
"""

from __future__ import annotations

import argparse
import copy
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


# Keys accepted by create-launch-configuration (subset of describe output).
_LC_CREATE_KEYS = (
    "ImageId",
    "KeyName",
    "SecurityGroups",
    "ClassicLinkVPCId",
    "ClassicLinkVPCSecurityGroups",
    "UserData",
    "InstanceType",
    "InstanceMonitoring",
    "SpotPrice",
    "IamInstanceProfile",
    "EbsOptimized",
    "AssociatePublicIpAddress",
    "PlacementTenancy",
    "MetadataOptions",
)


def _bool_cli(flag: str, value: bool | None) -> list[str]:
    if value is None:
        return []
    return [flag] if value else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--stack", required=True, help="Stack name, e.g. frontend-disco")
    parser.add_argument("--instance-type", required=True, help="e.g. t3.medium")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Start ASG instance refresh and wait for completion",
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()
    region = args.region or od_aws.region_for(brain)
    asg_name = f"{args.stack}-AutoscalingGroup"

    groups = od_aws.run_aws(
        args.env,
        ["autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", asg_name],
        region=region,
        brain=brain,
    )
    ag = (groups.get("AutoScalingGroups") or [None])[0]
    if not ag:
        raise SystemExit(f"ASG not found: {asg_name}")
    if ag.get("LaunchTemplate") or (ag.get("MixedInstancesPolicy") or {}).get("LaunchTemplate"):
        raise SystemExit(
            f"{asg_name} uses a Launch Template; this tool only handles Launch Configurations."
        )
    old_lc_name = ag.get("LaunchConfigurationName")
    if not old_lc_name:
        raise SystemExit(f"{asg_name} has no LaunchConfigurationName")

    lc_desc = od_aws.run_aws(
        args.env,
        ["autoscaling", "describe-launch-configurations", "--launch-configuration-names", old_lc_name],
        region=region,
        brain=brain,
    )
    old_lc = (lc_desc.get("LaunchConfigurations") or [None])[0]
    if not old_lc:
        raise SystemExit(f"Launch configuration not found: {old_lc_name}")

    old_type = old_lc.get("InstanceType")
    if old_type == args.instance_type:
        result = {
            "env": args.env,
            "asg": asg_name,
            "launchConfiguration": old_lc_name,
            "instanceType": old_type,
            "changed": False,
            "explanation": args.explain,
        }
        if args.refresh:
            result["instanceRefresh"] = _refresh(args.env, asg_name, region, brain)
        od_aws.emit(result)
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    new_lc_name = f"{args.stack}-lc-{args.instance_type.replace('.', '-')}-{stamp}"

    create_cmd = [
        "autoscaling",
        "create-launch-configuration",
        "--launch-configuration-name",
        new_lc_name,
        "--instance-type",
        args.instance_type,
    ]
    if old_lc.get("ImageId"):
        create_cmd.extend(["--image-id", old_lc["ImageId"]])
    if old_lc.get("KeyName"):
        create_cmd.extend(["--key-name", old_lc["KeyName"]])
    if old_lc.get("SecurityGroups"):
        create_cmd.extend(["--security-groups", *old_lc["SecurityGroups"]])
    if old_lc.get("UserData"):
        # describe returns base64 UserData; create expects base64 with this flag path via file is awkward —
        # AWS CLI accepts --user-data as plain or base64; pass via file:// from temp.
        import base64
        import tempfile

        raw = old_lc["UserData"]
        try:
            decoded = base64.b64decode(raw)
        except Exception:
            decoded = raw.encode() if isinstance(raw, str) else raw
        with tempfile.NamedTemporaryFile(delete=False, suffix="-userdata") as fh:
            fh.write(decoded)
            ud_path = fh.name
        create_cmd.extend(["--user-data", f"file://{ud_path}"])
    if old_lc.get("IamInstanceProfile"):
        create_cmd.extend(["--iam-instance-profile", old_lc["IamInstanceProfile"]])
    mon = (old_lc.get("InstanceMonitoring") or {}).get("Enabled")
    if mon is True:
        create_cmd.append("--instance-monitoring")
    elif mon is False:
        create_cmd.append("--no-instance-monitoring")
    if old_lc.get("EbsOptimized") is True:
        create_cmd.append("--ebs-optimized")
    elif old_lc.get("EbsOptimized") is False:
        create_cmd.append("--no-ebs-optimized")
    if old_lc.get("AssociatePublicIpAddress") is True:
        create_cmd.append("--associate-public-ip-address")
    elif old_lc.get("AssociatePublicIpAddress") is False:
        create_cmd.append("--no-associate-public-ip-address")
    # Block device mappings
    bdms = old_lc.get("BlockDeviceMappings")
    if bdms:
        import json as _json

        # Strip read-only / ebs null noise AWS rejects
        cleaned = []
        for bdm in bdms:
            item = {k: v for k, v in bdm.items() if v is not None}
            if "Ebs" in item and isinstance(item["Ebs"], dict):
                item["Ebs"] = {k: v for k, v in item["Ebs"].items() if v is not None}
            cleaned.append(item)
        create_cmd.extend(["--block-device-mappings", _json.dumps(cleaned)])

    od_aws.run_aws(args.env, create_cmd, region=region, brain=brain)

    od_aws.run_aws(
        args.env,
        [
            "autoscaling",
            "update-auto-scaling-group",
            "--auto-scaling-group-name",
            asg_name,
            "--launch-configuration-name",
            new_lc_name,
        ],
        region=region,
        brain=brain,
    )

    result = {
        "env": args.env,
        "asg": asg_name,
        "mutation": "asg.set-instance-type",
        "before": {"launchConfiguration": old_lc_name, "instanceType": old_type},
        "after": {"launchConfiguration": new_lc_name, "instanceType": args.instance_type},
        "changed": True,
        "explanation": args.explain,
    }
    if args.refresh:
        result["instanceRefresh"] = _refresh(args.env, asg_name, region, brain)
    od_aws.emit(result)
    return 0


def _refresh(env: str, asg: str, region: str, brain: dict) -> dict:
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
    return {"refreshId": refresh_id, "refresh": last}


if __name__ == "__main__":
    raise SystemExit(main())
