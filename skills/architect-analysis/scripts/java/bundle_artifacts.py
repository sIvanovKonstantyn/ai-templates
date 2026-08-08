#!/usr/bin/env python3
"""
Merge summary, config, libs listing, and issues-hints into a single
analysis-bundle.json for single-read consumption.

Usage:
    python bundle_artifacts.py \
        --summary      artifacts/<svc>-summary.json \
        --config       artifacts/<svc>-config.json \
        --issues-hints artifacts/<svc>-issues-hints.json \
        --libs-dir     artifacts/libs-kb/ \
        --output       artifacts/<svc>-analysis-bundle.json
"""

import argparse
import json
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def list_libs(libs_dir: str) -> dict:
    """Load categorized library metadata from libs-metadata.json.
    Falls back to flat file listing if metadata doesn't exist."""
    p = Path(libs_dir)
    meta_file = p / "libs-metadata.json"
    if meta_file.exists():
        with open(meta_file) as f:
            return json.load(f)
    # Fallback: flat list from filenames (legacy behavior)
    if not p.exists():
        return {"utilities": []}
    libs = []
    for f in sorted(p.glob("*.md")):
        name = f.stem
        parts = name.split(".")
        group_parts = []
        artifact_parts = []
        found_artifact = False
        for i, part in enumerate(parts):
            if not found_artifact and "-" in part:
                found_artifact = True
            if found_artifact:
                artifact_parts.append(part)
            else:
                group_parts.append(part)
        if not artifact_parts:
            artifact_parts = [parts[-1]]
            group_parts = parts[:-1]
        libs.append({
            "groupId": ".".join(group_parts),
            "artifactId": ".".join(artifact_parts),
        })
    return {"utilities": libs}


def main():
    parser = argparse.ArgumentParser(description="Bundle analysis artifacts")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--issues-hints", required=True)
    parser.add_argument("--libs-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    bundle = {
        "summary": load_json(args.summary),
        "config": load_json(args.config),
        "issuesHints": load_json(args.issues_hints),
        "libraries": list_libs(args.libs_dir),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(bundle, f, indent=2)
    print(f"Analysis bundle written to: {out}")


if __name__ == "__main__":
    main()
