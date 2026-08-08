#!/usr/bin/env python3
"""Bootstrap / inspect workspace Devops brain (AWS profiles → prod mapping)."""

from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path

import aws_lib as od_aws


def discover_profiles() -> list[str]:
    names: set[str] = set()
    config_path = Path.home() / ".aws" / "config"
    creds_path = Path.home() / ".aws" / "credentials"

    if config_path.is_file():
        parser = configparser.RawConfigParser()
        parser.read(config_path)
        for section in parser.sections():
            if section == "default":
                names.add("default")
            elif section.startswith("profile "):
                names.add(section[len("profile ") :].strip())
            else:
                names.add(section.strip())

    if creds_path.is_file():
        parser = configparser.RawConfigParser()
        parser.read(creds_path)
        for section in parser.sections():
            names.add(section.strip())

    preferred = ["dev", "staging", "qa", "prod", "infra", "default"]
    ordered = [p for p in preferred if p in names]
    ordered.extend(sorted(n for n in names if n not in ordered))
    return ordered


def cmd_list(_: argparse.Namespace) -> None:
    profiles = discover_profiles()
    brain_exists = od_aws.brain_path().is_file()
    current = None
    if brain_exists:
        try:
            current = od_aws.load_brain()
        except SystemExit:
            current = json.loads(od_aws.brain_path().read_text())
    od_aws.emit(
        {
            "brain_path": str(od_aws.brain_path()),
            "brain_exists": brain_exists,
            "current_brain": current,
            "discovered_profiles": profiles,
            "next_step": (
                "Prefer devops-onboard for full setup. Or: "
                "bootstrap_env.py set-prod <profile> [more...]"
            ),
        }
    )


def cmd_set_prod(args: argparse.Namespace) -> None:
    profiles = discover_profiles()
    prod = list(args.prod_profiles)
    unknown = [p for p in prod if p not in profiles]
    if unknown:
        raise SystemExit(f"Unknown profiles (not in ~/.aws): {unknown}. Known: {profiles}")

    existing: dict = {}
    if od_aws.brain_path().is_file():
        try:
            existing = json.loads(od_aws.brain_path().read_text())
        except json.JSONDecodeError:
            existing = {}

    brain = {
        **existing,
        "version": 1,
        "auth_mode": args.auth_mode,
        "region_default": args.region or existing.get("region_default") or "us-east-1",
        "profiles": profiles,
        "prod_profiles": prod,
        "vault_command": args.vault or existing.get("vault_command") or "aws-vault",
    }
    path = od_aws.save_brain(brain)
    od_aws.emit({"saved": str(path), "brain": brain})


def cmd_show(_: argparse.Namespace) -> None:
    od_aws.emit({"brain_path": str(od_aws.brain_path()), "brain": od_aws.load_brain()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Discover AWS profiles and brain status")
    p_list.set_defaults(func=cmd_list)

    p_set = sub.add_parser("set-prod", help="Save which profiles are prod-class")
    p_set.add_argument("prod_profiles", nargs="+", help="Profile name(s) treated as prod")
    p_set.add_argument("--region", default="us-east-1")
    p_set.add_argument("--vault", default="aws-vault")
    p_set.add_argument(
        "--auth-mode",
        default="aws-vault",
        choices=["aws-vault", "aws-profile", "env"],
        help="How tools obtain AWS credentials",
    )
    p_set.set_defaults(func=cmd_set_prod)

    p_show = sub.add_parser("show", help="Print current brain")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
