#!/usr/bin/env python3
"""Query Datadog logs (v2 events search). Credentials from brain datadog.*_param or DD_* env."""

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


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _simplify_event(ev: dict[str, Any]) -> dict[str, Any]:
    attrs = ev.get("attributes") or {}
    return {
        "id": ev.get("id"),
        "timestamp": attrs.get("timestamp"),
        "service": attrs.get("service"),
        "host": attrs.get("host"),
        "status": attrs.get("status"),
        "message": attrs.get("message"),
        "tags": attrs.get("tags"),
        "attributes": attrs.get("attributes"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument(
        "--query",
        default="*",
        help='Datadog log query (e.g. service:my-service status:error)',
    )
    parser.add_argument("--hours", type=int, default=1, help="Lookback hours if --from/--to omitted")
    parser.add_argument("--from", dest="time_from", default=None, help="UTC start ISO8601")
    parser.add_argument("--to", dest="time_to", default=None, help="UTC end ISO8601")
    parser.add_argument("--limit", type=int, default=50, help="Max events (1-1000)")
    parser.add_argument(
        "--sort",
        default="-timestamp",
        choices=["timestamp", "-timestamp"],
        help="Sort order",
    )
    parser.add_argument("--cursor", default=None, help="Pagination cursor from prior page")
    parser.add_argument("--api-key-param", default=None)
    parser.add_argument("--app-key-param", default=None)
    parser.add_argument("--site-param", default=None)
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Include raw Datadog response body",
    )
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
        start = _parse_utc(args.time_from) if args.time_from else None
        end = _parse_utc(args.time_to) if args.time_to else None
        if start is None or end is None:
            raise SystemExit("Provide both --from and --to, or use --hours")
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=args.hours)

    limit = max(1, min(int(args.limit), 1000))
    body: dict[str, Any] = {
        "filter": {
            "query": args.query,
            "from": _iso_z(start),
            "to": _iso_z(end),
        },
        "sort": args.sort,
        "page": {"limit": limit},
    }
    if args.cursor:
        body["page"]["cursor"] = args.cursor

    resp = od_datadog.request(creds, "POST", "/api/v2/logs/events/search", body=body)
    payload = resp["body"] or {}
    events = [_simplify_event(e) for e in (payload.get("data") or [])]
    meta = payload.get("meta") or {}
    page = meta.get("page") or {}

    out: dict[str, Any] = {
        "env": args.env,
        "prod_class": od_aws.is_prod_env(args.env, brain),
        "credentials": od_datadog.credentials_meta(creds),
        "request": {
            "query": args.query,
            "from": _iso_z(start),
            "to": _iso_z(end),
            "limit": limit,
            "sort": args.sort,
        },
        "count": len(events),
        "events": events,
        "nextCursor": page.get("after"),
        "elapsedMs": meta.get("elapsed"),
        "status": meta.get("status"),
    }
    if args.raw:
        out["raw"] = payload
    od_aws.emit(out)


if __name__ == "__main__":
    main()
