#!/usr/bin/env python3
"""
Summarize AST, HTTP dependency, and event dependency artifacts into a compact
metrics JSON that can be consumed by the report step without reading thousands
of lines of raw data.

Usage:
    python summarize_ast.py \
        --ast       artifacts/<service>-ast.json \
        --http-deps artifacts/<service>-http-dependencies.json \
        --event-deps artifacts/<service>-event-dependencies.json \
        --output    artifacts/<service>-summary.json
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def summarize_entrypoints(entrypoints: list) -> dict:
    by_type = defaultdict(list)
    for ep in entrypoints:
        ep_type = ep.get("type", "UNKNOWN")
        entry = {
            "class": ep.get("class"),
            "method": ep.get("method"),
        }
        if ep_type == "REST":
            entry["httpMethod"] = ep.get("httpMethod")
            entry["path"] = ep.get("path")
        by_type[ep_type].append(entry)
    return {
        "total": len(entrypoints),
        "byType": {k: {"count": len(v), "endpoints": v} for k, v in by_type.items()},
    }


def summarize_graph(graph: dict) -> dict:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    type_counts = Counter(n.get("type", "UNKNOWN") for n in nodes)

    # Collect representative class names per type (up to 5 unique classes)
    type_classes = defaultdict(set)
    for n in nodes:
        node_type = n.get("type", "UNKNOWN")
        node_id = n.get("id", "")
        # Extract class name from "ClassName.methodName" format
        class_name = node_id.split(".")[0] if "." in node_id else node_id
        if class_name and len(type_classes[node_type]) < 5:
            type_classes[node_type].add(class_name)

    # fan-in / fan-out
    fan_out = Counter()
    fan_in = Counter()
    for e in edges:
        fan_out[e["from"]] += 1
        fan_in[e["to"]] += 1

    top_fan_out = fan_out.most_common(10)
    top_fan_in = fan_in.most_common(10)

    # detect self-referencing / recursive edges
    recursive = [e for e in edges if e["from"] == e["to"]]

    # detect cycles (simple: A->B and B->A)
    edge_set = {(e["from"], e["to"]) for e in edges}
    bidirectional = [(a, b) for a, b in edge_set if (b, a) in edge_set and a < b]

    return {
        "totalNodes": len(nodes),
        "totalEdges": len(edges),
        "nodesByType": {
            k: {"count": v, "classes": sorted(type_classes.get(k, set()))}
            for k, v in type_counts.most_common()
        },
        "topFanOut": [{"node": n, "count": c} for n, c in top_fan_out],
        "topFanIn": [{"node": n, "count": c} for n, c in top_fan_in],
        "recursiveEdges": [{"from": e["from"], "to": e["to"]} for e in recursive],
        "bidirectionalPairs": [{"a": a, "b": b} for a, b in bidirectional],
    }


def summarize_http_deps(data: dict) -> dict:
    deps = data.get("dependencies", [])
    by_client = defaultdict(list)
    by_method = Counter()
    unresolved = 0
    for d in deps:
        by_client[d.get("sourceClass", "unknown")].append({
            "method": d.get("sourceMethod"),
            "httpMethod": d.get("httpMethod"),
            "targetService": d.get("targetService"),
        })
        by_method[d.get("httpMethod", "UNKNOWN")] += 1
        if d.get("targetService") is None:
            unresolved += 1

    return {
        "total": len(deps),
        "unresolvedTargets": unresolved,
        "byHttpMethod": dict(by_method.most_common()),
        "byClient": {
            k: {"count": len(v), "calls": v} for k, v in by_client.items()
        },
    }


def summarize_event_deps(data: dict) -> dict:
    events = data.get("events", [])
    total_consumers = 0
    total_producers = 0
    event_list = []
    for ev in events:
        consumers = ev.get("consumers", [])
        total_consumers += len(consumers)
        if ev.get("producer"):
            total_producers += 1
        event_list.append({
            "eventType": ev.get("eventType"),
            "channel": ev.get("channel"),
            "hasProducer": ev.get("producer") is not None,
            "consumerCount": len(consumers),
        })
    return {
        "totalEvents": len(events),
        "totalProducers": total_producers,
        "totalConsumers": total_consumers,
        "events": event_list,
    }


def count_flow_depth(flow: dict, current: int = 0) -> int:
    """Walk the flow tree and return max depth."""
    if not flow:
        return current
    steps = flow.get("steps", [])
    max_d = current
    for step in steps:
        if "flow" in step:
            max_d = max(max_d, count_flow_depth(step["flow"], current + 1))
        if "ifTrue" in step:
            for s in step["ifTrue"]:
                if "flow" in s:
                    max_d = max(max_d, count_flow_depth(s["flow"], current + 1))
        if "ifFalse" in step:
            for s in step.get("ifFalse", []):
                if "flow" in s:
                    max_d = max(max_d, count_flow_depth(s["flow"], current + 1))
        if "try" in step:
            for s in step["try"]:
                if "flow" in s:
                    max_d = max(max_d, count_flow_depth(s["flow"], current + 1))
        if "loop" in step:
            for s in step["loop"]:
                if "flow" in s:
                    max_d = max(max_d, count_flow_depth(s["flow"], current + 1))
    return max_d


def summarize_flow_complexity(entrypoints: list) -> list:
    """Return per-entrypoint flow depth as a complexity indicator.
    Filters out depth-0 entries to save tokens — only meaningful flows are included."""
    results = []
    for ep in entrypoints:
        depth = count_flow_depth(ep.get("flow", {}))
        if depth > 0:
            results.append({
                "class": ep.get("class"),
                "method": ep.get("method"),
                "type": ep.get("type"),
                "maxFlowDepth": depth,
            })
    results.sort(key=lambda x: x["maxFlowDepth"], reverse=True)
    return results[:15]  # top 15 most complex


def main():
    parser = argparse.ArgumentParser(description="Summarize AST artifacts")
    parser.add_argument("--ast", required=True, help="Path to <service>-ast.json")
    parser.add_argument("--http-deps", required=True, help="Path to <service>-http-dependencies.json")
    parser.add_argument("--event-deps", required=True, help="Path to <service>-event-dependencies.json")
    parser.add_argument("--output", required=True, help="Output summary JSON path")
    args = parser.parse_args()

    ast_data = load_json(args.ast)
    http_data = load_json(args.http_deps)
    event_data = load_json(args.event_deps)

    summary = {
        "project": ast_data.get("project", "unknown"),
        "entrypoints": summarize_entrypoints(ast_data.get("entrypoints", [])),
        "graph": summarize_graph(ast_data.get("graph", {})),
        "httpDependencies": summarize_http_deps(http_data),
        "eventDependencies": summarize_event_deps(event_data),
        "flowComplexity": summarize_flow_complexity(ast_data.get("entrypoints", [])),
        "metadata": ast_data.get("metadata", {}),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written to: {out}")


if __name__ == "__main__":
    main()
