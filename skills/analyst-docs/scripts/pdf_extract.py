#!/usr/bin/env python3
"""Extract text from a PDF using pypdf (skill-local .venv).

Examples:
  pdf_extract.py docs/spec.pdf
  pdf_extract.py docs/spec.pdf --pages 1-5
  pdf_extract.py docs/spec.pdf --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_pypdf():
    try:
        from pypdf import PdfReader  # noqa: F401

        return
    except ImportError:
        pass
    here = Path(__file__).resolve().parent
    venv_py = here / ".venv" / "bin" / "python"
    tip = (
        f"pypdf not installed for this interpreter ({sys.executable}).\n"
        f"Bootstrap once:\n"
        f"  python3 -m venv {here}/.venv && "
        f"{here}/.venv/bin/pip install -r {here}/requirements.txt\n"
        f"Then re-run with:\n"
        f"  {venv_py} {Path(__file__).name} ...\n"
    )
    raise SystemExit(tip)


def _parse_pages(spec: str | None, page_count: int) -> list[int]:
    """Return 0-based page indices from a 1-based spec like '1-3,5'."""
    if not spec:
        return list(range(page_count))
    indices: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start < 1 or end < start:
                raise SystemExit(f"Invalid page range: {part}")
            indices.extend(range(start - 1, end))
        else:
            n = int(part)
            if n < 1:
                raise SystemExit(f"Invalid page: {part}")
            indices.append(n - 1)
    out = []
    for i in indices:
        if i >= page_count:
            raise SystemExit(f"Page {i + 1} out of range (PDF has {page_count} pages)")
        out.append(i)
    return out


def extract(path: Path, pages_spec: str | None) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    n = len(reader.pages)
    idxs = _parse_pages(pages_spec, n)
    pages_out = []
    for i in idxs:
        text = reader.pages[i].extract_text() or ""
        pages_out.append({"page": i + 1, "text": text})
    return {
        "path": str(path.resolve()),
        "page_count": n,
        "extracted_pages": [p["page"] for p in pages_out],
        "pages": pages_out,
    }


def main() -> None:
    _ensure_pypdf()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="PDF file path")
    ap.add_argument(
        "--pages",
        help="1-based page selection, e.g. 1-5 or 1,3,8-10 (default: all)",
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")
    args = ap.parse_args()
    path: Path = args.path
    if not path.is_file():
        raise SystemExit(f"Not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected a .pdf file, got: {path.suffix}")

    data = extract(path, args.pages)
    if args.json:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    print(f"pages={data['page_count']} path={data['path']}")
    for block in data["pages"]:
        print(f"\n===== PAGE {block['page']} =====\n")
        print(block["text"].rstrip())
        print()


if __name__ == "__main__":
    main()
