#!/usr/bin/env python3
"""Summarize ECS services for a stack cluster (resources + running task age)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _parse_aws_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    # AWS CLI JSON uses e.g. 2026-07-26T17:49:19.206000+00:00 or ...Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _human_duration(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _running_age(started_at: Any, now: datetime) -> dict[str, Any]:
    started = _parse_aws_time(started_at)
    if not started:
        return {"startedAt": started_at, "runningFor": None, "runningForSeconds": None}
    secs = int((now - started).total_seconds())
    return {
        "startedAt": started_at,
        "runningFor": _human_duration(secs),
        "runningForSeconds": secs,
    }


def _taskdef_resources(task_def: dict[str, Any]) -> dict[str, Any]:
    containers = []
    cpu_sum = 0
    mem_sum = 0
    for c in task_def.get("containerDefinitions") or []:
        containers.append(
            {
                "name": c.get("name"),
                "cpu": c.get("cpu"),
                "memory": c.get("memory"),
                "memoryReservation": c.get("memoryReservation"),
            }
        )
        if isinstance(c.get("cpu"), int):
            cpu_sum += c["cpu"]
        mem = c.get("memory")
        if mem is None:
            mem = c.get("memoryReservation")
        if isinstance(mem, int):
            mem_sum += mem
    task_cpu = task_def.get("cpu")
    task_mem = task_def.get("memory")
    # Prefer task-level when set (Fargate); else sum container hard limits (EC2).
    configured_cpu: Any = task_cpu if task_cpu not in (None, "") else (cpu_sum or None)
    configured_mem: Any = task_mem if task_mem not in (None, "") else (mem_sum or None)
    return {
        "taskCpu": task_cpu,
        "taskMemory": task_mem,
        "configuredCpu": configured_cpu,
        "configuredMemory": configured_mem,
        "containers": containers,
    }


def _describe_taskdefs(
    env: str,
    refs: list[str],
    *,
    region: str | None,
    brain: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for ref in refs:
        short = ref.rsplit("/", 1)[-1]
        if short in out:
            continue
        desc = od_aws.run_aws(
            env,
            ["ecs", "describe-task-definition", "--task-definition", ref],
            region=region,
            brain=brain,
        )
        td = desc.get("taskDefinition") or {}
        key = f"{td.get('family')}:{td.get('revision')}"
        resources = _taskdef_resources(td)
        out[key] = resources
        out[short] = resources
        out[ref] = resources
    return out


def _list_running_task_arns(
    env: str,
    cluster: str,
    service_name: str,
    *,
    region: str | None,
    brain: dict[str, Any],
) -> list[str]:
    listed = od_aws.run_aws(
        env,
        [
            "ecs",
            "list-tasks",
            "--cluster",
            cluster,
            "--service-name",
            service_name,
            "--desired-status",
            "RUNNING",
        ],
        region=region,
        brain=brain,
    ) or {}
    return list(listed.get("taskArns") or [])


def _describe_running_tasks(
    env: str,
    cluster: str,
    arns: list[str],
    *,
    region: str | None,
    brain: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    tasks_out: list[dict[str, Any]] = []
    for i in range(0, len(arns), 100):
        chunk = arns[i : i + 100]
        desc = od_aws.run_aws(
            env,
            ["ecs", "describe-tasks", "--cluster", cluster, "--tasks", *chunk],
            region=region,
            brain=brain,
        )
        for t in desc.get("tasks") or []:
            age = _running_age(t.get("startedAt"), now)
            tasks_out.append(
                {
                    "id": (t.get("taskArn") or "").rsplit("/", 1)[-1],
                    "lastStatus": t.get("lastStatus"),
                    "health": t.get("healthStatus"),
                    "taskDef": (t.get("taskDefinitionArn") or "").rsplit("/", 1)[-1],
                    "cpu": t.get("cpu"),
                    "memory": t.get("memory"),
                    **age,
                }
            )
    tasks_out.sort(key=lambda x: x.get("startedAt") or "")
    return tasks_out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--stack", required=True, help="Stack name, e.g. hub-service")
    parser.add_argument(
        "--services",
        default=None,
        help="Comma-separated service names (default: all in cluster)",
    )
    args = parser.parse_args()
    brain = od_aws.load_brain()
    cluster = od_aws.stack_cluster(args.stack, brain)
    now = datetime.now(timezone.utc)

    if args.services:
        service_names = [s.strip() for s in args.services.split(",") if s.strip()]
    else:
        listed = od_aws.run_aws(
            args.env,
            ["ecs", "list-services", "--cluster", cluster],
            region=args.region,
            brain=brain,
        ) or {}
        service_names = [a.rsplit("/", 1)[-1] for a in listed.get("serviceArns") or []]

    if not service_names:
        od_aws.emit(
            {
                "env": args.env,
                "cluster": cluster,
                "services": [],
                "note": "No services found",
            }
        )
        return

    raw_services: list[dict[str, Any]] = []
    taskdef_refs: list[str] = []
    for i in range(0, len(service_names), 10):
        chunk = service_names[i : i + 10]
        desc = od_aws.run_aws(
            args.env,
            ["ecs", "describe-services", "--cluster", cluster, "--services", *chunk],
            region=args.region,
            brain=brain,
        )
        for svc in desc.get("services") or []:
            raw_services.append(svc)
            td = svc.get("taskDefinition")
            if td:
                taskdef_refs.append(td)
            for d in svc.get("deployments") or []:
                dtd = d.get("taskDefinition")
                if dtd:
                    taskdef_refs.append(dtd)

    # unique preserving order
    seen: set[str] = set()
    unique_refs: list[str] = []
    for ref in taskdef_refs:
        if ref not in seen:
            seen.add(ref)
            unique_refs.append(ref)

    resources_by_td = _describe_taskdefs(
        args.env, unique_refs, region=args.region, brain=brain
    )

    services_out = []
    for svc in raw_services:
        deps = []
        for d in svc.get("deployments") or []:
            td_short = (d.get("taskDefinition") or "").rsplit("/", 1)[-1]
            deps.append(
                {
                    "status": d.get("status"),
                    "desired": d.get("desiredCount"),
                    "running": d.get("runningCount"),
                    "pending": d.get("pendingCount"),
                    "failed": d.get("failedTasks"),
                    "rollout": d.get("rolloutState"),
                    "taskDef": td_short,
                    "resources": resources_by_td.get(td_short),
                }
            )
        events = [
            {"at": e.get("createdAt"), "message": e.get("message")}
            for e in (svc.get("events") or [])[:8]
        ]
        td_short = (svc.get("taskDefinition") or "").rsplit("/", 1)[-1]
        name = svc.get("serviceName") or ""
        running_arns = _list_running_task_arns(
            args.env, cluster, name, region=args.region, brain=brain
        )
        running_tasks = _describe_running_tasks(
            args.env,
            cluster,
            running_arns,
            region=args.region,
            brain=brain,
            now=now,
        )
        services_out.append(
            {
                "name": name,
                "status": svc.get("status"),
                "desired": svc.get("desiredCount"),
                "running": svc.get("runningCount"),
                "pending": svc.get("pendingCount"),
                "taskDef": td_short,
                "resources": resources_by_td.get(td_short),
                "tasks": running_tasks,
                "deployments": deps,
                "events": events,
            }
        )

    cluster_desc = od_aws.run_aws(
        args.env,
        ["ecs", "describe-clusters", "--clusters", cluster, "--include", "STATISTICS"],
        region=args.region,
        brain=brain,
    )
    c0 = (cluster_desc.get("clusters") or [{}])[0]

    od_aws.emit(
        {
            "env": args.env,
            "prod_class": od_aws.is_prod_env(args.env, brain),
            "cluster": {
                "name": cluster,
                "status": c0.get("status"),
                "runningTasks": c0.get("runningTasksCount"),
                "pendingTasks": c0.get("pendingTasksCount"),
                "instances": c0.get("registeredContainerInstancesCount"),
                "activeServices": c0.get("activeServicesCount"),
            },
            "services": services_out,
        }
    )


if __name__ == "__main__":
    main()
