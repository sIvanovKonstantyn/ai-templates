#!/usr/bin/env python3
"""
Deterministic Gradle dependency extractor for project-analysis.

Creates artifacts compatible with bundle_artifacts.py:
- <kb_dir>/libs-metadata.json (categorized deps with version + scope)
- optional stub .md files (mirrors libs_kb_parser.py behavior)

Supports simple Gradle Groovy patterns commonly used in this repo:
- ext { key = 'value' } for ${key} interpolation
- dependencies { implementation("g:a:v"), api("g:a:v"), testImplementation(...), runtimeOnly(...), classpath(...) }
- string notations with/without parentheses; single or double quotes
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEP_RE = re.compile(
    r"""^\s*
        (?P<conf>[A-Za-z_][A-Za-z0-9_]*)
        \s*
        (?:\(\s*)?
        (?P<q>['"])
        (?P<gav>[^'"]+)
        (?P=q)
        (?:\s*\))?
        \s*$
    """,
    re.VERBOSE,
)

EXT_KV_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]([^'\"]*)['\"]\s*$")
INTERP_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


CATEGORY_RULES = [
    ("frameworks", ["org.springframework.boot", "org.springframework.cloud", "spring-boot", "spring-cloud", "thymeleaf"]),
    ("datastores", ["elasticsearch", "mongodb", "redis", "dynamodb", "jdbc", "hibernate"]),
    ("security", ["security", "keycloak", "oauth2", "jwt"]),
    ("caching", ["caffeine", "ehcache", "cache"]),
    ("testing", ["test", "junit", "mockito", "wiremock", "awaitility", "pact", "assertj", "hamcrest", "testcontainers", "cobertura", "spotbugs"]),
    ("integration", ["hystrix", "retry", "websocket", "httpclient", "okhttp", "retrofit", "feign", "jackson", "gson"]),
]


def _classify(group: str, artifact: str, scope: str) -> str:
    if scope.lower().startswith("test"):
        return "testing"
    full = f"{group}.{artifact}".lower()
    for cat, pats in CATEGORY_RULES:
        for p in pats:
            if p.lower() in full:
                return cat
    return "utilities"


def _resolve_interpolation(s: str, props: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return props.get(key, m.group(0))
    return INTERP_RE.sub(repl, s)


def _parse_ext_props(text: str) -> dict[str, str]:
    """
    Parse ext { ... } blocks for key = 'value' assignments.
    This is intentionally simple/deterministic (no Groovy evaluation).
    """
    props: dict[str, str] = {}
    in_ext = False
    brace_depth = 0
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].rstrip()
        if not line:
            continue
        if not in_ext:
            if re.search(r"\bext\s*\{", line):
                in_ext = True
                brace_depth = line.count("{") - line.count("}")
            continue
        else:
            brace_depth += line.count("{") - line.count("}")
            m = EXT_KV_RE.match(line)
            if m:
                props[m.group(1)] = m.group(2)
            if brace_depth <= 0:
                in_ext = False
    return props


def _parse_dependencies(text: str, props: dict[str, str]) -> list[dict]:
    deps: list[dict] = []
    in_deps = False
    brace_depth = 0
    for raw in text.splitlines():
        # Strip inline comments (best-effort; keeps determinism)
        line = raw.split("//", 1)[0].rstrip()
        if not line:
            continue

        if not in_deps:
            if re.search(r"\bdependencies\s*\{", line):
                in_deps = True
                brace_depth = line.count("{") - line.count("}")
            continue

        brace_depth += line.count("{") - line.count("}")
        if brace_depth <= 0:
            in_deps = False
            continue

        m = DEP_RE.match(line)
        if not m:
            continue

        conf = m.group("conf")
        gav = _resolve_interpolation(m.group("gav").strip(), props)

        # Keep only plain GAV coordinates: group:artifact[:version]
        parts = [p.strip() for p in gav.split(":")]
        if len(parts) < 2:
            continue

        group = parts[0]
        artifact = parts[1]
        version = parts[2] if len(parts) >= 3 and parts[2] else None

        deps.append(
            {
                "groupId": group,
                "artifactId": artifact,
                "version": version,
                "scope": conf,
            }
        )
    return deps


def _write_kb_stubs(deps: list[dict], kb_dir: Path) -> None:
    kb_dir.mkdir(parents=True, exist_ok=True)
    for d in deps:
        name = f"{d['groupId']}.{d['artifactId']}"
        md = kb_dir / f"{name}.md"
        if not md.exists():
            md.write_text(f"what is {name}? write a short guide about how to use it.\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gradle_file", help="Path to build.gradle")
    ap.add_argument("kb_dir", help="Output directory (e.g., artifacts/libs-kb/)")
    ap.add_argument("--no-stubs", action="store_true", help="Do not create .md stub files")
    args = ap.parse_args()

    gradle_path = Path(args.gradle_file)
    kb_dir = Path(args.kb_dir)

    text = gradle_path.read_text(encoding="utf-8", errors="replace")
    props = _parse_ext_props(text)
    deps = _parse_dependencies(text, props)

    categorized: dict[str, list[dict]] = {}
    for d in deps:
        cat = _classify(d["groupId"], d["artifactId"], d["scope"])
        categorized.setdefault(cat, []).append(d)

    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "libs-metadata.json").write_text(json.dumps(categorized, indent=2))

    if not args.no_stubs:
        _write_kb_stubs(deps, kb_dir)


if __name__ == "__main__":
    main()

