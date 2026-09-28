# Stage 1 guide: network, security groups, storage, secrets, logs and alerts

Part of [aws-terraform.md](aws-terraform.md). Built step by step: each step adds one file, is explained, then checked with `terraform fmt` and `terraform validate`. **Nothing is applied until step 8.** Cost while up: near zero (about USD 0.40 per secret per month; storage billed by use).

## Steps

| # | File | Creates | Status |
|---|---|---|---|
| 1 | `variables.tf` (AZs), `network.tf` | VPC, internet gateway, 2 public + 2 private subnets in 2 AZs, route tables | written |
| 2 | `security_groups.tf` | `sg-alb`, `sg-app`, `sg-db`; the VPC's default security group emptied | written |
| 3 | `storage.tf` | S3 bucket (Block Public Access, versioning, SSE-S3, TLS-only policy, CORS); ECR repository | written |
| 4 | `secrets.tf` | Four empty secrets (below) | written |
| 5 | `monitoring.tf` | Log group (7 days), SNS topic and email subscription | written |
| 6 | `outputs.tf` | Values later stages and commands need | written |
| 7 | Lab checks | Recorded in `evidence/aws-capability-record.md` | done (29 September 2026): SSM, secret create/retrieve/delete, WAF, Budgets all allowed under `LabInstanceProfile`, tested from a throwaway EC2 instance, terminated afterward |
| 8 | `plan`, review, `apply`, acceptance | Push the image; set secret values from the CLI | |

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

## Acceptance

Subnets in two AZs; anonymous S3 requests denied; the image in ECR tagged with the git SHA; four secrets exist with values set; SNS subscription confirmed; runbook entry with date, commit and cost.
