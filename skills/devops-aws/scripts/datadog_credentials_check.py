#!/usr/bin/env python3
"""Check Datadog SSM credential presence (never prints secret values)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws
import datadog_lib as od_datadog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--api-key-param", default=None)
    parser.add_argument("--app-key-param", default=None)
    parser.add_argument("--site-param", default=None)
    args = parser.parse_args()

    brain = od_aws.load_brain()
    try:
        creds = od_datadog.resolve_credentials(
            args.env,
            region=args.region,
            brain=brain,
            api_key_param=args.api_key_param,
            app_key_param=args.app_key_param,
            site_param=args.site_param,
        )
        od_aws.emit(
            {
                "env": args.env,
                "prod_class": od_aws.is_prod_env(args.env, brain),
                "ok": True,
                "credentials": od_datadog.credentials_meta(creds),
            }
        )
    except SystemExit as exc:
        od_aws.emit(
            {
                "env": args.env,
                "prod_class": od_aws.is_prod_env(args.env, brain),
                "ok": False,
                "error": str(exc),
            }
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
