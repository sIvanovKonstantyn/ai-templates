#!/usr/bin/env python3
"""Shared AWS helpers for Devops tools (aws-vault / profile / env credentials)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".cursor").is_dir():
            return parent
    return here.parents[3]


def brain_path() -> Path:
    return repo_root() / ".cursor" / "devops" / "brain.json"


def load_brain() -> dict[str, Any]:
    path = brain_path()
    if not path.is_file():
        raise SystemExit(
            f"Brain missing: {path}\n"
            "Run the devops-onboard skill (or bootstrap_env.py via onboard) first."
        )
    with path.open() as f:
        brain = json.load(f)
    if not brain.get("prod_profiles"):
        raise SystemExit(
            f"Brain incomplete (prod_profiles empty): {path}\n"
            "Re-run devops-onboard / bootstrap_env.py set-prod ..."
        )
    return brain


def save_brain(brain: dict[str, Any]) -> Path:
    path = brain_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(brain, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def require_brain_key(brain: dict[str, Any], dotted: str) -> Any:
    """Return nested brain value or exit with onboard guidance."""
    cur: Any = brain
    parts = dotted.split(".")
    for part in parts:
        if not isinstance(cur, dict) or part not in cur or cur[part] in (None, ""):
            raise SystemExit(
                f"Brain missing required key `{dotted}` (at `{part}`).\n"
                f"Re-run devops-onboard and set this field, or edit {brain_path()}."
            )
        cur = cur[part]
    return cur


def is_prod_env(env: str, brain: dict[str, Any] | None = None) -> bool:
    brain = brain or load_brain()
    return env in set(brain.get("prod_profiles") or [])


def region_for(brain: dict[str, Any] | None = None) -> str:
    brain = brain or load_brain()
    return (
        brain.get("region_default")
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )


def auth_mode(brain: dict[str, Any] | None = None) -> str:
    brain = brain or load_brain()
    mode = (brain.get("auth_mode") or "aws-vault").strip().lower()
    if mode not in {"aws-vault", "aws-profile", "env"}:
        raise SystemExit(
            f"Unsupported brain auth_mode={mode!r}. Use aws-vault | aws-profile | env."
        )
    return mode


def aws_vault_bin(brain: dict[str, Any] | None = None) -> str:
    brain = brain or load_brain()
    return brain.get("vault_command") or "aws-vault"


def _aws_cli_base(env: str, aws_args: list[str], region: str, *, use_profile: bool) -> list[str]:
    cmd = ["aws", *aws_args, "--region", region, "--output", "json"]
    if use_profile:
        cmd[1:1] = []  # no-op keep structure clear
        # insert profile after aws
        cmd = ["aws", *aws_args, "--profile", env, "--region", region, "--output", "json"]
    return cmd


def _vault_credentials_missing(err: str) -> bool:
    lower = err.lower()
    return "credentials missing" in lower or "no credentials" in lower


def run_aws(
    env: str,
    aws_args: list[str],
    *,
    region: str | None = None,
    brain: dict[str, Any] | None = None,
) -> Any:
    """Run AWS CLI for env according to brain auth_mode."""
    brain = brain or load_brain()
    region = region or region_for(brain)
    mode = auth_mode(brain)

    if mode == "env":
        proc = subprocess.run(
            ["aws", *aws_args, "--region", region, "--output", "json"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise SystemExit(f"AWS command failed (env creds): {' '.join(aws_args)}\n{err}")
        text = (proc.stdout or "").strip()
        return json.loads(text) if text else None

    if mode == "aws-profile":
        proc = subprocess.run(
            _aws_cli_base(env, aws_args, region, use_profile=True),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise SystemExit(f"AWS command failed ({env}): {' '.join(aws_args)}\n{err}")
        text = (proc.stdout or "").strip()
        return json.loads(text) if text else None

    # aws-vault (default), with profile fallback
    vault_cmd = [
        aws_vault_bin(brain),
        "exec",
        env,
        "--",
        "aws",
        *aws_args,
        "--region",
        region,
        "--output",
        "json",
    ]
    proc = subprocess.run(vault_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        if _vault_credentials_missing(err):
            proc = subprocess.run(
                _aws_cli_base(env, aws_args, region, use_profile=True),
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                err2 = (proc.stderr or proc.stdout or "").strip()
                raise SystemExit(
                    f"AWS command failed ({env}): {' '.join(aws_args)}\n"
                    f"aws-vault: {err}\naws --profile: {err2}"
                )
        else:
            raise SystemExit(f"AWS command failed ({env}): {' '.join(aws_args)}\n{err}")
    text = (proc.stdout or "").strip()
    return json.loads(text) if text else None


def require_mutate_approval(env: str, explanation: str, approve_prod: bool) -> None:
    brain = load_brain()
    print(json.dumps({"mutation_explanation": explanation, "env": env}, indent=2))
    if is_prod_env(env, brain) and not approve_prod:
        raise SystemExit(
            "REFUSED: prod-class env requires chat approval first.\n"
            "Explain the change to the user, wait for explicit approve/yes, "
            "then re-run with --approve-prod."
        )


def emit(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def add_env_args(parser: argparse.ArgumentParser, *, mutating: bool = False) -> None:
    parser.add_argument("--env", required=True, help="AWS profile / brain env name")
    parser.add_argument("--region", default=None, help="Override region (default from brain)")
    if mutating:
        parser.add_argument(
            "--approve-prod",
            action="store_true",
            help="Required for prod-class envs after explicit chat approval",
        )
        parser.add_argument(
            "--explain",
            required=True,
            help="Human-readable explanation of the mutation (required)",
        )


def stack_cluster(stack: str, brain: dict[str, Any] | None = None) -> str:
    """Resolve ECS cluster name from brain ecs.cluster_name_template.

    Template must include `{stack}` (e.g. `{stack}-cluster`). If the caller
    already passed a full cluster name matching a known suffix heuristic, it is
    returned unchanged when it equals the rendered template for the same stack.
    """
    brain = brain or load_brain()
    template = require_brain_key(brain, "ecs.cluster_name_template")
    if not isinstance(template, str) or "{stack}" not in template:
        raise SystemExit(
            "Brain ecs.cluster_name_template must be a string containing `{stack}`.\n"
            f"Re-run devops-onboard. Current: {template!r}"
        )
    base = stack.rstrip("-")
    # If user already passed the rendered cluster name, accept it.
    rendered = template.format(stack=base)
    if stack == rendered:
        return stack
    # If stack already looks like a full cluster (contains more than the bare name),
    # and equals template with stack=prefix, prefer explicit full name when it
    # matches common patterns: ends with same suffix as template after {stack}.
    suffix = template.split("{stack}", 1)[-1]
    if suffix and stack.endswith(suffix) and "{stack}" not in stack:
        return stack
    return rendered


def cluster_name(service: str, brain: dict[str, Any] | None = None) -> str:
    """Alias for stack_cluster (historical name)."""
    return stack_cluster(service, brain)


def critical_env_keys(brain: dict[str, Any] | None = None) -> list[str]:
    brain = brain or load_brain()
    keys = (brain.get("ecs") or {}).get("critical_env_keys") or []
    if not isinstance(keys, list):
        raise SystemExit("Brain ecs.critical_env_keys must be a list of strings")
    return [str(k) for k in keys]


def opensearch_domain(brain: dict[str, Any] | None = None) -> str:
    brain = brain or load_brain()
    return str(require_brain_key(brain, "opensearch.domain"))
