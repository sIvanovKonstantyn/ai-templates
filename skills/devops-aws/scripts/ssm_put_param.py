#!/usr/bin/env python3
"""Create or overwrite an SSM Parameter Store value (mutate; prod needs --approve-prod).

Never prints the plaintext value — only name, type, version, length, masked last 4.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _mask(value: str, *, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return f"{'*' * (len(value) - keep)}{value[-keep:]}"


def put_param(
    env: str,
    name: str,
    value: str,
    *,
    param_type: str,
    overwrite: bool,
    description: str | None,
    tags: list[dict[str, str]] | None,
    region: str | None,
    brain: dict[str, Any],
) -> dict[str, Any]:
    args = [
        "ssm",
        "put-parameter",
        "--name",
        name,
        "--type",
        param_type,
        "--value",
        value,
    ]
    if description:
        args.extend(["--description", description])
    if overwrite:
        args.append("--overwrite")
    # Tags only allowed on create (not with overwrite of existing in some cases).
    # AWS: --tags cannot be used with --overwrite. Apply tags only when not overwriting.
    if tags and not overwrite:
        tag_args = []
        for t in tags:
            tag_args.append(f"Key={t['Key']},Value={t['Value']}")
        args.extend(["--tags", *tag_args])

    raw = od_aws.run_aws(env, args, region=region, brain=brain) or {}
    return {
        "env": env,
        "name": name,
        "type": param_type,
        "version": raw.get("Version"),
        "tier": raw.get("Tier"),
        "overwrite": overwrite,
        "valueLength": len(value),
        "valueMasked": _mask(value),
        "taggedOnCreate": bool(tags) and not overwrite,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--value", required=True, help="Parameter value (avoid logging shells)")
    parser.add_argument(
        "--type",
        dest="param_type",
        default="SecureString",
        choices=["String", "StringList", "SecureString"],
    )
    parser.add_argument("--description", default=None)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite if the parameter already exists",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Tag on create only (repeatable). Ignored when --overwrite.",
    )
    args = parser.parse_args()
    od_aws.require_mutate_approval(args.env, args.explain, args.approve_prod)

    tags = []
    for item in args.tag:
        if "=" not in item:
            raise SystemExit(f"Bad --tag {item!r}; expected KEY=VALUE")
        k, v = item.split("=", 1)
        tags.append({"Key": k, "Value": v})

    brain = od_aws.load_brain()
    result = put_param(
        args.env,
        args.name,
        args.value,
        param_type=args.param_type,
        overwrite=args.overwrite,
        description=args.description,
        tags=tags or None,
        region=args.region,
        brain=brain,
    )
    result["prod_class"] = od_aws.is_prod_env(args.env, brain)
    result["mutation_explanation"] = args.explain
    od_aws.emit(result)


if __name__ == "__main__":
    main()
