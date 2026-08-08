#!/usr/bin/env python3
"""Create a CloudFront invalidation for CDN path(s)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws
import cdn_lib as od_cdn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--url", default=None, help="CDN URL (derives host + one path)")
    parser.add_argument("--host", default=None, help="CDN hostname (with --paths)")
    parser.add_argument(
        "--distribution-id",
        default=None,
        help="CloudFront distribution id (skips alias lookup)",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=None,
        help="Invalidation paths starting with / (e.g. /assets/.../logo.png)",
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()

    paths: list[str] = list(args.paths or [])
    host = args.host
    dist_id = args.distribution_id

    if args.url:
        h, key = od_cdn.parse_target(args.url, None, None)
        host = host or h
        paths.append(od_cdn.cloudfront_path_for_key(key))

    if not paths:
        raise SystemExit("Provide --paths and/or --url")

    normalized = []
    for p in paths:
        if not p.startswith("/"):
            p = "/" + p
        if p not in normalized:
            normalized.append(p)

    if not dist_id:
        if not host:
            raise SystemExit("Provide --host, --url, or --distribution-id")
        dist = od_cdn.find_distribution(args.env, host, region=args.region, brain=brain)
        if not dist or not dist.get("id"):
            raise SystemExit(f"Could not resolve CloudFront distribution for host {host}")
        dist_id = dist["id"]
        aliases = dist.get("aliases")
    else:
        aliases = None

    result = od_aws.run_aws(
        args.env,
        [
            "cloudfront",
            "create-invalidation",
            "--distribution-id",
            dist_id,
            "--paths",
            *normalized,
        ],
        region=args.region,
        brain=brain,
    )

    od_aws.emit(
        {
            "env": args.env,
            "distributionId": dist_id,
            "host": host,
            "aliases": aliases,
            "paths": normalized,
            "invalidation": (result or {}).get("Invalidation"),
        }
    )


if __name__ == "__main__":
    main()
