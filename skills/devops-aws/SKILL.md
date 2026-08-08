---
name: devops-aws
description: >-
  Safe AWS ops for ECS, ASG, App Auto Scaling, CDN (CloudFront/S3), OpenSearch,
  Datadog logs/metrics (SSM keys from brain), SSM Parameter Store, and Lambda
  via prepared Python tools. Use when diagnosing crash loops, canaries,
  capacity, CDN assets, OpenSearch volume/CPU, Datadog queries, or QA/prod
  deploys; when the Devops role is active. Requires devops-onboard brain.
---

# Devops AWS

Follow the workspace `devops-role` rule. **Never** call `aws` / vault directly —
only scripts under this skill’s `scripts/`. Configuration comes from
`.cursor/devops/brain.json` (written by **devops-onboard**).

## Resolve scripts

```bash
SCRIPTS="$(find . -path '*/skills/devops-aws/scripts' -type d 2>/dev/null | head -n 1)"
```

## Prerequisites

1. Run **devops-onboard** (or ensure brain exists with `prod_profiles`,
   `ecs.cluster_name_template`, and any CDN/OpenSearch/Datadog keys you need).
2. Auth via brain `auth_mode`: `aws-vault` | `aws-profile` | `env`.

Missing brain keys fail fast with “re-run devops-onboard” — do not invent names.

## Shell / prod gates

| Env class | Chat approval | Mutate flags |
|-----------|---------------|--------------|
| Non-prod | Explain mutates | `--explain` |
| Prod-class (`prod_profiles`) | `approve`/`yes` before any AWS shell | `--explain` + `--approve-prod` |

## Read tools

| Tool | Purpose |
|------|---------|
| `ecs_service_status.py --env E --stack S` | Cluster + services |
| `ecs_task_failures.py --env E --stack S --service SVC` | STOPPED tasks |
| `ecs_taskdef_env_diff.py` / `ecs_taskdef_required_env.py` | Env diffs / critical keys from brain |
| `ecs_cluster_capacity.py --env E --stack S` | Instance capacity |
| `app_autoscaling_status.py` | Scalable targets + policies |
| `cdn_object_lookup.py --env E --url URL` | CloudFront + origin bucket (brain) |
| `opensearch_cluster_stats.py --env E` | Domain from `brain.opensearch.domain` |
| `opensearch_indices.py --env E` | `_cat/indices` (SigV4) |
| `datadog_credentials_check.py` / `datadog_logs.py` / `datadog_metrics.py` | Brain SSM paths or `DD_*` |
| `ssm_get_param.py --env E --name /Path` | SSM read (masked by default) |
| `lambda_sqs_status.py --env E --function F --queue Q` | Lambda + SQS snapshot |

Cluster names use `brain.ecs.cluster_name_template` (must contain `{stack}`).

## Mutate tools

Always `--explain '...'`. Prod-class also `--approve-prod` after chat approval.

Includes: `ecs_update_service`, `ecs_delete_service`, `asg_*`,
`app_autoscaling_set_suspended`, `cdn_put_object`, `cdn_invalidate`,
`opensearch_delete_by_query`, `ssm_put_param`, `lambda_update_env`,
`lambda_deploy`, `tf_apply`.

## Datadog

Requires `brain.datadog.api_key_param` + `app_key_param` (and optional
`site_param`), or `DD_API_KEY` / `DD_APP_KEY` / `DD_SITE` env overrides.
Never print key values.

## Out of scope

Company-specific deploy CLIs, monitor CRUD, ALB rule editing, hand-built
`RegisterTaskDefinition`. Teach-request those as new tools.
