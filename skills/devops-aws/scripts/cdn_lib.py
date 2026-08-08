#!/usr/bin/env python3
"""Shared CDN helpers (CloudFront alias + origin bucket from brain)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import aws_lib as od_aws


def parse_target(url: str | None, host: str | None, key: str | None) -> tuple[str, str]:
    if url:
        parsed = urlparse(url)
        if not parsed.netloc or not parsed.path or parsed.path == "/":
            raise SystemExit(f"URL must include host and object path: {url}")
        return parsed.netloc, parsed.path.lstrip("/")
    if host and key:
        return host, key.lstrip("/")
    raise SystemExit("Provide --url or both --host and --key")


def find_distribution(
    env: str, host: str, *, region: str | None, brain: dict[str, Any]
) -> dict[str, Any] | None:
    listed = od_aws.run_aws(
        env,
        ["cloudfront", "list-distributions"],
        region=region,
        brain=brain,
    ) or {}
    items = ((listed.get("DistributionList") or {}).get("Items")) or []
    for dist in items:
        aliases = ((dist.get("Aliases") or {}).get("Items")) or []
        if host in aliases or any(host.endswith(a) for a in aliases):
            origins = []
            for o in ((dist.get("Origins") or {}).get("Items")) or []:
                origins.append(
                    {
                        "id": o.get("Id"),
                        "domainName": o.get("DomainName"),
                        "originPath": o.get("OriginPath") or "",
                    }
                )
            return {
                "id": dist.get("Id"),
                "domainName": dist.get("DomainName"),
                "status": dist.get("Status"),
                "enabled": dist.get("Enabled"),
                "aliases": aliases,
                "origins": origins,
            }
    return None


def find_web_bucket(
    env: str, *, region: str | None, brain: dict[str, Any]
) -> dict[str, Any] | None:
    cdn = brain.get("cdn") or {}
    bucket_name = cdn.get("bucket_name")
    if bucket_name:
        return {"name": str(bucket_name), "arn": None, "tags": {}, "source": "brain.cdn.bucket_name"}

    tag = cdn.get("bucket_tag") or {}
    key = tag.get("key")
    value = tag.get("value")
    if not key or not value:
        raise SystemExit(
            "CDN bucket not configured in brain.\n"
            "Set cdn.bucket_name and/or cdn.bucket_tag.{key,value} via devops-onboard."
        )

    tagged = od_aws.run_aws(
        env,
        [
            "resourcegroupstaggingapi",
            "get-resources",
            "--resource-type-filters",
            "s3",
            "--tag-filters",
            f"Key={key},Values={value}",
        ],
        region=region,
        brain=brain,
    ) or {}
    mappings = tagged.get("ResourceTagMappingList") or []
    if not mappings:
        return None
    arn = mappings[0].get("ResourceARN") or ""
    name = arn.rsplit(":::", 1)[-1] if ":::" in arn else arn
    tags = {t.get("Key"): t.get("Value") for t in (mappings[0].get("Tags") or [])}
    return {
        "name": name,
        "arn": arn,
        "tags": tags,
        "source": f"tag:{key}={value}",
    }


def s3_bucket_from_origin(domain: str) -> str | None:
    if ".s3" in domain and domain.endswith(".amazonaws.com"):
        return domain.split(".s3", 1)[0]
    return None


def guess_content_type(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".css"):
        return "text/css"
    if lower.endswith(".js"):
        return "application/javascript"
    return "application/octet-stream"


def cloudfront_path_for_key(key: str) -> str:
    return "/" + key.lstrip("/")
