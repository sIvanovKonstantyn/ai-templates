#!/usr/bin/env python3
"""Inventory markdown/text docs under configured roots.

Examples:
  docs_index.py
  docs_index.py --query billing
  docs_index.py --json
  docs_index.py --root docs --ext .md,.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import analyst_lib

TEXT_EXTS = {".md", ".txt", ".markdown", ".rst", ".csv", ".json", ".yml", ".yaml", ".log"}
BINARY_HINTS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".docx", ".xlsx", ".zip"}


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return re.sub(r"^#+\s*", "", s).strip() or None
    return None


def _snippet(text: str, query: str | None, limit: int = 160) -> str:
    flat = " ".join(text.split())
    if not query:
        return flat[:limit]
    q = query.lower()
    lower = flat.lower()
    idx = lower.find(q)
    if idx < 0:
        return flat[:limit]
    start = max(0, idx - 40)
    return flat[start : start + limit]


def index_docs(
    root: Path,
    *,
    exts: set[str],
    query: str | None,
    include_pdf: bool,
    repo: Path,
) -> list[dict]:
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    rows: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        suffix = path.suffix.lower()
        if suffix in BINARY_HINTS and not (include_pdf and suffix == ".pdf"):
            continue
        if suffix not in exts and not (include_pdf and suffix == ".pdf"):
            continue

        try:
            repo_rel = str(path.relative_to(repo))
        except ValueError:
            repo_rel = str(path)

        title = path.stem
        snippet = ""
        size = path.stat().st_size
        if suffix == ".pdf":
            title = path.name
            snippet = f"(PDF, {size} bytes — use pdf_extract.py to read)"
            hay = f"{path.name} {title}".lower()
        else:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                snippet = f"(unreadable: {exc})"
                text = ""
            heading = _first_heading(text) if text else None
            if heading:
                title = heading
            snippet = _snippet(text, query) if text else snippet
            hay = f"{path.name} {title} {text[:4000]}".lower()

        if query and query.lower() not in hay:
            continue

        rows.append(
            {
                "path": repo_rel,
                "name": path.name,
                "title": title,
                "ext": suffix or "",
                "bytes": size,
                "snippet": snippet,
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Single docs root (default: all brain docs_roots)",
    )
    ap.add_argument(
        "--ext",
        default=",".join(sorted(TEXT_EXTS)),
        help="Comma-separated extensions to include",
    )
    ap.add_argument("--query", "-q", help="Case-insensitive filter on name/title/body")
    ap.add_argument("--json", action="store_true", help="JSON array to stdout")
    ap.add_argument(
        "--include-pdf",
        action="store_true",
        help="List PDFs in the index (metadata only)",
    )
    ap.add_argument(
        "--allow-missing-brain",
        action="store_true",
        help="If brain missing, fall back to ./docs under repo root",
    )
    args = ap.parse_args()

    repo = analyst_lib.repo_root()
    if args.root:
        roots = [args.root if args.root.is_absolute() else repo / args.root]
    else:
        try:
            roots = analyst_lib.docs_roots()
        except SystemExit:
            if not args.allow_missing_brain:
                raise
            roots = [repo / "docs"]

    exts = {
        e.strip().lower() if e.strip().startswith(".") else f".{e.strip().lower()}"
        for e in args.ext.split(",")
        if e.strip()
    }

    all_rows: list[dict] = []
    for root in roots:
        all_rows.extend(
            index_docs(
                root,
                exts=exts,
                query=args.query,
                include_pdf=args.include_pdf,
                repo=repo,
            )
        )

    if args.json:
        json.dump(
            {"roots": [str(r) for r in roots], "count": len(all_rows), "docs": all_rows},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return

    print(f"roots={','.join(str(r) for r in roots)} count={len(all_rows)}")
    for r in all_rows:
        print(f"- {r['path']}")
        print(f"  title: {r['title']}")
        if r["snippet"]:
            print(f"  note:  {r['snippet'][:140]}")


if __name__ == "__main__":
    main()
