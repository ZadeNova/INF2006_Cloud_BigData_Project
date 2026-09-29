# Stage 1 guide: network, security groups, storage, secrets, logs and alerts

Part of [aws-terraform.md](aws-terraform.md). Built step by step: each step adds one file, is explained, then checked with `terraform fmt` and `terraform validate`. **Nothing is applied until step 8.** Cost while up: near zero (about USD 0.40 per secret per month; storage billed by use).

## Steps

| # | File | Creates | Status |
|---|---|---|---|
| 1 | `variables.tf` (AZs), `network.tf` | VPC, internet gateway, 2 public + 2 private subnets in 2 AZs, route tables | written |
| 2 | `security_groups.tf` | `sg-alb`, `sg-app`, `sg-db`; the VPC's default security group emptied | written |
| 3 | `storage.tf` | S3 bucket (Block Public Access, versioning, SSE-S3, TLS-only policy); ECR repository. The CORS rule was removed before it was ever created (see the stage 2 plan) | written |
| 4 | `secrets.tf` | Four empty secrets (below) | written |
| 5 | `monitoring.tf` | Log group (7 days), SNS topic and email subscription | written |
| 6 | `outputs.tf` | Values later stages and commands need | written |
| 7 | Lab checks | Recorded in `evidence/aws-capability-record.md` | done (29 September 2026): SSM, secret create/retrieve/delete, WAF, Budgets all allowed under `LabInstanceProfile`, tested from a throwaway EC2 instance, terminated afterward |
| 8 | `plan`, review, `apply`, acceptance | Push the image; set secret values from the CLI | review gate closed (29 September 2026, `8f2e89b`, no blocking findings; [log](../reviews/aws-terraform.md#stage-1-network-security-groups-storage-secrets-monitoring)); applied 29 September 2026 after the S3 fix below, acceptance passed; image `c19d547` pushed and non-database secret fields set (29 September 2026). **Stage 1 complete** ([runbook](../../evidence/aws-build-runbook.md)) |

## Decisions for this stage

- **AZs pinned** to `us-east-1a` and `us-east-1b` through a variable, not "the first two available". The result is deterministic, and some us-east-1 AZs lack instance types.
- **Subnets:** public `10.0.1.0/24`, `10.0.2.0/24`; private `10.0.11.0/24`, `10.0.12.0/24`. Public subnets do **not** auto-assign public IPs; the stage 3 launch template asks for one explicitly, so the choice is visible where it matters.
- **DNS hostnames on** in the VPC (RDS endpoints and `verify-full` TLS need them).
- **Secrets** (field lists from the [runtime handoff](../AWS_INFRASTRUCTURE.md#secrets-manager-startup-and-alb-boundary)); Terraform creates the containers only, values are set with the CLI so they never enter state:

| Secret | JSON keys |
|---|---|
| `inf2006-grp21/web` | `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER` (runtime role), `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY` |
| `inf2006-grp21/migration` | same keys, `POSTGRES_USER` is the migration owner |
| `inf2006-grp21/trainer` | `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (read-only identity) |
| `inf2006-grp21/bootstrap` | DB keys plus `MIGRATION_USER`, `MIGRATION_PASSWORD`, `BOOTSTRAP_USER`, `BOOTSTRAP_PASSWORD` |

`POSTGRES_PORT` is optional everywhere; the RDS master password itself is managed by RDS (stage 2).

## S3 bucket: created with the CLI (lab constraint, 29 September 2026)

The first apply created 32 of 39 resources, then failed reading the new bucket back: the Learner Lab's service control policy denies `s3:GetBucketObjectLockConfiguration`, which the `aws_s3_bucket` resource calls on every read. A probe of 16 bucket read calls showed this is the **only** denied one. So the bucket itself is created once with the CLI and looked up with `data "aws_s3_bucket"`; its public access block, ownership controls, versioning, encryption, lifecycle rule and TLS-only policy remain Terraform resources. A `removed` block (with `destroy = false`) makes Terraform forget the bucket resource from the failed apply without deleting the bucket.

On a fresh account (for example a groupmate's fallback), before the first apply:

```bash
B="inf2006-grp21-data-$(openssl rand -hex 8)"
aws s3api create-bucket --bucket "$B" --region us-east-1
aws s3api put-bucket-tagging --bucket "$B" --tagging \
  'TagSet=[{Key=Name,Value=inf2006-grp21-data},{Key=Project,Value=inf2006-grp21},{Key=Env,Value=evidence},{Key=ManagedBy,Value=cli}]'
echo "s3_bucket_name = \"$B\"" >> terraform.tfvars
```

At teardown (stage 6), `terraform destroy` removes the bucket's settings but not the bucket. Empty it (all object versions) and delete it with the CLI afterwards; the stage 6 guide will give the command.

## Acceptance

Subnets in two AZs; anonymous S3 requests denied; the image in ECR tagged with the git SHA; four secret containers exist, with the non-database fields set (the database fields follow once stage 2 creates RDS); SNS subscription confirmed; runbook entry with date, commit and cost.
