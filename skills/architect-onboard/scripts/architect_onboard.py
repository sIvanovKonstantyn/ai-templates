#!/usr/bin/env python3
"""Architect onboard: write .cursor/architect/brain.json (+ short CONTEXT.md)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import architect_lib  # noqa: E402


def cmd_write(args: argparse.Namespace) -> None:
    existing: dict[str, Any] = {}
    if architect_lib.brain_path().is_file():
        existing = json.loads(architect_lib.brain_path().read_text())

    product = args.product_name or existing.get("product_name")
    if not product:
        raise SystemExit("Provide --product-name")

    brain = {
        **existing,
        "version": 1,
        "product_name": product,
        "org_label": args.org_label or existing.get("org_label") or product,
        "default_stack": args.default_stack
        or existing.get("default_stack")
        or "java",
        "artifacts_dir": args.artifacts_dir
        or existing.get("artifacts_dir")
        or "artifacts",
        "reports_root": args.reports_root
        or existing.get("reports_root")
        or "docs/architecture",
        "java_source_hint": args.java_source_hint
        or existing.get("java_source_hint")
        or "src/main/java",
        "notes": f"Written by architect-onboard at {datetime.now(timezone.utc).isoformat()}",
    }

    path = architect_lib.save_brain(brain)
    context = _write_context(brain)
    # Ensure dirs exist when requested
    if args.ensure_dirs:
        architect_lib.artifacts_dir(brain).mkdir(parents=True, exist_ok=True)
        architect_lib.reports_root(brain).mkdir(parents=True, exist_ok=True)

    print(
        json.dumps(
            {"saved": str(path), "context": str(context), "brain": brain},
            indent=2,
        )
    )


def _write_context(brain: dict[str, Any]) -> Path:
    path = architect_lib.repo_root() / ".cursor" / "architect" / "CONTEXT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {brain.get('org_label') or brain.get('product_name')} — architect context",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**Product:** {brain.get('product_name')}",
        f"**Default stack:** {brain.get('default_stack')}",
        "",
        "## Paths",
        "",
        f"- Artifacts: `{brain.get('artifacts_dir')}`",
        f"- Reports: `{brain.get('reports_root')}`",
        f"- Java sources hint: `{brain.get('java_source_hint')}`",
        "",
        "Use `architect-analysis` for full STEPs 1–7 reports.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cmd_show(_: argparse.Namespace) -> None:
    brain = architect_lib.load_brain()
    print(json.dumps(brain, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="Write brain + CONTEXT.md")
    w.add_argument("--product-name")
    w.add_argument("--org-label")
    w.add_argument("--default-stack", default=None)
    w.add_argument("--artifacts-dir", default=None)
    w.add_argument("--reports-root", default=None)
    w.add_argument("--java-source-hint", default=None)
    w.add_argument(
        "--ensure-dirs",
        action="store_true",
        help="Create artifacts_dir and reports_root if missing",
    )
    w.set_defaults(func=cmd_write)

    s = sub.add_parser("show", help="Print current brain")
    s.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
