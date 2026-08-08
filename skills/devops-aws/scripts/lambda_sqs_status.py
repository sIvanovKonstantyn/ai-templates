#!/usr/bin/env python3
"""Snapshot Lambda config/concurrency + linked SQS queue + event-source mapping."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aws_lib as od_aws


def _metric(
    env: str,
    *,
    namespace: str,
    metric: str,
    dimensions: list[dict[str, str]],
    minutes: int,
    period: int,
    stat: str,
    region: str | None,
    brain: dict[str, Any],
) -> dict[str, Any]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    args = [
        "cloudwatch",
        "get-metric-statistics",
        "--namespace",
        namespace,
        "--metric-name",
        metric,
        "--dimensions",
        *[f"Name={d['Name']},Value={d['Value']}" for d in dimensions],
        "--start-time",
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--end-time",
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--period",
        str(period),
        "--statistics",
        stat,
    ]
    raw = od_aws.run_aws(env, args, region=region, brain=brain) or {}
    points = sorted(raw.get("Datapoints") or [], key=lambda p: p.get("Timestamp") or "")
    values = [p.get(stat) for p in points if p.get(stat) is not None]
    latest = points[-1] if points else None
    return {
        "metric": metric,
        "stat": stat,
        "periodSeconds": period,
        "windowMinutes": minutes,
        "sampleCount": len(values),
        "latest": latest.get(stat) if latest else None,
        "latestAt": latest.get("Timestamp") if latest else None,
        "max": max(values) if values else None,
        "sum": sum(values) if values and stat == "Sum" else None,
    }


def _lambda_config(env: str, function: str, *, region: str | None, brain: dict[str, Any]) -> dict[str, Any]:
    conf = od_aws.run_aws(
        env,
        ["lambda", "get-function-configuration", "--function-name", function],
        region=region,
        brain=brain,
    ) or {}
    return {
        "functionName": conf.get("FunctionName"),
        "state": conf.get("State"),
        "stateReason": conf.get("StateReason"),
        "lastUpdateStatus": conf.get("LastUpdateStatus"),
        "runtime": conf.get("Runtime"),
        "timeout": conf.get("Timeout"),
        "memorySize": conf.get("MemorySize"),
        "reservedConcurrentExecutions": conf.get("ReservedConcurrentExecutions"),
        "codeSize": conf.get("CodeSize"),
        "lastModified": conf.get("LastModified"),
        "vpcConfigured": bool((conf.get("VpcConfig") or {}).get("VpcId")),
        "architectures": conf.get("Architectures"),
    }


def _account_settings(env: str, *, region: str | None, brain: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = od_aws.run_aws(
            env,
            ["lambda", "get-account-settings"],
            region=region,
            brain=brain,
        ) or {}
    except SystemExit as exc:
        return {"error": str(exc)}
    limits = raw.get("AccountLimit") or {}
    usage = raw.get("AccountUsage") or {}
    return {
        "concurrentExecutionsLimit": limits.get("ConcurrentExecutions"),
        "unreservedConcurrentExecutions": limits.get("UnreservedConcurrentExecutions"),
        "functionCount": usage.get("FunctionCount"),
    }


def _event_source_mappings(
    env: str, function: str, *, region: str | None, brain: dict[str, Any]
) -> list[dict[str, Any]]:
    listed = od_aws.run_aws(
        env,
        ["lambda", "list-event-source-mappings", "--function-name", function],
        region=region,
        brain=brain,
    ) or {}
    out = []
    for m in listed.get("EventSourceMappings") or []:
        out.append(
            {
                "uuid": m.get("UUID"),
                "state": m.get("State"),
                "stateTransitionReason": m.get("StateTransitionReason"),
                "batchSize": m.get("BatchSize"),
                "eventSourceArn": m.get("EventSourceArn"),
                "functionArn": m.get("FunctionArn"),
                "lastProcessingResult": m.get("LastProcessingResult"),
                "lastModified": m.get("LastModified"),
            }
        )
    return out


def _sqs_attrs(env: str, queue: str, *, region: str | None, brain: dict[str, Any]) -> dict[str, Any]:
    # Accept name or URL
    url = queue
    if not queue.startswith("https://"):
        urls = od_aws.run_aws(
            env,
            ["sqs", "get-queue-url", "--queue-name", queue],
            region=region,
            brain=brain,
        ) or {}
        url = urls.get("QueueUrl") or queue
    attrs = od_aws.run_aws(
        env,
        [
            "sqs",
            "get-queue-attributes",
            "--queue-url",
            url,
            "--attribute-names",
            "All",
        ],
        region=region,
        brain=brain,
    ) or {}
    a = attrs.get("Attributes") or {}

    def _i(key: str) -> int | None:
        v = a.get(key)
        return int(v) if v is not None and str(v).isdigit() else None

    visible = _i("ApproximateNumberOfMessages")
    in_flight = _i("ApproximateNumberOfMessagesNotVisible")
    delayed = _i("ApproximateNumberOfMessagesDelayed")
    visibility = _i("VisibilityTimeout")
    return {
        "queueUrl": url,
        "approximateMessagesVisible": visible,
        "approximateMessagesNotVisible": in_flight,
        "approximateMessagesDelayed": delayed,
        "visibilityTimeoutSeconds": visibility,
        "messageRetentionPeriod": _i("MessageRetentionPeriod"),
        "receiveMessageWaitTimeSeconds": _i("ReceiveMessageWaitTimeSeconds"),
        "createdTimestamp": a.get("CreatedTimestamp"),
        "lastModifiedTimestamp": a.get("LastModifiedTimestamp"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    od_aws.add_env_args(parser)
    parser.add_argument("--function", required=True, help="Lambda function name")
    parser.add_argument(
        "--queue",
        required=True,
        help="SQS queue name or URL",
    )
    parser.add_argument("--minutes", type=int, default=60, help="CloudWatch metric window")
    args = parser.parse_args()
    brain = od_aws.load_brain()
    queue = args.queue

    conf = _lambda_config(args.env, args.function, region=args.region, brain=brain)
    mappings = _event_source_mappings(args.env, args.function, region=args.region, brain=brain)
    sqs = _sqs_attrs(args.env, queue, region=args.region, brain=brain)
    account = _account_settings(args.env, region=args.region, brain=brain)

    dims_fn = [{"Name": "FunctionName", "Value": args.function}]
    metrics = {
        "concurrentExecutions": _metric(
            args.env,
            namespace="AWS/Lambda",
            metric="ConcurrentExecutions",
            dimensions=dims_fn,
            minutes=args.minutes,
            period=60,
            stat="Maximum",
            region=args.region,
            brain=brain,
        ),
        "throttles": _metric(
            args.env,
            namespace="AWS/Lambda",
            metric="Throttles",
            dimensions=dims_fn,
            minutes=args.minutes,
            period=60,
            stat="Sum",
            region=args.region,
            brain=brain,
        ),
        "errors": _metric(
            args.env,
            namespace="AWS/Lambda",
            metric="Errors",
            dimensions=dims_fn,
            minutes=args.minutes,
            period=60,
            stat="Sum",
            region=args.region,
            brain=brain,
        ),
        "invocations": _metric(
            args.env,
            namespace="AWS/Lambda",
            metric="Invocations",
            dimensions=dims_fn,
            minutes=args.minutes,
            period=60,
            stat="Sum",
            region=args.region,
            brain=brain,
        ),
        "duration": _metric(
            args.env,
            namespace="AWS/Lambda",
            metric="Duration",
            dimensions=dims_fn,
            minutes=args.minutes,
            period=60,
            stat="Maximum",
            region=args.region,
            brain=brain,
        ),
    }

    warnings: list[str] = []
    if conf.get("timeout") and sqs.get("visibilityTimeoutSeconds"):
        if conf["timeout"] > sqs["visibilityTimeoutSeconds"]:
            warnings.append(
                f"Lambda timeout ({conf['timeout']}s) > SQS visibility timeout "
                f"({sqs['visibilityTimeoutSeconds']}s): in-flight messages can reappear and "
                "be processed by another concurrent invocation while the first is still running."
            )
    reserved = conf.get("reservedConcurrentExecutions")
    if isinstance(reserved, int) and reserved <= 1:
        warnings.append(
            f"Reserved concurrency is {reserved}: a single long-running invocation can "
            "stall the entire queue."
        )
    if (sqs.get("approximateMessagesVisible") or 0) > 0:
        warnings.append(
            f"Queue has {sqs['approximateMessagesVisible']} visible message(s) waiting."
        )

    od_aws.emit(
        {
            "env": args.env,
            "prod_class": od_aws.is_prod_env(args.env, brain),
            "lambda": conf,
            "account": account,
            "eventSourceMappings": mappings,
            "sqs": sqs,
            "metricsLastMinutes": args.minutes,
            "metrics": metrics,
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
