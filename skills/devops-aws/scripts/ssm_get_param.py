#!/usr/bin/env python3
"""Read an SSM Parameter Store value (metadata + masked or full value).

Default output masks the value (shows last 4 chars). Pass --show-value for
plaintext. Always uses WithDecryption for SecureString unless --no-decrypt.
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


def get_param(
    env: str,
    name: str,
    *,
    decrypt: bool,
    show_value: bool,
    region: str | None,
    brain: dict[str, Any],
) -> dict[str, Any]:
    args = ["ssm", "get-parameter", "--name", name]
    if decrypt:
        args.append("--with-decryption")
    raw = od_aws.run_aws(env, args, region=region, brain=brain) or {}
    param = raw.get("Parameter") or {}
    value = param.get("Value")
    value_str = "" if value is None else str(value)
    out: dict[str, Any] = {
        "env": env,
        "name": param.get("Name") or name,
        "type": param.get("Type"),
        "version": param.get("Version"),
        "lastModifiedDate": param.get("LastModifiedDate"),
        "lastModifiedUser": param.get("LastModifiedUser"),
        "arn": param.get("ARN"),
        "dataType": param.get("DataType"),
        "decrypted": decrypt,
        "valueShown": show_value,
        "valueLength": len(value_str),
        "valueMasked": _mask(value_str),
    }
    if show_value:
        out["value"] = value_str
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get SSM parameter metadata + masked/full value"
    )
    od_aws.add_env_args(parser)
    parser.add_argument("--name", required=True, help="SSM parameter name (e.g. /Integrations/SendGrid/ApiKey)")
    parser.add_argument(
        "--show-value",
        action="store_true",
        help="Include plaintext value in JSON (default: mask, show last 4 only)",
    )
    parser.add_argument(
        "--no-decrypt",
        action="store_true",
        help="Do not pass --with-decryption (SecureString stays ciphertext / fails)",
    )
    args = parser.parse_args()
    brain = od_aws.load_brain()
    result = get_param(
        args.env,
        args.name,
        decrypt=not args.no_decrypt,
        show_value=args.show_value,
        region=args.region,
        brain=brain,
    )
    result["prod_class"] = od_aws.is_prod_env(args.env, brain)
    od_aws.emit(result)


if __name__ == "__main__":
    main()
