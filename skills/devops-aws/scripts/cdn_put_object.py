#!/usr/bin/env python3
"""Upload/replace an object in CDN origin bucket (from brain)."""

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
    parser.add_argument("--url", default=None, help="Full CDN URL (host + key)")
    parser.add_argument("--host", default=None)
    parser.add_argument("--key", default=None)
    parser.add_argument("--file", required=True, help="Local file to upload")
    parser.add_argument(
        "--content-type",
        default=None,
        help="Content-Type (default: guess from file extension)",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Override S3 bucket (default: brain cdn.*)",
    )
    parser.add_argument(
        "--invalidate",
        action="store_true",
        help="Also create a CloudFront invalidation for the object path",
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    brain = od_aws.load_brain()

    local = Path(args.file)
    if not local.is_file():
        raise SystemExit(f"File not found: {local}")

    host, key = od_cdn.parse_target(args.url, args.host, args.key)
    content_type = args.content_type or od_cdn.guess_content_type(str(local))

    web_bucket = od_cdn.find_web_bucket(args.env, region=args.region, brain=brain)
    bucket = args.bucket or ((web_bucket or {}).get("name"))
    if not bucket:
        raise SystemExit("Could not resolve CDN bucket from brain; pass --bucket or re-run devops-onboard")

    before = None
    try:
        before = od_aws.run_aws(
            args.env,
            ["s3api", "head-object", "--bucket", bucket, "--key", key],
            region=args.region,
            brain=brain,
        )
    except SystemExit:
        before = None

    put = od_aws.run_aws(
        args.env,
        [
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--body",
            str(local.resolve()),
            "--content-type",
            content_type,
            "--server-side-encryption",
            "AES256",
        ],
        region=args.region,
        brain=brain,
    )

    after = od_aws.run_aws(
        args.env,
        ["s3api", "head-object", "--bucket", bucket, "--key", key],
        region=args.region,
        brain=brain,
    )

    invalidation = None
    if args.invalidate:
        dist = od_cdn.find_distribution(args.env, host, region=args.region, brain=brain)
        if not dist or not dist.get("id"):
            raise SystemExit(f"Could not resolve CloudFront distribution for host {host}")
        path = od_cdn.cloudfront_path_for_key(key)
        invalidation = od_aws.run_aws(
            args.env,
            [
                "cloudfront",
                "create-invalidation",
                "--distribution-id",
                dist["id"],
                "--paths",
                path,
            ],
            region=args.region,
            brain=brain,
        )

    od_aws.emit(
        {
            "env": args.env,
            "host": host,
            "key": key,
            "bucket": bucket,
            "contentType": content_type,
            "localFile": str(local.resolve()),
            "localBytes": local.stat().st_size,
            "before": {
                "etag": (before or {}).get("ETag"),
                "versionId": (before or {}).get("VersionId"),
                "contentLength": (before or {}).get("ContentLength"),
            }
            if before
            else None,
            "put": {
                "etag": (put or {}).get("ETag"),
                "versionId": (put or {}).get("VersionId"),
            },
            "after": {
                "etag": (after or {}).get("ETag"),
                "versionId": (after or {}).get("VersionId"),
                "contentLength": (after or {}).get("ContentLength"),
                "contentType": (after or {}).get("ContentType"),
            },
            "invalidation": invalidation,
            "publicUrl": f"https://{host}/{key}",
        }
    )


if __name__ == "__main__":
    main()
