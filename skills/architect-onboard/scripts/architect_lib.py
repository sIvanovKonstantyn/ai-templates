#!/usr/bin/env python3
"""Architect brain helpers (artifacts dir, reports root, stack)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    """Workspace root containing `.cursor/` (prefer cwd, then skill install path)."""
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        cursor = parent / ".cursor"
        if cursor.is_dir() and (cursor / "skills").is_dir():
            return parent

    here = Path(__file__).resolve()
    for parent in here.parents:
        # Installed as <ws>/.cursor/skills/architect-onboard/scripts/...
        if parent.name == "skills" and parent.parent.name == ".cursor":
            return parent.parent.parent

    raise SystemExit(
        "Cannot locate workspace root (.cursor/skills). "
        "Run from a project that has the kit installed under .cursor/."
    )


def brain_path() -> Path:
    return repo_root() / ".cursor" / "architect" / "brain.json"


def load_brain(*, allow_missing: bool = False) -> dict[str, Any]:
    path = brain_path()
    if not path.is_file():
        if allow_missing:
            return {}
        raise SystemExit(
            f"Architect brain missing: {path}\n"
            "Run the architect-onboard skill first."
        )
    with path.open() as f:
        return json.load(f)


def save_brain(brain: dict[str, Any]) -> Path:
    path = brain_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(brain, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def artifacts_dir(brain: dict[str, Any] | None = None) -> Path:
    brain = brain if brain is not None else load_brain()
    root = repo_root()
    rel = brain.get("artifacts_dir") or "artifacts"
    p = Path(rel)
    return p if p.is_absolute() else root / p


def reports_root(brain: dict[str, Any] | None = None) -> Path:
    brain = brain if brain is not None else load_brain()
    root = repo_root()
    rel = brain.get("reports_root") or "docs/architecture"
    p = Path(rel)
    return p if p.is_absolute() else root / p
