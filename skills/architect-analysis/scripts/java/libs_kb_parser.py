import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_dependencies(pom_path: str) -> list[tuple[str, str, str, str]]:
    tree = ET.parse(pom_path)
    root = tree.getroot()
    ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    prefix = f"{{{ns}}}" if ns else ""

    # Collect properties for variable resolution
    props = {}
    props_el = root.find(f"{prefix}properties")
    if props_el is not None:
        for child in props_el:
            tag = child.tag.replace(f"{{{ns}}}", "") if ns else child.tag
            if child.text:
                props[tag] = child.text.strip()

    def resolve(text):
        if text and "${" in text:
            for k, v in props.items():
                text = text.replace(f"${{{k}}}", v)
        return text

    deps = []
    for dep in root.iter(f"{prefix}dependency"):
        group = dep.find(f"{prefix}groupId")
        artifact = dep.find(f"{prefix}artifactId")
        version_el = dep.find(f"{prefix}version")
        scope_el = dep.find(f"{prefix}scope")
        if group is not None and artifact is not None:
            version = resolve(version_el.text.strip()) if version_el is not None and version_el.text else None
            scope = scope_el.text.strip() if scope_el is not None and scope_el.text else "compile"
            deps.append((group.text.strip(), artifact.text.strip(), version, scope))
    return deps


def populate_kb(dependencies: list[tuple[str, str, str, str]], kb_dir: str):
    kb_path = Path(kb_dir)
    kb_path.mkdir(parents=True, exist_ok=True)

    for group, artifact, version, scope in dependencies:
        name = f"{group}.{artifact}"
        md_file = kb_path / f"{name}.md"
        if not md_file.exists():
            md_file.write_text(f"what is {name}? write a short guide about how to use it.\n")
            print(f"created: {md_file}")
        else:
            print(f"skipped: {md_file}")


import json

CATEGORY_RULES = [
    # (category, match patterns on groupId or artifactId)
    ("frameworks", ["org.springframework.boot", "org.springframework.cloud", "io.awspring.cloud",
                     "org.springframework.data", "spring-boot-starter", "spring-cloud"]),
    ("datastores", ["data-redis", "data-mongodb", "data-jpa", "data-dynamodb", "hapi-fhir",
                     "mongo", "dynamodb", "redis", "cassandra", "elasticsearch", "jdbc"]),
    ("security",   ["security", "keycloak", "oauth2", "jwt"]),
    ("caching",    ["caffeine", "ehcache", "cache"]),
    ("testing",    ["test", "junit", "mockito", "wiremock", "awaitility", "pact",
                     "assertj", "hamcrest", "testcontainers"]),
    ("integration",["httpclient", "resttemplate", "webclient", "feign", "jackson",
                     "gson", "okhttp", "retrofit"]),
]


def classify_dependency(group: str, artifact: str, scope: str) -> str:
    if scope == "test":
        return "testing"
    full = f"{group}.{artifact}".lower()
    for category, patterns in CATEGORY_RULES:
        for pat in patterns:
            if pat.lower() in full:
                return category
    return "utilities"


def write_metadata(dependencies: list[tuple[str, str, str, str]], kb_dir: str):
    """Write a libs-metadata.json with version, scope, and category for each dependency."""
    kb_path = Path(kb_dir)
    categorized = {}
    for group, artifact, version, scope in dependencies:
        cat = classify_dependency(group, artifact, scope)
        categorized.setdefault(cat, []).append({
            "groupId": group,
            "artifactId": artifact,
            "version": version,
            "scope": scope,
        })
    meta_file = kb_path / "libs-metadata.json"
    meta_file.write_text(json.dumps(categorized, indent=2))
    print(f"metadata: {meta_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: libs_kb_parser.py <pom.xml> <kb_dir>")
        sys.exit(1)

    deps = parse_dependencies(sys.argv[1])
    populate_kb(deps, sys.argv[2])
    write_metadata(deps, sys.argv[2])
