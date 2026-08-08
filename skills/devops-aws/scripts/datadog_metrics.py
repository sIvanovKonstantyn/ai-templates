#!/usr/bin/env python3
"""Query Datadog metrics (v1 timeseries). Credentials from brain datadog.*_param or DD_* env."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws
import datadog_lib as od_datadog


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument(
        "--query",
        required=True,
        help='Metric query, e.g. avg:aws.es.cpuutilization{domainname:YOUR_DOMAIN}',
    )
    parser.add_argument("--hours", type=int, default=6, help="Lookback hours if --from/--to omitted")
    parser.add_argument("--from", dest="time_from", default=None, help="UTC start ISO8601")
    parser.add_argument("--to", dest="time_to", default=None, help="UTC end ISO8601")
    parser.add_argument("--api-key-param", default=None)
    parser.add_argument("--app-key-param", default=None)
    parser.add_argument("--site-param", default=None)
    parser.add_argument("--raw", action="store_true", help="Include raw Datadog response")
    args = parser.parse_args()

    brain = od_aws.load_brain()
    creds = od_datadog.resolve_credentials(
        args.env,
        region=args.region,
        brain=brain,
        api_key_param=args.api_key_param,
        app_key_param=args.app_key_param,
        site_param=args.site_param,
    )

    if args.time_from or args.time_to:
        if not args.time_from or not args.time_to:
            raise SystemExit("Provide both --from and --to, or use --hours")
        start = _parse_utc(args.time_from)
        end = _parse_utc(args.time_to)
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=args.hours)

    from_epoch = int(start.timestamp())
    to_epoch = int(end.timestamp())

    resp = od_datadog.request(
        creds,
        "GET",
        "/api/v1/query",
        query={"from": from_epoch, "to": to_epoch, "query": args.query},
    )
    payload = resp["body"] or {}
    series_out = []
    for s in payload.get("series") or []:
        points = []
        for pt in s.get("pointlist") or []:
            if not pt or len(pt) < 2:
                continue
            ts_ms, value = pt[0], pt[1]
            points.append(
                {
                    "timestampMs": ts_ms,
                    "timestamp": datetime.fromtimestamp(
                        float(ts_ms) / 1000.0, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "value": value,
                }
            )
        series_out.append(
            {
                "metric": s.get("metric"),
                "displayName": s.get("display_name"),
                "scope": s.get("scope"),
                "unit": (s.get("unit") or [None])[0] if s.get("unit") else None,
                "interval": s.get("interval"),
                "pointCount": len(points),
                "points": points,
            }
        )

    out: dict[str, Any] = {
        "env": args.env,
        "prod_class": od_aws.is_prod_env(args.env, brain),
        "credentials": od_datadog.credentials_meta(creds),
        "request": {
            "query": args.query,
            "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fromEpoch": from_epoch,
            "toEpoch": to_epoch,
        },
        "status": payload.get("status"),
        "seriesCount": len(series_out),
        "series": series_out,
        "error": payload.get("error"),
        "message": payload.get("message"),
    }
    if args.raw:
        out["raw"] = payload
    od_aws.emit(out)


if __name__ == "__main__":
    main()
