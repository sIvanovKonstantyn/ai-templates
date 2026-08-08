#!/usr/bin/env python3
"""Deploy a Lambda zip via update-function-code.

Optional --package-dir runs `npm run package` there and uses --zip-name inside build/.
Also can set linked SQS visibility timeout when --visibility-timeout is passed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _run_local(cmd: list[str], *, cwd: Path) -> None:
    print(f"+ ({cwd}) {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, cwd=str(cwd), text=True)
    if proc.returncode != 0:
        raise SystemExit(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def _package(service_dir: Path, zip_name: str) -> Path:
    zip_path = service_dir / "build" / zip_name
    if not (service_dir / "node_modules").is_dir():
        _run_local(["npm", "ci"], cwd=service_dir) if (service_dir / "package-lock.json").is_file() else _run_local(
            ["npm", "i"], cwd=service_dir
        )
    _run_local(["npm", "run", "package"], cwd=service_dir)
    if not zip_path.is_file():
        raise SystemExit(f"Package zip missing: {zip_path}")
    return zip_path


def _wait_updated(env: str, function: str, *, region: str | None, brain: dict[str, Any]) -> None:
    # wait has no useful JSON; use update-function-configuration get instead via get-function
    od_aws.run_aws(
        env,
        ["lambda", "wait", "function-updated", "--function-name", function],
        region=region,
        brain=brain,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser, mutating=True)
    parser.add_argument("--function", required=True, help="Lambda function name")
    parser.add_argument(
        "--zip",
        default=None,
        help="Path to deployment zip (required unless --package-dir is set)",
    )
    parser.add_argument(
        "--package-dir",
        default=None,
        help="Directory with package.json; runs npm run package and uses build/--zip-name",
    )
    parser.add_argument(
        "--zip-name",
        default="function.zip",
        help="Zip filename under package-dir/build/ (default: function.zip)",
    )
    parser.add_argument(
        "--queue",
        default=None,
        help="SQS queue name/URL to update visibility (required with --visibility-timeout)",
    )
    parser.add_argument(
        "--visibility-timeout",
        type=int,
        default=None,
        help="If set, update SQS VisibilityTimeout to this many seconds",
    )
    args = parser.parse_args()
    brain = od_aws.load_brain()

    od_aws.require_mutate_approval(
        args.env,
        args.explain,
        args.approve_prod,
    )

    if args.zip:
        zip_path = Path(args.zip).resolve()
    elif args.package_dir:
        zip_path = _package(Path(args.package_dir), args.zip_name).resolve()
    else:
        raise SystemExit("Provide --zip or --package-dir")
    if not zip_path.is_file():
        raise SystemExit(f"Zip missing: {zip_path}")

    before = od_aws.run_aws(
        args.env,
        ["lambda", "get-function-configuration", "--function-name", args.function],
        region=args.region,
        brain=brain,
    ) or {}

    updated = od_aws.run_aws(
        args.env,
        [
            "lambda",
            "update-function-code",
            "--function-name",
            args.function,
            "--zip-file",
            f"fileb://{zip_path}",
        ],
        region=args.region,
        brain=brain,
    ) or {}

    # wait command returns empty; ignore via try by calling get until Successful
    try:
        subprocess_wait = [
            "lambda",
            "wait",
            "function-updated",
            "--function-name",
            args.function,
        ]
        # od_aws.run_aws json.loads empty → None; wait outputs nothing on success
        vault_or_profile_wait(args.env, subprocess_wait, region=args.region, brain=brain)
    except SystemExit:
        pass

    after = od_aws.run_aws(
        args.env,
        ["lambda", "get-function-configuration", "--function-name", args.function],
        region=args.region,
        brain=brain,
    ) or {}

    sqs_result = None
    if args.visibility_timeout is not None:
        if not args.queue:
            raise SystemExit("--visibility-timeout requires --queue")
        queue = args.queue
        url = queue
        if not queue.startswith("https://"):
            urls = od_aws.run_aws(
                args.env,
                ["sqs", "get-queue-url", "--queue-name", queue],
                region=args.region,
                brain=brain,
            ) or {}
            url = urls["QueueUrl"]
        od_aws.run_aws(
            args.env,
            [
                "sqs",
                "set-queue-attributes",
                "--queue-url",
                url,
                "--attributes",
                f"VisibilityTimeout={args.visibility_timeout}",
            ],
            region=args.region,
            brain=brain,
        )
        attrs = od_aws.run_aws(
            args.env,
            [
                "sqs",
                "get-queue-attributes",
                "--queue-url",
                url,
                "--attribute-names",
                "VisibilityTimeout",
            ],
            region=args.region,
            brain=brain,
        ) or {}
        sqs_result = {
            "queueUrl": url,
            "visibilityTimeoutSeconds": int(
                (attrs.get("Attributes") or {}).get("VisibilityTimeout") or 0
            ),
        }

    od_aws.emit(
        {
            "env": args.env,
            "function": args.function,
            "zip": str(zip_path),
            "zipBytes": zip_path.stat().st_size,
            "before": {
                "lastModified": before.get("LastModified"),
                "codeSize": before.get("CodeSize"),
                "codeSha256": before.get("CodeSha256"),
                "timeout": before.get("Timeout"),
            },
            "after": {
                "lastModified": after.get("LastModified"),
                "codeSize": after.get("CodeSize"),
                "codeSha256": after.get("CodeSha256"),
                "lastUpdateStatus": after.get("LastUpdateStatus"),
                "state": after.get("State"),
                "timeout": after.get("Timeout"),
            },
            "updateFunctionCode": {
                "codeSha256": updated.get("CodeSha256"),
                "lastUpdateStatus": updated.get("LastUpdateStatus"),
            },
            "sqs": sqs_result,
            "mutation_explanation": args.explain,
        }
    )


def vault_or_profile_wait(
    env: str, aws_args: list[str], *, region: str | None, brain: dict[str, Any]
) -> None:
    """Run a non-JSON aws command (e.g. lambda wait) with same vault/profile fallback as od_aws."""
    import os
    import subprocess as sp

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
    proc = sp.run(vault_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        if "credentials missing" in err.lower() or "no credentials" in err.lower():
            proc = sp.run(
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
                    f"AWS wait failed ({env}): {' '.join(aws_args)}\n{(proc.stderr or proc.stdout or '').strip()}"
                )
        else:
            raise SystemExit(f"AWS wait failed ({env}): {' '.join(aws_args)}\n{err}")


if __name__ == "__main__":
    main()
