# Devops AWS — ops reference

## Brain (`.cursor/devops/brain.json`)

Created by **devops-onboard**. Example: kit `schemas/devops-brain.example.json`.

Important keys:

| Key | Used by |
|-----|---------|
| `auth_mode`, `vault_command`, `profiles`, `prod_profiles`, `region_default` | All tools |
| `ecs.cluster_name_template` | ECS/ASG helpers (`{stack}` required) |
| `ecs.critical_env_keys`, `ecs.min_env_count` | `ecs_taskdef_required_env` |
| `cdn.bucket_name` or `cdn.bucket_tag` | CDN tools |
| `opensearch.domain`, optional `opensearch.endpoint_param` | OpenSearch tools |
| `datadog.*_param` | Datadog query tools |
| `capabilities`, `discovered` | Onboard report / agent context |

## Auth modes

- `aws-vault` — `vault exec <env> -- aws …`, with `--profile` fallback if vault has no creds
- `aws-profile` — `aws --profile <env>` only
- `env` — ambient credentials (no profile)

## CDN

Resolve origin bucket from brain only (name or tag). CloudFront via alias match on URL host.

## OpenSearch

Control plane: `describe-domain` + CloudWatch using `opensearch.domain`.
Data plane: SigV4 to endpoint from `endpoint_param` or describe-domain `Endpoint`.

## Prod safety

Mutations print `mutation_explanation` JSON. Prod-class without `--approve-prod` exits refused.
