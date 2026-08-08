#!/usr/bin/env python3
"""Devops onboard: discover AWS layout and write brain + report."""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Prefer sibling devops-aws aws_lib
_HERE = Path(__file__).resolve().parent
_AWS_SCRIPTS = _HERE.parents[1] / "devops-aws" / "scripts"
if _AWS_SCRIPTS.is_dir():
    sys.path.insert(0, str(_AWS_SCRIPTS))
else:
    sys.path.insert(0, str(_HERE))

import aws_lib as od_aws  # noqa: E402


def discover_profiles() -> list[str]:
    names: set[str] = set()
    for path_name in ("config", "credentials"):
        path = Path.home() / ".aws" / path_name
        if not path.is_file():
            continue
        parser = configparser.RawConfigParser()
        parser.read(path)
        for section in parser.sections():
            if section == "default":
                names.add("default")
            elif section.startswith("profile "):
                names.add(section[len("profile ") :].strip())
            else:
                names.add(section.strip())
    preferred = ["dev", "staging", "qa", "prod", "infra", "default"]
    ordered = [p for p in preferred if p in names]
    ordered.extend(sorted(n for n in names if n not in ordered))
    return ordered


def _probe(env: str, label: str, aws_args: list[str], *, region: str, brain: dict) -> dict[str, Any]:
    try:
        data = od_aws.run_aws(env, aws_args, region=region, brain=brain)
        return {"status": "ok", "label": label, "sample": _summarize(label, data)}
    except SystemExit as exc:
        err = str(exc)
        status = "denied" if "AccessDenied" in err or "Unauthorized" in err else "error"
        return {"status": status, "label": label, "error": err[-500:]}


def _summarize(label: str, data: Any) -> Any:
    if data is None:
        return None
    if label == "sts":
        return {
            "account": data.get("Account"),
            "arn": data.get("Arn"),
            "userId": data.get("UserId"),
        }
    if label == "ecs_clusters":
        return (data or {}).get("clusterArns", [])[:20]
    if label == "asg":
        groups = (data or {}).get("AutoScalingGroups") or []
        return [g.get("AutoScalingGroupName") for g in groups[:20]]
    if label == "opensearch":
        return (data or {}).get("DomainNames") or []
    if label == "cloudfront":
        items = ((data or {}).get("DistributionList") or {}).get("Items") or []
        out = []
        for d in items[:15]:
            aliases = ((d.get("Aliases") or {}).get("Items")) or []
            out.append({"id": d.get("Id"), "aliases": aliases[:5]})
        return out
    if label == "ssm_params":
        return [p.get("Name") for p in ((data or {}).get("Parameters") or [])[:30]]
    return "ok"


def cmd_discover(args: argparse.Namespace) -> None:
    profiles = discover_profiles()
    # Temporary brain for auth during discover (do not require prod_profiles yet)
    brain = {
        "version": 1,
        "auth_mode": args.auth_mode,
        "vault_command": args.vault,
        "region_default": args.region,
        "profiles": profiles,
        "prod_profiles": args.prod_profiles or ["__none__"],
    }
    if args.prod_profiles:
        brain["prod_profiles"] = list(args.prod_profiles)

    if od_aws.is_prod_env(args.env, brain) and brain["prod_profiles"] != ["__none__"]:
        if not args.approve_prod:
            raise SystemExit(
                "REFUSED: discovering with a prod-class --env requires chat approval "
                "then --approve-prod."
            )

    region = args.region
    probes = [
        ("sts", ["sts", "get-caller-identity"]),
        ("ecs_clusters", ["ecs", "list-clusters"]),
        ("asg", ["autoscaling", "describe-auto-scaling-groups", "--max-records", "50"]),
        ("opensearch", ["opensearch", "list-domain-names"]),
        ("cloudfront", ["cloudfront", "list-distributions"]),
        (
            "ssm_params",
            [
                "ssm",
                "describe-parameters",
                "--max-results",
                "20",
            ],
        ),
    ]
    capabilities: dict[str, str] = {}
    discovered: dict[str, Any] = {"profiles": profiles, "probes": {}}
    for label, aws_args in probes:
        result = _probe(args.env, label, aws_args, region=region, brain=brain)
        capabilities[label] = result["status"]
        discovered["probes"][label] = result

    out = {
        "env": args.env,
        "auth_mode": args.auth_mode,
        "region": region,
        "capabilities": capabilities,
        "discovered": discovered,
        "hint": "Pass useful fields to `devops_onboard.py write` after user confirmation.",
    }
    od_aws.emit(out)


def _parse_tag(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    if "=" not in value:
        raise SystemExit("--cdn-bucket-tag must be Key=Value")
    key, val = value.split("=", 1)
    return {"key": key, "value": val}


def cmd_write(args: argparse.Namespace) -> None:
    profiles = discover_profiles()
    existing: dict[str, Any] = {}
    if od_aws.brain_path().is_file():
        existing = json.loads(od_aws.brain_path().read_text())

    discover_blob = None
    if args.from_discover:
        discover_blob = json.loads(Path(args.from_discover).read_text())

    prod = list(args.prod_profiles)
    if not prod:
        raise SystemExit("Provide --prod-profiles")
    if prod == ["none"]:
        # Sentinel that never matches a real profile name
        prod = ["__no_prod_profile__"]

    brain: dict[str, Any] = {
        **existing,
        "version": 1,
        "auth_mode": args.auth_mode,
        "vault_command": args.vault,
        "region_default": args.region,
        "profiles": profiles or existing.get("profiles") or [],
        "prod_profiles": prod,
        "ecs": {
            **(existing.get("ecs") or {}),
            "cluster_name_template": args.cluster_template
            or (existing.get("ecs") or {}).get("cluster_name_template"),
            "critical_env_keys": args.critical_env_keys.split(",")
            if args.critical_env_keys
            else (existing.get("ecs") or {}).get("critical_env_keys") or [],
        },
        "cdn": {
            **(existing.get("cdn") or {}),
            "bucket_name": args.cdn_bucket
            if args.cdn_bucket is not None
            else (existing.get("cdn") or {}).get("bucket_name"),
            "bucket_tag": _parse_tag(args.cdn_bucket_tag)
            if args.cdn_bucket_tag
            else (existing.get("cdn") or {}).get("bucket_tag"),
        },
        "opensearch": {
            **(existing.get("opensearch") or {}),
            "domain": args.opensearch_domain
            if args.opensearch_domain is not None
            else (existing.get("opensearch") or {}).get("domain"),
            "endpoint_param": args.opensearch_endpoint_param
            if args.opensearch_endpoint_param is not None
            else (existing.get("opensearch") or {}).get("endpoint_param"),
        },
        "datadog": {
            **(existing.get("datadog") or {}),
            "api_key_param": args.datadog_api_param
            if args.datadog_api_param is not None
            else (existing.get("datadog") or {}).get("api_key_param"),
            "app_key_param": args.datadog_app_param
            if args.datadog_app_param is not None
            else (existing.get("datadog") or {}).get("app_key_param"),
            "site_param": args.datadog_site_param
            if args.datadog_site_param is not None
            else (existing.get("datadog") or {}).get("site_param"),
        },
        "notes": f"Written by devops-onboard at {datetime.now(timezone.utc).isoformat()}",
    }

    if discover_blob:
        brain["capabilities"] = discover_blob.get("capabilities") or {}
        brain["discovered"] = (discover_blob.get("discovered") or {}).get("probes") or discover_blob.get(
            "discovered"
        )
    elif args.env:
        # optional light refresh of capabilities not required
        pass

    if not brain["ecs"].get("cluster_name_template") or "{stack}" not in str(
        brain["ecs"]["cluster_name_template"]
    ):
        raise SystemExit(
            "ecs.cluster_name_template is required and must contain `{stack}` "
            "(pass --cluster-template)."
        )

    path = od_aws.save_brain(brain)
    report = _write_report(brain)
    od_aws.emit({"saved": str(path), "report": str(report), "brain": brain, "readiness": readiness(brain)})


def readiness(brain: dict[str, Any]) -> dict[str, Any]:
    def ok(cond: bool) -> str:
        return "ready" if cond else "blocked"

    ecs_t = (brain.get("ecs") or {}).get("cluster_name_template")
    cdn = brain.get("cdn") or {}
    os_cfg = brain.get("opensearch") or {}
    dd = brain.get("datadog") or {}
    return {
        "ecs_asg": ok(bool(ecs_t) and "{stack}" in str(ecs_t)),
        "cdn": ok(bool(cdn.get("bucket_name") or (cdn.get("bucket_tag") or {}).get("value"))),
        "opensearch": ok(bool(os_cfg.get("domain"))),
        "datadog": ok(bool(dd.get("api_key_param") and dd.get("app_key_param"))),
        "ssm_lambda_generic": "ready",
        "auth": ok(bool(brain.get("auth_mode"))),
    }


def cmd_readiness(_: argparse.Namespace) -> None:
    brain = od_aws.load_brain()
    od_aws.emit({"brain_path": str(od_aws.brain_path()), "readiness": readiness(brain)})


def _write_report(brain: dict[str, Any]) -> Path:
    report_path = od_aws.repo_root() / ".cursor" / "devops" / "ONBOARD_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    ready = readiness(brain)
    lines = [
        "# Devops onboard report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Auth",
        "",
        f"- auth_mode: `{brain.get('auth_mode')}`",
        f"- vault_command: `{brain.get('vault_command')}`",
        f"- region_default: `{brain.get('region_default')}`",
        f"- profiles: {', '.join(brain.get('profiles') or [])}",
        f"- prod_profiles: {', '.join(brain.get('prod_profiles') or [])}",
        "",
        "## Tool readiness",
        "",
    ]
    for k, v in ready.items():
        lines.append(f"- **{k}**: {v}")
    lines.extend(
        [
            "",
            "## Brain keys",
            "",
            "```json",
            json.dumps(
                {
                    "ecs": brain.get("ecs"),
                    "cdn": brain.get("cdn"),
                    "opensearch": brain.get("opensearch"),
                    "datadog": {
                        "api_key_param": (brain.get("datadog") or {}).get("api_key_param"),
                        "app_key_param": (brain.get("datadog") or {}).get("app_key_param"),
                        "site_param": (brain.get("datadog") or {}).get("site_param"),
                    },
                },
                indent=2,
            ),
            "```",
            "",
            "## Capabilities (last discover)",
            "",
            "```json",
            json.dumps(brain.get("capabilities") or {}, indent=2),
            "```",
            "",
            "No secrets are stored in the brain. Re-run `devops_onboard.py discover` after IAM changes.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines))
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_disc = sub.add_parser("discover", help="Probe AWS and print JSON snapshot")
    p_disc.add_argument("--env", required=True)
    p_disc.add_argument("--region", default="us-east-1")
    p_disc.add_argument("--auth-mode", default="aws-vault", choices=["aws-vault", "aws-profile", "env"])
    p_disc.add_argument("--vault", default="aws-vault")
    p_disc.add_argument("--prod-profiles", nargs="*", default=[])
    p_disc.add_argument("--approve-prod", action="store_true")
    p_disc.set_defaults(func=cmd_discover)

    p_write = sub.add_parser("write", help="Write brain.json + ONBOARD_REPORT.md")
    p_write.add_argument("--env", default=None, help="Unused except documentation")
    p_write.add_argument("--region", default="us-east-1")
    p_write.add_argument("--auth-mode", default="aws-vault", choices=["aws-vault", "aws-profile", "env"])
    p_write.add_argument("--vault", default="aws-vault")
    p_write.add_argument("--prod-profiles", nargs="+", required=True)
    p_write.add_argument("--cluster-template", required=True, help="Must include {stack}")
    p_write.add_argument("--critical-env-keys", default=None, help="Comma-separated")
    p_write.add_argument("--cdn-bucket", default=None)
    p_write.add_argument("--cdn-bucket-tag", default=None, help="Key=Value")
    p_write.add_argument("--opensearch-domain", default=None)
    p_write.add_argument("--opensearch-endpoint-param", default=None)
    p_write.add_argument("--datadog-api-param", default=None)
    p_write.add_argument("--datadog-app-param", default=None)
    p_write.add_argument("--datadog-site-param", default=None)
    p_write.add_argument("--from-discover", default=None, help="Path to discover JSON output")
    p_write.set_defaults(func=cmd_write)

    p_ready = sub.add_parser("readiness", help="Show tool readiness from brain")
    p_ready.set_defaults(func=cmd_readiness)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
