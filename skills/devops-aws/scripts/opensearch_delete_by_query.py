#!/usr/bin/env python3
"""OpenSearch delete-by-query (SigV4) against the onboarded domain data plane.

Requires IAM es:ESHttpPost (and typically es:ESHttpGet for pre-count).
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



def _agency_id_query(patterns: list[str]) -> dict[str, Any]:
    return {
        "query": {
            "bool": {
                "should": [
                    {"regexp": {"monitoringMeta.agencyId": pattern}} for pattern in patterns
                ],
                "minimum_should_match": 1,
            }
        }
    }


def _signed_json(
    session,
    host: str,
    region: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    url = f"https://{host}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    creds = session.get_credentials()
    if creds is None:
        raise SystemExit("No AWS credentials for OpenSearch SigV4 call")
    aws_req = AWSRequest(method=method, url=url, data=data, headers=headers)
    SigV4Auth(creds.get_frozen_credentials(), "es", region).add_auth(aws_req)
    prepared = aws_req.prepare()
    req = urllib.request.Request(
        prepared.url,
        data=prepared.body,
        headers=dict(prepared.headers),
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"OpenSearch {method} {path} HTTP {exc.code}: {err_body}\n"
            "Needs es:ESHttpPost (delete) / es:ESHttpGet (count) on the OpenSearch domain."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--index", required=True, help="Index name")
    parser.add_argument(
        "--agency-id-pattern",
        action="append",
        dest="agency_id_patterns",
        required=True,
        help="Regexp for monitoringMeta.agencyId (repeatable; required)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count matching docs; do not delete",
    )
    args = parser.parse_args()

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)
    _ensure_boto3()
    brain = od_aws.load_brain()
    region = args.region or od_aws.region_for(brain)
    host = _resolve_host(args.env, region=args.region, brain=brain)
    session = _session(args.env, region)
    patterns = args.agency_id_patterns
    body = _agency_id_query(patterns)

    count_resp = _signed_json(
        session, host, region, "POST", f"/{args.index}/_count", body=body
    )
    match_count = int((count_resp or {}).get("count") or 0)

    result: dict[str, Any] = {
        "env": args.env,
        "endpoint": host,
        "index": args.index,
        "agencyIdPatterns": patterns,
        "matchCountBefore": match_count,
        "dryRun": bool(args.dry_run),
        "explain": args.explain,
    }

    if args.dry_run:
        result["deleted"] = 0
        od_aws.emit(result)
        return

    delete_resp = _signed_json(
        session,
        host,
        region,
        "POST",
        f"/{args.index}/_delete_by_query",
        body=body,
        query={"conflicts": "proceed", "refresh": "true"},
    )
    deleted = int((delete_resp or {}).get("deleted") or 0)
    result["deleted"] = deleted
    result["deleteByQuery"] = {
        "took": (delete_resp or {}).get("took"),
        "timedOut": (delete_resp or {}).get("timed_out"),
        "total": (delete_resp or {}).get("total"),
        "deleted": deleted,
        "versionConflicts": (delete_resp or {}).get("version_conflicts"),
        "failures": (delete_resp or {}).get("failures") or [],
    }

    count_after = _signed_json(
        session, host, region, "POST", f"/{args.index}/_count", body=body
    )
    result["matchCountAfter"] = int((count_after or {}).get("count") or 0)
    od_aws.emit(result)


if __name__ == "__main__":
    main()
