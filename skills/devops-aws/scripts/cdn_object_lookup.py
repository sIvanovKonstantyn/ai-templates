#!/usr/bin/env python3
"""Locate a CDN object: CloudFront alias → S3 origin → head-object (+ optional prefix list)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws
import cdn_lib as od_cdn


def _head_object(
    env: str,
    bucket: str,
    key: str,
    *,
    region: str | None,
    brain: dict[str, Any],
) -> dict[str, Any]:
    try:
        meta = od_aws.run_aws(
            env,
            ["s3api", "head-object", "--bucket", bucket, "--key", key],
            region=region,
            brain=brain,
        ) or {}
        return {
            "exists": True,
            "bucket": bucket,
            "key": key,
            "contentType": meta.get("ContentType"),
            "contentLength": meta.get("ContentLength"),
            "etag": meta.get("ETag"),
            "lastModified": meta.get("LastModified"),
            "versionId": meta.get("VersionId"),
            "serverSideEncryption": meta.get("ServerSideEncryption"),
        }
    except SystemExit as exc:
        err = str(exc)
        if "Not Found" in err or "404" in err or "NoSuchKey" in err:
            return {"exists": False, "bucket": bucket, "key": key, "error": err}
        raise


def _list_prefix(
    env: str,
    bucket: str,
    prefix: str,
    *,
    region: str | None,
    brain: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    listed = od_aws.run_aws(
        env,
        [
            "s3api",
            "list-objects-v2",
            "--bucket",
            bucket,
            "--prefix",
            prefix,
            "--max-keys",
            str(limit),
        ],
        region=region,
        brain=brain,
    ) or {}
    out = []
    for obj in listed.get("Contents") or []:
        out.append(
            {
                "key": obj.get("Key"),
                "size": obj.get("Size"),
                "lastModified": obj.get("LastModified"),
                "etag": obj.get("ETag"),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--url", default=None, help="Full CDN URL to resolve")
    parser.add_argument("--host", default=None, help="CDN hostname (with --key)")
    parser.add_argument("--key", default=None, help="Object key (with --host)")
    parser.add_argument(
        "--list-prefix",
        action="store_true",
        help="Also list sibling objects under the object's directory prefix",
    )
    parser.add_argument("--limit", type=int, default=30, help="Max keys when listing prefix")
    args = parser.parse_args()
    brain = od_aws.load_brain()

    host, key = od_cdn.parse_target(args.url, args.host, args.key)
    dist = od_cdn.find_distribution(args.env, host, region=args.region, brain=brain)
    web_bucket = od_cdn.find_web_bucket(args.env, region=args.region, brain=brain)

    candidate_buckets: list[str] = []
    if web_bucket and web_bucket.get("name"):
        candidate_buckets.append(web_bucket["name"])
    if dist:
        for o in dist.get("origins") or []:
            b = od_cdn.s3_bucket_from_origin(o.get("domainName") or "")
            if b and b not in candidate_buckets:
                candidate_buckets.append(b)

    heads: list[dict[str, Any]] = []
    found: dict[str, Any] | None = None
    for bucket in candidate_buckets:
        head = _head_object(args.env, bucket, key, region=args.region, brain=brain)
        heads.append(head)
        if head.get("exists"):
            found = head
            break

    prefix_listing = None
    if args.list_prefix and found:
        prefix = key.rsplit("/", 1)[0] + "/" if "/" in key else ""
        prefix_listing = {
            "prefix": prefix,
            "objects": _list_prefix(
                args.env,
                found["bucket"],
                prefix,
                region=args.region,
                brain=brain,
                limit=args.limit,
            ),
        }

    od_aws.emit(
        {
            "env": args.env,
            "prod_class": od_aws.is_prod_env(args.env, brain),
            "host": host,
            "key": key,
            "cloudfront": dist,
            "originBucket": web_bucket,
            "candidateBuckets": candidate_buckets,
            "object": found,
            "headAttempts": heads,
            "prefixListing": prefix_listing,
        }
    )


if __name__ == "__main__":
    main()
