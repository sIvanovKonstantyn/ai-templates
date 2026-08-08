#!/usr/bin/env python3
"""Parse Spring Boot and deployment configuration files."""
import argparse, json, re, sys
from pathlib import Path
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

def find_config_files(source):
    patterns = {
        "spring": ["src/main/resources/application*.yml", "src/main/resources/application*.yaml",
                    "src/main/resources/application*.properties", "src/main/resources/bootstrap*.yml"],
        "deployment": ["appconfig/values*.yaml", "appconfig/values*.yml"],
        "docker": ["Dockerfile", "docker-compose*.yml"],
    }
    found = {}
    for cat, globs in patterns.items():
        files = []
        for g in globs:
            files.extend(sorted(source.glob(g)))
        if files:
            found[cat] = [str(f.relative_to(source)) for f in files]
    return found

def _parse_yaml_basic(path):
    result, stack, indent_stack = {}, [None], [-1]
    stack[0] = result
    with open(path) as f:
        for line in f:
            s = line.rstrip()
            if not s or s.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            c = s.lstrip()
            if ":" not in c:
                continue
            while len(indent_stack) > 1 and indent <= indent_stack[-1]:
                indent_stack.pop()
                stack.pop()
            key, _, val = c.partition(":")
            key, val = key.strip(), val.strip().strip("'\"")
            if val:
                stack[-1][key] = val
            else:
                d = {}
                stack[-1][key] = d
                stack.append(d)
                indent_stack.append(indent)
    return result

def load_yaml_safe(path):
    try:
        if HAS_YAML:
            with open(path) as f:
                d = yaml.safe_load(f)
                return d if isinstance(d, dict) else {}
        return _parse_yaml_basic(path)
    except Exception:
        return {}

def load_properties(path):
    props = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
    except Exception:
        pass
    return props

def flatten_dict(d, prefix=""):
    items = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, key))
        else:
            items[key] = v
    return items

_SENSITIVE = re.compile(r"(password|secret|token|key|credential|api[_-]?key)", re.I)

def redact(flat):
    return {k: "[REDACTED]" if _SENSITIVE.search(k) else v for k, v in flat.items()}

def extract_profiles(source):
    profiles = {}
    for f in sorted(source.glob("src/main/resources/application*.yml")):
        name = f.stem.replace("application-", "").replace("application", "default")
        profiles[name] = redact(flatten_dict(load_yaml_safe(f)))
    for f in sorted(source.glob("src/main/resources/application*.properties")):
        name = f.stem.replace("application-", "").replace("application", "default")
        profiles[name] = redact(load_properties(f))
    return profiles

def extract_feature_flags(profiles):
    flags = {}
    pats = ["featureflag", "feature-flag", "feature_flag", "toggle", "enabled"]
    for pname, flat in profiles.items():
        for k, v in flat.items():
            if any(p in k.lower() for p in pats):
                flags.setdefault(k, {})[pname] = v
    return flags

def extract_external_services(profiles):
    url_re = re.compile(r"(url|uri|host|endpoint|base-url|api)", re.I)
    services, seen = [], set()
    for pname, flat in profiles.items():
        for k, v in flat.items():
            if url_re.search(k) and isinstance(v, str) and v != "[REDACTED]":
                ident = f"{k}={v}"
                if ident not in seen:
                    seen.add(ident)
                    services.append({"key": k, "value": v, "profile": pname})
    return services


def build_diff_based_config(profiles):
    """Build a base + per-profile overrides structure instead of repeating all keys."""
    if not profiles:
        return {"base": {}, "overrides": {}}

    profile_names = sorted(profiles.keys())
    # Use 'default' as base if it exists, otherwise the first profile
    base_name = "default" if "default" in profiles else profile_names[0]
    base = dict(profiles.get(base_name, {}))

    overrides = {}
    for pname in profile_names:
        if pname == base_name:
            continue
        flat = profiles[pname]
        diff = {}
        for k, v in flat.items():
            if k not in base or str(base[k]) != str(v):
                diff[k] = v
        # Only flag removals for keys that are NOT profile-specific defaults
        # (skip null entries — they just mean the override profile has a narrower scope)
        if diff:
            overrides[pname] = diff

    return {"baseProfile": base_name, "base": base, "overrides": overrides}

def extract_infrastructure(profiles):
    infra = {"databases": [], "cache": [], "messaging": []}
    rules = [
        ("databases", ["mongodb", "dynamodb", "datasource", "jpa", "hibernate", "cdr"]),
        ("cache", ["cache", "caffeine"]),
        ("messaging", ["kafka", "rabbit", "redis", "event"]),
    ]
    for pname, flat in profiles.items():
        for k, v in flat.items():
            kl = k.lower()
            for cat, keys in rules:
                if any(dk in kl for dk in keys):
                    infra[cat].append({"key": k, "value": v, "profile": pname})
                    break
    for cat in infra:
        seen, deduped = set(), []
        for item in infra[cat]:
            uid = f"{item['key']}|{item['profile']}"
            if uid not in seen:
                seen.add(uid)
                deduped.append(item)
        infra[cat] = deduped
    return infra

def extract_deployment(source):
    envs = {}
    for f in sorted(source.glob("appconfig/values*.yaml")):
        name = f.stem.replace("values.", "").replace("values", "default")
        envs[name] = redact(flatten_dict(load_yaml_safe(f)))
    return envs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    source = Path(args.source)
    profiles = extract_profiles(source)
    diff_config = build_diff_based_config(profiles)
    result = {
        "configFiles": find_config_files(source),
        "profiles": list(profiles.keys()),
        "config": diff_config,
        "featureFlags": extract_feature_flags(profiles),
        "infrastructure": extract_infrastructure(profiles),
        "deployment": extract_deployment(source),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Config analysis written to: {out}")

if __name__ == "__main__":
    main()
