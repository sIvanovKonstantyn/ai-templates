#!/usr/bin/env python3
"""List OpenSearch index store sizes via data-plane _cat/indices (SigV4).

Requires IAM es:ESHttpGet. Many interactive users are denied; then use
opensearch_cluster_stats.py (cluster-level CloudWatch volume) instead.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _ensure_boto3() -> None:
    try:
        import boto3  # noqa: F401
        from botocore.auth import SigV4Auth  # noqa: F401
        from botocore.awsrequest import AWSRequest  # noqa: F401
    except ImportError as exc:
        venv = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
        raise SystemExit(
            "boto3 required for SigV4 OpenSearch calls.\n"
            f"  python3 -m venv {Path(__file__).resolve().parent}/.venv && "
            f"{Path(__file__).resolve().parent}/.venv/bin/pip install boto3\n"
            f"  {venv} {__file__} ...\n{exc}"
        ) from exc


def _session(env: str, region: str):
    import boto3

    try:
        return boto3.Session(profile_name=env, region_name=region)
    except Exception:
        return boto3.Session(region_name=region)


def _resolve_host(env: str, *, region: str | None, brain: dict) -> str:
    os_cfg = brain.get("opensearch") or {}
    endpoint_param = os_cfg.get("endpoint_param")
    if endpoint_param:
        param = od_aws.run_aws(
            env,
            ["ssm", "get-parameter", "--name", endpoint_param],
            region=region,
            brain=brain,
        )
        host = ((param or {}).get("Parameter") or {}).get("Value") or ""
        host = host.replace("https://", "").replace("http://", "").rstrip("/")
        if host:
            return host
        raise SystemExit(f"Empty SSM {endpoint_param}")
    domain = od_aws.opensearch_domain(brain)
    desc = od_aws.run_aws(
        env,
        ["opensearch", "describe-domain", "--domain-name", domain],
        region=region,
        brain=brain,
    ) or {}
    host = ((desc.get("DomainStatus") or {}).get("Endpoint")) or ""
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    if not host:
        raise SystemExit(
            f"No endpoint for OpenSearch domain {domain!r}. "
            "Set brain opensearch.endpoint_param or ensure describe-domain returns Endpoint."
        )
    return host



def _signed_get(session, host: str, region: str, path: str, query: dict[str, str]) -> Any:
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    url = f"https://{host}{path}?{urlencode(query)}"
    creds = session.get_credentials()
    if creds is None:
        raise SystemExit("No AWS credentials for OpenSearch SigV4 call")
    aws_req = AWSRequest(method="GET", url=url)
    SigV4Auth(creds.get_frozen_credentials(), "es", region).add_auth(aws_req)
    prepared = aws_req.prepare()
    req = urllib.request.Request(prepared.url, headers=dict(prepared.headers), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"OpenSearch GET {path} HTTP {exc.code}: {body}\n"
            "If AccessDenied/es:ESHttpGet — use opensearch_cluster_stats.py for cluster volume, "
            "or run from a role/IP allowed for data-plane."
        ) from exc


def _gib(n: int | float) -> float:
    return round(float(n) / (1024**3), 3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    args = parser.parse_args()
    _ensure_boto3()
    brain = od_aws.load_brain()
    region = args.region or od_aws.region_for(brain)
    host = _resolve_host(args.env, region=args.region, brain=brain)
    session = _session(args.env, region)

    rows = _signed_get(
        session,
        host,
        region,
        "/_cat/indices",
        {
            "format": "json",
            "bytes": "b",
            "h": "health,status,index,pri,rep,docs.count,store.size,pri.store.size",
        },
    ) or []

    indices = []
    total_store = total_pri = total_docs = 0
    for r in rows:
        name = r.get("index") or ""
        if name.startswith("."):
            continue
        store = int(r.get("store.size") or 0)
        pri_store = int(r.get("pri.store.size") or 0)
        docs = int(float(r.get("docs.count") or 0))
        pri = int(r.get("pri") or 0)
        rep = int(r.get("rep") or 0)
        total_store += store
        total_pri += pri_store
        total_docs += docs
        avg = (pri_store / pri) if pri else None
        indices.append(
            {
                "index": name,
                "health": r.get("health"),
                "pri": pri,
                "rep": rep,
                "docs": docs,
                "storeGiB": _gib(store),
                "primaryStoreGiB": _gib(pri_store),
                "avgPrimaryShardGiB": _gib(avg) if avg is not None else None,
            }
        )
    indices.sort(key=lambda x: x.get("storeGiB") or 0, reverse=True)

    tiny = [
        i
        for i in indices
        if i.get("pri", 0) > 1
        and i.get("avgPrimaryShardGiB") is not None
        and i["avgPrimaryShardGiB"] < 1.0
        and (i.get("primaryStoreGiB") or 0) < 5.0
    ]

    od_aws.emit(
        {
            "env": args.env,
            "endpoint": host,
            "indexCount": len(indices),
            "totalDocs": total_docs,
            "totalStoreGiB": _gib(total_store),
            "totalPrimaryStoreGiB": _gib(total_pri),
            "indices": indices,
            "likelyOvershardedTinyShards": tiny,
        }
    )


if __name__ == "__main__":
    main()
