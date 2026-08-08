#!/usr/bin/env python3
"""OpenSearch domain capacity + optional CloudWatch metric series.

Uses describe-domain + CloudWatch (control plane). Data-plane _cat/indices needs
es:ESHttpGet — see opensearch_indices.py.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws

DEFAULT_METRICS = (
    "ClusterUsedSpace",
    "FreeStorageSpace",
    "SearchableDocuments",
    "CPUUtilization",
    "JVMMemoryPressure",
)


def _gib_from_mib(mib: float | None) -> float | None:
    if mib is None:
        return None
    return round(float(mib) / 1024.0, 3)


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _metric_datapoints(
    env: str,
    account: str,
    metric: str,
    domain_name: str,
    *,
    start: datetime,
    end: datetime,
    period: int,
    region: str | None,
    brain: dict,
) -> list[dict[str, Any]]:
    raw = od_aws.run_aws(
        env,
        [
            "cloudwatch",
            "get-metric-statistics",
            "--namespace",
            "AWS/ES",
            "--metric-name",
            metric,
            "--dimensions",
            f"Name=DomainName,Value={domain_name}",
            f"Name=ClientId,Value={account}",
            "--start-time",
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--end-time",
            end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--period",
            str(period),
            "--statistics",
            "Average",
            "Maximum",
            "Minimum",
        ],
        region=region,
        brain=brain,
    ) or {}
    pts = sorted(raw.get("Datapoints") or [], key=lambda p: p.get("Timestamp") or "")
    out = []
    for p in pts:
        out.append(
            {
                "Timestamp": p.get("Timestamp"),
                "Average": p.get("Average"),
                "Maximum": p.get("Maximum"),
                "Minimum": p.get("Minimum"),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--hours", type=int, default=6, help="Lookback hours when --start/--end omitted")
    parser.add_argument("--start", default=None, help="UTC start ISO8601 (e.g. 2026-07-28T09:30:00Z)")
    parser.add_argument("--end", default=None, help="UTC end ISO8601")
    parser.add_argument(
        "--period",
        type=int,
        default=None,
        help="CloudWatch period seconds (default: 3600, or 900 when --start/--end set)",
    )
    parser.add_argument(
        "--series",
        default=None,
        help="Comma-separated metrics for full series (default: all capacity metrics as latest only; "
        "with --start/--end defaults to CPUUtilization,JVMMemoryPressure)",
    )
    args = parser.parse_args()
    brain = od_aws.load_brain()
    DOMAIN = od_aws.opensearch_domain(brain)

    ident = od_aws.run_aws(args.env, ["sts", "get-caller-identity"], region=args.region, brain=brain) or {}
    account = ident.get("Account")
    if not account:
        raise SystemExit("Could not resolve AWS account id")

    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("Provide both --start and --end")
        start = _parse_utc(args.start)
        end = _parse_utc(args.end)
        period = args.period or 900
        series_names = [
            m.strip()
            for m in (args.series or "CPUUtilization,JVMMemoryPressure").split(",")
            if m.strip()
        ]
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=args.hours)
        period = args.period or 3600
        series_names = [m.strip() for m in args.series.split(",")] if args.series else []

    domain = od_aws.run_aws(
        args.env,
        ["opensearch", "describe-domain", "--domain-name", DOMAIN],
        region=args.region,
        brain=brain,
    ) or {}
    status = domain.get("DomainStatus") or {}
    cc = status.get("ClusterConfig") or {}
    ebs = status.get("EBSOptions") or {}

    instance_count = int(cc.get("InstanceCount") or 0)
    volume_size = int(ebs.get("VolumeSize") or 0)
    raw_disk_gib = instance_count * volume_size
    usable_disk_gib = round(raw_disk_gib * 0.7, 1)

    latest: dict[str, Any] = {}
    for name in DEFAULT_METRICS:
        pts = _metric_datapoints(
            args.env,
            account,
            name,
            DOMAIN,
            start=start,
            end=end,
            period=max(period, 3600) if not args.start else period,
            region=args.region,
            brain=brain,
        )
        # For mixed windows, re-fetch latest with hourly when using incident period
        if args.start:
            pts_latest = _metric_datapoints(
                args.env,
                account,
                name,
                DOMAIN,
                start=end - timedelta(hours=6),
                end=end,
                period=3600,
                region=args.region,
                brain=brain,
            )
            latest[name] = pts_latest[-1] if pts_latest else None
        else:
            latest[name] = pts[-1] if pts else None

    used_mib = (latest.get("ClusterUsedSpace") or {}).get("Average")
    free_mib = (latest.get("FreeStorageSpace") or {}).get("Average")
    docs = (latest.get("SearchableDocuments") or {}).get("Average")
    used_gib = _gib_from_mib(used_mib)
    free_gib = _gib_from_mib(free_mib)

    fill_raw = round(100.0 * used_gib / raw_disk_gib, 1) if used_gib and raw_disk_gib else None
    fill_usable = (
        round(100.0 * used_gib / usable_disk_gib, 1) if used_gib and usable_disk_gib else None
    )
    primary_est_gib = round(used_gib / 2.0, 3) if used_gib else None

    series: dict[str, Any] = {}
    for name in series_names:
        series[name] = _metric_datapoints(
            args.env,
            account,
            name,
            DOMAIN,
            start=start,
            end=end,
            period=period,
            region=args.region,
            brain=brain,
        )

    od_aws.emit(
        {
            "env": args.env,
            "prod_class": od_aws.is_prod_env(args.env, brain),
            "account": account,
            "window": {
                "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "periodSeconds": period,
            },
            "note": (
                "ClusterUsedSpace is total cluster used (MiB→GiB). "
                "FreeStorageSpace is often per-node free, not cluster sum. "
                "Per-index sizes: opensearch_indices.py (needs es:ESHttpGet)."
            ),
            "domain": {
                "name": DOMAIN,
                "endpoint": status.get("Endpoint"),
                "engine": status.get("EngineVersion"),
                "instanceType": cc.get("InstanceType"),
                "instanceCount": instance_count,
                "dedicatedMasterEnabled": cc.get("DedicatedMasterEnabled"),
                "zoneAwarenessEnabled": cc.get("ZoneAwarenessEnabled"),
                "ebs": {
                    "volumeType": ebs.get("VolumeType"),
                    "volumeSizeGiB": volume_size,
                    "iops": ebs.get("Iops"),
                    "throughput": ebs.get("Throughput"),
                },
            },
            "capacity": {
                "rawDiskGiB": raw_disk_gib,
                "usableDiskGiBAt70pct": usable_disk_gib,
                "clusterUsedGiB": used_gib,
                "freeStorageMetricGiB": free_gib,
                "fillPctOfRaw": fill_raw,
                "fillPctOfUsable70": fill_usable,
                "searchableDocuments": int(docs) if docs is not None else None,
                "estimatedPrimaryStoreGiBIf1Replica": primary_est_gib,
            },
            "recentMetrics": {
                k: {
                    "Average": (v or {}).get("Average"),
                    "Maximum": (v or {}).get("Maximum"),
                    "Minimum": (v or {}).get("Minimum"),
                    "Timestamp": (v or {}).get("Timestamp"),
                }
                if v
                else None
                for k, v in latest.items()
            },
            "series": series or None,
        }
    )


if __name__ == "__main__":
    main()
