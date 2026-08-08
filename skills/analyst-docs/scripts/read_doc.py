#!/usr/bin/env python3
"""Unified document reader for Analyst (PDF + text-like files).

Examples:
  read_doc.py docs/overview.md
  read_doc.py "docs/Vendor Spec.pdf" --pages 1-3
  read_doc.py docs/service-graph.json --max-chars 4000
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TEXT_EXTS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".csv",
    ".json",
    ".yml",
    ".yaml",
    ".log",
    ".xml",
    ".html",
    ".htm",
    ".tsv",
}


def _pdf_python() -> Path:
    here = Path(__file__).resolve().parent
    venv_py = here / ".venv" / "bin" / "python"
    return venv_py if venv_py.is_file() else Path(sys.executable)


def read_pdf(path: Path, pages: str | None, as_json: bool) -> int:
    script = Path(__file__).resolve().parent / "pdf_extract.py"
    cmd = [str(_pdf_python()), str(script), str(path)]
    if pages:
        cmd.extend(["--pages", pages])
    if as_json:
        cmd.append("--json")
    return subprocess.call(cmd)


def read_text(path: Path, max_chars: int | None, as_json: bool) -> int:
    raw = path.read_text(encoding="utf-8", errors="replace")
    truncated = False
    if max_chars is not None and len(raw) > max_chars:
        raw = raw[:max_chars]
        truncated = True
    if as_json:
        json.dump(
            {
                "path": str(path.resolve()),
                "ext": path.suffix.lower(),
                "chars": len(raw),
                "truncated": truncated,
                "text": raw,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0
    print(f"path={path.resolve()} chars={len(raw)} truncated={truncated}")
    print()
    sys.stdout.write(raw)
    if not raw.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="File to read")
    ap.add_argument("--pages", help="PDF only: 1-based page range (passed to pdf_extract)")
    ap.add_argument("--max-chars", type=int, help="Text only: truncate after N characters")
    ap.add_argument("--json", action="store_true", help="Structured JSON output")
    args = ap.parse_args()

    path: Path = args.path
    if not path.is_file():
        raise SystemExit(f"Not a file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raise SystemExit(read_pdf(path, args.pages, args.json))

    if suffix in TEXT_EXTS or suffix == "":
        raise SystemExit(read_text(path, args.max_chars, args.json))

    raise SystemExit(
        f"Unsupported extension '{suffix}'. "
        f"v1 supports PDF and {', '.join(sorted(TEXT_EXTS))}. "
        "Extend analyst-docs for other formats."
    )


if __name__ == "__main__":
    main()
