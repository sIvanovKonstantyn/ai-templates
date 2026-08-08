#!/usr/bin/env python3
"""
Pre-generate deterministic issue hints from analysis artifacts.

Reduces LLM reasoning by flagging known anti-patterns and thresholds
directly from the data.

Usage:
    python generate_issues_hints.py \
        --summary  artifacts/<svc>-summary.json \
        --config   artifacts/<svc>-config.json \
        --output   artifacts/<svc>-issues-hints.json
"""

import argparse
import json
from pathlib import Path

# --- Thresholds ---
FAN_OUT_THRESHOLD = 15
FAN_IN_THRESHOLD = 20
UNKNOWN_RATIO_THRESHOLD = 0.25
FLOW_DEPTH_THRESHOLD = 6


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def check_god_classes(summary: dict) -> list:
    """Flag nodes with fan-out above threshold."""
    hints = []
    for item in summary.get("graph", {}).get("topFanOut", []):
        if item["count"] >= FAN_OUT_THRESHOLD:
            hints.append({
                "type": "god_class",
                "severity": "high",
                "node": item["node"],
                "fanOut": item["count"],
                "message": f"{item['node']} has {item['count']} outgoing calls (threshold: {FAN_OUT_THRESHOLD})"
            })
    return hints


def check_dependency_magnets(summary: dict) -> list:
    """Flag nodes with fan-in above threshold."""
    hints = []
    for item in summary.get("graph", {}).get("topFanIn", []):
        if item["count"] >= FAN_IN_THRESHOLD:
            hints.append({
                "type": "dependency_magnet",
                "severity": "high",
                "node": item["node"],
                "fanIn": item["count"],
                "message": f"{item['node']} has {item['count']} incoming calls (threshold: {FAN_IN_THRESHOLD})"
            })
    return hints


def check_get_state_changing(summary: dict) -> list:
    """Flag GET endpoints whose method name suggests state mutation."""
    hints = []
    # Only check method names — path segments like "queue-size" are too noisy
    action_words = [
        "add", "create", "send", "delete", "remove", "update", "submit",
        "trigger", "execute", "run", "start", "stop", "reset", "clear",
        "publish", "push", "export", "import", "process",
    ]
    rest_eps = summary.get("entrypoints", {}).get("byType", {}).get("REST", {}).get("endpoints", [])
    for ep in rest_eps:
        if ep.get("httpMethod", "").upper() != "GET":
            continue
        method = (ep.get("method") or "").lower()
        matched = [w for w in action_words if w in method]
        if matched:
            hints.append({
                "type": "get_state_changing",
                "severity": "medium",
                "endpoint": f"GET {ep.get('path')}",
                "class": ep.get("class"),
                "method": ep.get("method"),
                "matchedWords": matched,
                "message": f"GET {ep.get('path')} ({ep.get('class')}.{ep.get('method')}) appears state-changing: {', '.join(matched)}"
            })
    return hints


def check_unresolved_http_targets(summary: dict) -> list:
    """Flag unresolved outgoing HTTP targets."""
    hints = []
    http = summary.get("httpDependencies", {})
    total = http.get("total", 0)
    unresolved = http.get("unresolvedTargets", 0)
    if unresolved > 0:
        hints.append({
            "type": "unresolved_http_targets",
            "severity": "medium",
            "total": total,
            "unresolved": unresolved,
            "ratio": round(unresolved / total, 2) if total else 0,
            "message": f"{unresolved}/{total} outgoing HTTP targets are unresolved"
        })
    return hints


def check_unknown_nodes(summary: dict) -> list:
    """Flag high ratio of UNKNOWN-typed nodes."""
    hints = []
    nodes_by_type = summary.get("graph", {}).get("nodesByType", {})
    total = summary.get("graph", {}).get("totalNodes", 0)
    unknown_count = nodes_by_type.get("UNKNOWN", {}).get("count", 0)
    if total > 0:
        ratio = unknown_count / total
        if ratio >= UNKNOWN_RATIO_THRESHOLD:
            hints.append({
                "type": "high_unknown_ratio",
                "severity": "low",
                "unknownCount": unknown_count,
                "totalNodes": total,
                "ratio": round(ratio, 2),
                "message": f"{unknown_count}/{total} nodes ({round(ratio*100)}%) are UNKNOWN type"
            })
    return hints


def check_recursive_and_circular(summary: dict) -> list:
    """Flag recursive edges and bidirectional pairs."""
    hints = []
    for edge in summary.get("graph", {}).get("recursiveEdges", []):
        hints.append({
            "type": "recursive_call",
            "severity": "medium",
            "from": edge["from"],
            "to": edge["to"],
            "message": f"Recursive call: {edge['from']} → {edge['to']}"
        })
    for pair in summary.get("graph", {}).get("bidirectionalPairs", []):
        hints.append({
            "type": "circular_dependency",
            "severity": "medium",
            "a": pair["a"],
            "b": pair["b"],
            "message": f"Circular dependency: {pair['a']} ↔ {pair['b']}"
        })
    return hints


def check_deep_flows(summary: dict) -> list:
    """Flag entrypoints with flow depth above threshold."""
    hints = []
    for flow in summary.get("flowComplexity", []):
        if flow.get("maxFlowDepth", 0) >= FLOW_DEPTH_THRESHOLD:
            hints.append({
                "type": "deep_flow",
                "severity": "medium",
                "class": flow["class"],
                "method": flow["method"],
                "depth": flow["maxFlowDepth"],
                "message": f"{flow['class']}.{flow['method']} has flow depth {flow['maxFlowDepth']} (threshold: {FLOW_DEPTH_THRESHOLD})"
            })
    return hints


def check_multi_store_risk(config: dict) -> list:
    """Flag multi-store consistency risk if multiple data store types detected."""
    hints = []
    infra = config.get("infrastructure", {})
    db_types = set()
    for db in infra.get("databases", []):
        key = db.get("key", "").lower()
        if "datasource" in key or "postgresql" in key or "postgres" in key:
            db_types.add("postgresql")
        if "mongo" in key:
            db_types.add("mongodb")
        if "dynamo" in key:
            db_types.add("dynamodb")
        if "cdr" in key or "fhir" in key:
            db_types.add("fhir-cdr")
    for msg in infra.get("messaging", []):
        key = msg.get("key", "").lower()
        if "redis" in key:
            db_types.add("redis")
        if "kafka" in key:
            db_types.add("kafka")
    if len(db_types) >= 2:
        hints.append({
            "type": "multi_store_risk",
            "severity": "high",
            "stores": sorted(db_types),
            "message": f"Multiple data stores detected ({', '.join(sorted(db_types))}). Risk of inconsistent state without distributed transaction coordination."
        })
    return hints


def check_missing_resilience(summary: dict, config: dict) -> list:
    """Flag missing resilience patterns when multiple HTTP deps exist."""
    hints = []
    http_total = summary.get("httpDependencies", {}).get("total", 0)
    if http_total < 3:
        return hints

    # Check if any resilience library is referenced in config
    all_config = json.dumps(config).lower()
    resilience_keywords = ["resilience4j", "hystrix", "circuitbreaker", "circuit-breaker", "retry", "bulkhead"]
    has_resilience = any(kw in all_config for kw in resilience_keywords)

    if not has_resilience:
        hints.append({
            "type": "missing_resilience",
            "severity": "high",
            "httpDependencyCount": http_total,
            "message": f"{http_total} outgoing HTTP dependencies detected with no visible resilience patterns (circuit breaker, retry, bulkhead)"
        })
    return hints


def check_autoscaling_config(config: dict) -> list:
    """Flag suspicious deployment configurations."""
    hints = []
    for env, values in config.get("deployment", {}).items():
        enabled = values.get("autoscaling.enabled", "false")
        max_r = values.get("autoscaling.maxReplicas", "0")
        resources_enabled = values.get("resourcesEnabled", "true")
        if enabled == "false" and resources_enabled == "false":
            hints.append({
                "type": "deployment_risk",
                "severity": "medium",
                "environment": env,
                "message": f"Environment '{env}' has autoscaling disabled and resourcesEnabled=false. Risk of unbounded resource usage."
            })
        if enabled == "false" and int(max_r) > 50:
            hints.append({
                "type": "deployment_misconfiguration",
                "severity": "low",
                "environment": env,
                "maxReplicas": int(max_r),
                "message": f"Environment '{env}' has autoscaling disabled but maxReplicas={max_r}. Likely a template default."
            })
    return hints


def main():
    parser = argparse.ArgumentParser(description="Generate issue hints from artifacts")
    parser.add_argument("--summary", required=True, help="Path to <svc>-summary.json")
    parser.add_argument("--config", required=True, help="Path to <svc>-config.json")
    parser.add_argument("--output", required=True, help="Output issues-hints JSON path")
    args = parser.parse_args()

    summary = load_json(args.summary)
    config = load_json(args.config)

    all_hints = []
    all_hints.extend(check_god_classes(summary))
    all_hints.extend(check_dependency_magnets(summary))
    all_hints.extend(check_get_state_changing(summary))
    all_hints.extend(check_unresolved_http_targets(summary))
    all_hints.extend(check_unknown_nodes(summary))
    all_hints.extend(check_recursive_and_circular(summary))
    all_hints.extend(check_deep_flows(summary))
    all_hints.extend(check_multi_store_risk(config))
    all_hints.extend(check_missing_resilience(summary, config))
    all_hints.extend(check_autoscaling_config(config))

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_hints.sort(key=lambda h: severity_order.get(h.get("severity", "low"), 3))

    result = {
        "totalHints": len(all_hints),
        "bySeverity": {
            "high": len([h for h in all_hints if h["severity"] == "high"]),
            "medium": len([h for h in all_hints if h["severity"] == "medium"]),
            "low": len([h for h in all_hints if h["severity"] == "low"]),
        },
        "hints": all_hints,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Issues hints written to: {out}")


if __name__ == "__main__":
    main()
