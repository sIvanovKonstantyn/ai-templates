#!/usr/bin/env python3
"""Scaffold an ADS Solution Architecture Document from the kit template."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "solution"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solution", required=True, help="Solution / application name")
    parser.add_argument("--org", default="", help="Organisation name")
    parser.add_argument(
        "--depth",
        default="recommended",
        choices=("minimum", "recommended", "comprehensive"),
    )
    parser.add_argument("--application-id", default="TBD")
    parser.add_argument("--author", default="TBD")
    parser.add_argument("--owner", default="")
    parser.add_argument("--classification", default="internal")
    parser.add_argument("--version", default="0.1")
    parser.add_argument("--status", default="Draft")
    parser.add_argument(
        "--out",
        default="",
        help="Output path (default: ./{slug}-sad.md)",
    )
    parser.add_argument(
        "--template",
        default="",
        help="Override template path",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    template_path = (
        Path(args.template)
        if args.template
        else skill_root / "assets" / "sad-template.md"
    )
    if not template_path.is_file():
        raise SystemExit(f"Template not found: {template_path}")

    today = date.today().isoformat()
    owner = args.owner or args.author
    replacements = {
        "{{SOLUTION_NAME}}": args.solution,
        "{{ORG_NAME}}": args.org or "TBD",
        "{{DEPTH}}": args.depth,
        "{{BRIEF_OR_LINKS}}": "TBD",
        "{{APPLICATION_ID}}": args.application_id,
        "{{AUTHORS}}": args.author,
        "{{OWNER}}": owner,
        "{{VERSION}}": args.version,
        "{{STATUS}}": args.status,
        "{{CREATED_DATE}}": today,
        "{{LAST_UPDATED}}": today,
        "{{CLASSIFICATION}}": args.classification,
        "{{DOCUMENT_PURPOSE}}": (
            f"This SAD describes the architecture of **{args.solution}** "
            f"for **{args.org or 'TBD'}**. Content pending stakeholder input."
        ),
        "{{SOLUTION_OVERVIEW}}": "TBD — pending architecture inputs.",
        "{{AS_IS_ARCHITECTURE}}": "TBD — pending as-is assessment.",
        "{{PROJECT_NAME}}": args.solution,
        "{{PROJECT_ID}}": "TBD",
    }

    text = template_path.read_text(encoding="utf-8")
    for key, val in replacements.items():
        text = text.replace(key, val)

    out = Path(args.out) if args.out else Path(f"{_slug(args.solution)}-sad.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
