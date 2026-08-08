#!/usr/bin/env python3
"""Analyst brain helpers (docs roots, product label)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".cursor").is_dir():
            return parent
    return here.parents[3]


def brain_path() -> Path:
    return repo_root() / ".cursor" / "analyst" / "brain.json"


def load_brain() -> dict[str, Any]:
    path = brain_path()
    if not path.is_file():
        raise SystemExit(
            f"Analyst brain missing: {path}\n"
            "Run the analyst-onboard skill first."
        )
    with path.open() as f:
        brain = json.load(f)
    if not brain.get("docs_roots"):
        raise SystemExit(
            f"Analyst brain incomplete (docs_roots empty): {path}\n"
            "Re-run analyst-onboard."
        )
    return brain


def save_brain(brain: dict[str, Any]) -> Path:
    path = brain_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(brain, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def docs_roots(brain: dict[str, Any] | None = None) -> list[Path]:
    brain = brain or load_brain()
    root = repo_root()
    out: list[Path] = []
    for item in brain.get("docs_roots") or []:
        p = Path(item)
        if not p.is_absolute():
            p = root / p
        out.append(p)
    return out


def product_name(brain: dict[str, Any] | None = None) -> str:
    brain = brain or load_brain()
    return str(brain.get("product_name") or brain.get("org_label") or "the product")
