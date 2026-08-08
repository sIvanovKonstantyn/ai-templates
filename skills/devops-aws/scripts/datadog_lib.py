#!/usr/bin/env python3
"""Datadog API helpers: SSM credentials + HTTP (never echo secret values)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import aws_lib as od_aws

DEFAULT_SITE = "datadoghq.com"


def _ssm_get(env: str, name: str, *, region: str | None, brain: dict[str, Any]) -> str | None:
    try:
        raw = od_aws.run_aws(
            env,
            ["ssm", "get-parameter", "--name", name, "--with-decryption"],
            region=region,
            brain=brain,
        ) or {}
    except SystemExit as exc:
        err = str(exc)
        if "ParameterNotFound" in err or "not found" in err.lower():
            return None
        raise
    value = (raw.get("Parameter") or {}).get("Value")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_credentials(
    env: str,
    *,
    region: str | None = None,
    brain: dict[str, Any] | None = None,
    api_key_param: str | None = None,
    app_key_param: str | None = None,
    site_param: str | None = None,
) -> dict[str, Any]:
    """Load API key + application key + site from brain SSM paths or env overrides."""
    brain = brain or od_aws.load_brain()
    dd = brain.get("datadog") or {}

    api_path = api_key_param or dd.get("api_key_param")
    app_path = app_key_param or dd.get("app_key_param")
    site_path = site_param or dd.get("site_param")

    if not api_path and not (os.environ.get("DD_API_KEY") or "").strip():
        raise SystemExit(
            "Datadog API key path not configured.\n"
            "Set brain datadog.api_key_param via devops-onboard, or export DD_API_KEY."
        )
    if not app_path and not (os.environ.get("DD_APP_KEY") or "").strip():
        raise SystemExit(
            "Datadog application key path not configured.\n"
            "Set brain datadog.app_key_param via devops-onboard, or export DD_APP_KEY."
        )

    api_key = _ssm_get(env, api_path, region=region, brain=brain) if api_path else None
    api_from = "ssm" if api_key else None
    if not api_key:
        api_key = (os.environ.get("DD_API_KEY") or "").strip() or None
        api_from = "env:DD_API_KEY" if api_key else None

    app_key = _ssm_get(env, app_path, region=region, brain=brain) if app_path else None
    app_from = "ssm" if app_key else None
    if not app_key:
        app_key = (os.environ.get("DD_APP_KEY") or "").strip() or None
        app_from = "env:DD_APP_KEY" if app_key else None

    site = None
    site_from = None
    if site_path:
        site = _ssm_get(env, site_path, region=region, brain=brain)
        site_from = "ssm" if site else None
    if not site:
        site = (os.environ.get("DD_SITE") or "").strip() or DEFAULT_SITE
        site_from = "env:DD_SITE" if os.environ.get("DD_SITE") else "default"

    missing = []
    if not api_key:
        missing.append(f"API key (SSM {api_path!r} or env DD_API_KEY)")
    if not app_key:
        missing.append(f"Application key (SSM {app_path!r} or env DD_APP_KEY)")
    if missing:
        raise SystemExit("Datadog credentials incomplete:\n- " + "\n- ".join(missing))

    return {
        "api_key": api_key,
        "app_key": app_key,
        "site": site,
        "base_url": f"https://api.{site}",
        "sources": {
            "api_key": api_from,
            "app_key": app_from,
            "site": site_from,
            "api_key_param": api_path,
            "app_key_param": app_path,
            "site_param": site_path,
        },
    }


def credentials_meta(creds: dict[str, Any]) -> dict[str, Any]:
    """Safe summary for JSON output (lengths only, never values)."""
    return {
        "site": creds["site"],
        "base_url": creds["base_url"],
        "sources": creds["sources"],
        "api_key_len": len(creds["api_key"] or ""),
        "app_key_len": len(creds["app_key"] or ""),
    }


def request(
    creds: dict[str, Any],
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    url = creds["base_url"].rstrip("/") + path
    if query:
        qs = urllib.parse.urlencode(
            {k: v for k, v in query.items() if v is not None}, doseq=True
        )
        url = f"{url}?{qs}"
    data = None
    headers = {
        "DD-API-KEY": creds["api_key"],
        "DD-APPLICATION-KEY": creds["app_key"],
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
            payload = json.loads(raw) if raw.strip() else {}
            return {"status": status, "body": payload}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body) if err_body.strip() else {}
        except json.JSONDecodeError:
            parsed = {"raw": err_body[:2000]}
        raise SystemExit(
            f"Datadog API {method.upper()} {path} failed: HTTP {exc.code}\n"
            f"{json.dumps(parsed, indent=2)[:4000]}"
        ) from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"Datadog API network error: {exc}") from None
