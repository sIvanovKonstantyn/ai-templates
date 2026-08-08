#!/usr/bin/env python3
"""Analyst onboard: write brain + CONTEXT.md; inventory docs roots."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_DOC_SCRIPTS = _HERE.parents[1] / "analyst-docs" / "scripts"
sys.path.insert(0, str(_DOC_SCRIPTS if _DOC_SCRIPTS.is_dir() else _HERE))

import analyst_lib  # noqa: E402


def cmd_write(args: argparse.Namespace) -> None:
    existing: dict[str, Any] = {}
    if analyst_lib.brain_path().is_file():
        existing = json.loads(analyst_lib.brain_path().read_text())

    docs_roots = list(args.docs_root or existing.get("docs_roots") or [])
    if not docs_roots:
        raise SystemExit("Provide at least one --docs-root")

    source_roots = list(args.source_root or existing.get("source_roots") or [])
    notes = list(existing.get("context_notes") or [])
    for n in args.note or []:
        notes.append(n)
    glossary = list(existing.get("glossary") or [])
    for g in args.glossary_term or []:
        glossary.append(g)

    naming = dict(existing.get("naming") or {})
    if args.naming_analysis:
        naming["analysis"] = args.naming_analysis
    if args.naming_review:
        naming["review"] = args.naming_review
    if args.naming_postmortem:
        naming["postmortem"] = args.naming_postmortem
    naming.setdefault("analysis", "{topic}-analysis.md")
    naming.setdefault("review", "{topic}-review-YYYY-MM-DD.md")
    naming.setdefault("postmortem", "{topic}-YYYY-MM-DD-postmortem.md")
    naming.setdefault("service", "{service}-service.md")
    naming.setdefault("guide", "{topic}-guide.md")

    product = args.product_name or existing.get("product_name")
    if not product:
        raise SystemExit("Provide --product-name")

    brain = {
        **existing,
        "version": 1,
        "product_name": product,
        "org_label": args.org_label or existing.get("org_label") or product,
        "docs_roots": docs_roots,
        "source_roots": source_roots,
        "naming": naming,
        "glossary": glossary,
        "context_notes": notes,
        "indexed_at": existing.get("indexed_at"),
        "last_inventory_path": existing.get("last_inventory_path"),
        "notes": f"Written by analyst-onboard at {datetime.now(timezone.utc).isoformat()}",
    }

    repo = analyst_lib.repo_root()
    for rel in docs_roots + source_roots:
        p = Path(rel) if Path(rel).is_absolute() else repo / rel
        if not p.exists():
            print(f"warning: path does not exist yet: {p}", file=sys.stderr)

    path = analyst_lib.save_brain(brain)
    context = _write_context(brain)
    print(
        json.dumps(
            {"saved": str(path), "context": str(context), "brain": brain},
            indent=2,
        )
    )


def _write_context(brain: dict[str, Any]) -> Path:
    path = analyst_lib.repo_root() / ".cursor" / "analyst" / "CONTEXT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {brain.get('org_label') or brain.get('product_name')} — analyst context",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**Product:** {brain.get('product_name')}",
        "",
        "## Docs roots",
        "",
    ]
    for r in brain.get("docs_roots") or []:
        lines.append(f"- `{r}`")
    if brain.get("source_roots"):
        lines.extend(["", "## Source / vendor roots", ""])
        for r in brain["source_roots"]:
            lines.append(f"- `{r}`")
    if brain.get("context_notes"):
        lines.extend(["", "## Notes", ""])
        for n in brain["context_notes"]:
            lines.append(f"- {n}")
    if brain.get("glossary"):
        lines.extend(["", "## Glossary", ""])
        for g in brain["glossary"]:
            lines.append(f"- {g}")
    lines.extend(
        [
            "",
            "## Naming",
            "",
            "```json",
            json.dumps(brain.get("naming") or {}, indent=2),
            "```",
            "",
            "No secrets belong in this file. Update via analyst-onboard.",
            "",
        ]
    )
    path.write_text("\n".join(lines))
    return path


def cmd_inventory(_: argparse.Namespace) -> None:
    brain = analyst_lib.load_brain()
    index_script = _DOC_SCRIPTS / "docs_index.py"
    if not index_script.is_file():
        raise SystemExit(f"Missing {index_script}")
    out_path = analyst_lib.repo_root() / ".cursor" / "analyst" / "last_inventory.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(index_script), "--json", "--include-pdf"],
        capture_output=True,
        text=True,
        cwd=str(analyst_lib.repo_root()),
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout or "docs_index failed")
    out_path.write_text(proc.stdout)
    brain["indexed_at"] = datetime.now(timezone.utc).isoformat()
    brain["last_inventory_path"] = str(out_path.relative_to(analyst_lib.repo_root()))
    analyst_lib.save_brain(brain)
    data = json.loads(proc.stdout)
    print(
        json.dumps(
            {
                "indexed_at": brain["indexed_at"],
                "last_inventory_path": brain["last_inventory_path"],
                "count": data.get("count"),
                "roots": data.get("roots"),
            },
            indent=2,
        )
    )


def cmd_show(_: argparse.Namespace) -> None:
    print(
        json.dumps(
            {"brain_path": str(analyst_lib.brain_path()), "brain": analyst_lib.load_brain()},
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_write = sub.add_parser("write", help="Write analyst brain + CONTEXT.md")
    p_write.add_argument("--product-name", default=None)
    p_write.add_argument("--org-label", default=None)
    p_write.add_argument("--docs-root", action="append", default=None)
    p_write.add_argument("--source-root", action="append", default=None)
    p_write.add_argument("--note", action="append", default=None)
    p_write.add_argument("--glossary-term", action="append", default=None)
    p_write.add_argument("--naming-analysis", default=None)
    p_write.add_argument("--naming-review", default=None)
    p_write.add_argument("--naming-postmortem", default=None)
    p_write.set_defaults(func=cmd_write)

    p_inv = sub.add_parser("inventory", help="Index docs roots into last_inventory.json")
    p_inv.set_defaults(func=cmd_inventory)

    p_show = sub.add_parser("show", help="Print brain")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
