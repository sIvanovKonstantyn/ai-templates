#!/usr/bin/env python3
"""Merge or unset Lambda environment variables without replacing the full map.

AWS ``update-function-configuration --environment`` replaces the *entire*
Variables object. This tool always GETs the current map, merges ``--set`` /
applies ``--unset``, then PUTs the full result — so unrelated keys (secrets,
bucket names, Datadog) are never dropped.

Never prints secret values — keys matching KEY/SECRET/TOKEN/PASSWORD are masked.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws

_SECRET_KEY_RE = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD)", re.IGNORECASE)


def _mask_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if _SECRET_KEY_RE.search(key):
        if len(value) <= 4:
            return "*" * len(value)
        return f"{'*' * (len(value) - 4)}{value[-4:]}"
    return value


def _parse_set(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--set expects KEY=VALUE, got: {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"--set has empty key: {item!r}")
        if key in out:
            raise SystemExit(f"--set key repeated: {key}")
        out[key] = value
    return out


def _diff_env(
    before: dict[str, str], after: dict[str, str]
) -> list[dict[str, Any]]:
    keys = sorted(set(before) | set(after))
    changes: list[dict[str, Any]] = []
    for key in keys:
        b, a = before.get(key), after.get(key)
        if b == a:
            continue
        if b is None:
            action = "add"
        elif a is None:
            action = "remove"
        else:
            action = "change"
        changes.append(
            {
                "key": key,
                "action": action,
                "before": _mask_value(key, b),
                "after": _mask_value(key, a),
            }
        )
    return changes


def vault_or_profile_wait(
    env: str, aws_args: list[str], *, region: str | None, brain: dict[str, Any]
) -> None:
    """Run a non-JSON aws command (e.g. lambda wait) with same vault/profile fallback."""
    region = region or od_aws.region_for(brain)
    vault_cmd = [
        od_aws.aws_vault_bin(brain),
        "exec",
        env,
        "--",
        "aws",
        *aws_args,
        "--region",
        region,
    ]
    proc = subprocess.run(vault_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        if "credentials missing" in err.lower() or "no credentials" in err.lower():
            proc = subprocess.run(
                [
                    "aws",
                    *aws_args,
                    "--profile",
                    env,
                    "--region",
                    region,
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise SystemExit(
                    f"AWS wait failed ({env}): {' '.join(aws_args)}\n"
                    f"{(proc.stderr or proc.stdout or '').strip()}"
                )
        else:
            raise SystemExit(f"AWS wait failed ({env}): {' '.join(aws_args)}\n{err}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--function", required=True, help="Lambda function name")
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Upsert env var (repeatable). Merged into the existing Variables map.",
    )
    parser.add_argument(
        "--unset",
        action="append",
        default=[],
        metavar="KEY",
        help="Remove env var if present (repeatable).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print the merge diff only; do not call update-function-configuration",
    )
    args = parser.parse_args()
    brain = od_aws.load_brain()

    sets = _parse_set(args.set)
    unsets = [k.strip() for k in args.unset if k.strip()]
    if not sets and not unsets:
        raise SystemExit("Nothing to do: pass at least one --set KEY=VALUE or --unset KEY")
    overlap = sorted(set(sets) & set(unsets))
    if overlap:
        raise SystemExit(f"Same key in --set and --unset: {', '.join(overlap)}")

    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)

    before_cfg = (
        od_aws.run_aws(
            args.env,
            ["lambda", "get-function-configuration", "--function-name", args.function],
            region=args.region,
            brain=brain,
        )
        or {}
    )
    before_env = dict((before_cfg.get("Environment") or {}).get("Variables") or {})
    after_env = dict(before_env)
    for key in unsets:
        after_env.pop(key, None)
    after_env.update(sets)

    changes = _diff_env(before_env, after_env)
    if not changes:
        od_aws.emit(
            {
                "env": args.env,
                "function": args.function,
                "dryRun": args.dry_run,
                "changed": False,
                "changes": [],
                "envKeyCount": len(after_env),
                "mutation_explanation": args.explain,
            }
        )
        return

    if args.dry_run:
        od_aws.emit(
            {
                "env": args.env,
                "function": args.function,
                "dryRun": True,
                "changed": True,
                "changes": changes,
                "envKeyCountBefore": len(before_env),
                "envKeyCountAfter": len(after_env),
                "mutation_explanation": args.explain,
            }
        )
        return

    # CLI expects Variables as KEY=VALUE pairs for --environment
    # Prefer JSON file shape for values that may contain commas/spaces.
    import json
    import tempfile

    payload = {"Variables": after_env}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(payload, fh)
        env_file = fh.name

    try:
        od_aws.run_aws(
            args.env,
            [
                "lambda",
                "update-function-configuration",
                "--function-name",
                args.function,
                "--environment",
                f"file://{env_file}",
            ],
            region=args.region,
            brain=brain,
        )
    finally:
        Path(env_file).unlink(missing_ok=True)

    try:
        vault_or_profile_wait(
            args.env,
            ["lambda", "wait", "function-updated", "--function-name", args.function],
            region=args.region,
            brain=brain,
        )
    except SystemExit:
        pass

    after_cfg = (
        od_aws.run_aws(
            args.env,
            ["lambda", "get-function-configuration", "--function-name", args.function],
            region=args.region,
            brain=brain,
        )
        or {}
    )
    live_env = dict((after_cfg.get("Environment") or {}).get("Variables") or {})
    live_changes = _diff_env(before_env, live_env)

    od_aws.emit(
        {
            "env": args.env,
            "function": args.function,
            "dryRun": False,
            "changed": True,
            "changes": live_changes,
            "envKeyCountBefore": len(before_env),
            "envKeyCountAfter": len(live_env),
            "state": after_cfg.get("State"),
            "lastUpdateStatus": after_cfg.get("LastUpdateStatus"),
            "mutation_explanation": args.explain,
        }
    )


if __name__ == "__main__":
    main()
