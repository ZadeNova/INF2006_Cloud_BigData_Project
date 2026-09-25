# AWS infrastructure in Terraform

Status (25 September 2026): planned, not started. Terraform is not installed on the development machine yet, nothing is written and nothing is applied. Replaces the console-first order in [cloud-independent-prep.md](cloud-independent-prep.md) B7 and the "reproduce afterwards" framing of B5.

**How this is built.** The user has no Terraform experience and is learning it while building. Work goes one stage at a time, and **nothing starts until the user says so**. Each stage begins with a guide that explains the Terraform concepts that stage uses (starting from what Terraform is in stage 0), then lists explicit steps; the user runs `plan` and `apply` and approves every change.

## Decisions recorded here

| Decision | Detail |
|---|---|
| **Build method (changed 25 September 2026)** | Terraform creates and owns every team resource. The console is for watching and learning (reading settings, logs, metrics, CloudTrail) and for the few steps Terraform cannot do: the ACM validation record at an external registrar, confirming the SNS email subscription, and reading the lab balance. Anything created by hand is imported into Terraform or deleted, so there is no drift. Replaces "console first, then reproduce in Terraform". |
| Region and account | `us-east-1`, AWS Academy Learner Lab (`voclabs` role). One member's account is the integration account; one person applies. |
| IAM | Role creation is assumed denied. Reference `LabInstanceProfile` and `LabRole` through data sources; never create IAM roles. Recorded as external dependencies. |
| Database | RDS PostgreSQL pinned to **17.x** (the lab default is 18.3; the app, CI and all verification run on 17). Pick the newest 17 minor the lab offers. Single-AZ, private, encrypted, TLS forced. Master password managed by RDS in Secrets Manager (`manage_master_user_password`), so it never enters Terraform state. |
| Secrets | **Secrets Manager.** Terraform creates the secret resource only; its value (`DJANGO_SECRET_KEY`, application database password) is set once with the AWS CLI, so it is not in state or source. Instances read it at boot through the instance profile. |
| Object storage | **One S3 bucket**, prefixes `data/` (dataset), `exports/` (analytics exports), `media/images/`, `media/models/` (`.glb` shoe models). Block Public Access, versioning, SSE-S3, a deny-non-TLS policy. Browsers read media through short-lived pre-signed GET URLs. |
| CORS | Required for the `.glb` models (a 3D viewer fetches them from JavaScript; `<img>` does not need it). Rule: `GET` and `HEAD` from the application's HTTPS origin only, never `*`. Upload models with `Content-Type: model/gltf-binary`. |
| Image registry | ECR, immutable tags (git SHA), scan on push, keep the last 10 images. |
| HTTPS | ACM certificate on a team-owned domain with DNS validation at the registrar. Certificate ARN is a variable, so everything else can be applied before the domain exists. Fallback: a self-signed certificate imported into ACM, limitation documented. |
| Audit | CloudTrail **event history** (on by default, 90 days, free). Nothing created; shown on the diagram and cited in the threat-control map. |
| Scheduler | Jobs: `refresh_analytics`, `clearsessions`, optionally `snapshot_inventory`. Preferred: EventBridge Scheduler invoking SSM Run Command on an instance by tag, using `LabRole` as the scheduler's role. Test in stage 4; if the lab refuses, fall back to cron on one instance and document the host-loss limitation. The database lock already prevents double runs. |
| Not built | WAF, CloudFront, NAT gateway, ElastiCache, EKS, a separate analytics service. Reasons in [PROBLEM_FRAMING_AND_ARCHITECTURE.md](../PROBLEM_FRAMING_AND_ARCHITECTURE.md). |

## Layout

`src/terraform/`, one root module, one file per concern, no child modules (easier to read and learn):

```
versions.tf        provider and Terraform version pins
providers.tf       aws provider, default_tags Project=inf2006 Env=evidence ManagedBy=terraform
variables.tf       region, domain, certificate ARN, alarm email, instance type, scaling target, flags
data.tf            AZs, AL2023 AMI (SSM parameter), LabInstanceProfile, LabRole
network.tf         VPC 10.0.0.0/16, 2 public + 2 private subnets, IGW, route tables
security_groups.tf sg-alb (443/80 from internet), sg-app (8000 from sg-alb), sg-db (5432 from sg-app)
storage.tf         S3 bucket + policies + CORS, ECR repository + lifecycle
secrets.tf         Secrets Manager secret (value set outside Terraform)
database.tf        DB subnet group, parameter group, RDS instance
load_balancer.tf   ALB, target group (/health/), HTTPS listener, HTTP→HTTPS redirect
compute.tf         launch template (IMDSv2, encrypted EBS), ASG, target-tracking policy
user_data.sh.tftpl boot script
monitoring.tf      log group (7-day retention), SNS topic + email, alarms, 5xx metric filter
scheduler.tf       EventBridge schedules (behind a flag)
outputs.tf         ALB DNS name, ECR URL, bucket name, RDS endpoint
```

Names follow `inf2006-<component>` (`inf2006-alb`, `inf2006-db`, `inf2006-app-asg`), and the diagram uses the same names.

**State.** Local state on the applying machine, never committed (`.gitignore` gains `*.tfstate*`, `*.tfplan`, `.terraform.lock.hcl` is committed). The scope forbids submitting state with secrets, and the design above keeps secret values out of it anyway. A remote S3 backend is not worth it for one applier and a two-week stack.

**Credentials.** The Learner Lab issues temporary credentials (from "AWS Details") that expire with the session. Export them before each `plan` or `apply`; an expired token mid-apply leaves a partial apply that the next run completes.

## Boot script (what every instance does)

1. Install Docker; log in to ECR with the instance profile.
2. Read the Secrets Manager secret and the RDS-managed master secret's host details; write an env file to `/run/inf2006.env` (in memory, mode 0600).
3. Read the instance's private IP from IMDSv2 and add it to `DJANGO_ALLOWED_HOSTS`, so the ALB health probe (which uses the IP as Host) is accepted.
4. Run the image tag passed in the launch template, `DJANGO_TRUST_PROXY=true`, `awslogs` log driver to the CloudWatch log group.

IMDSv2 hop limit is 2 so the container can reach instance metadata if needed. SSM Session Manager, no SSH key and no port 22.

One-off operations run through SSM Run Command, not at boot: `db_bootstrap` (before the first migrate; leave RDS "initial database name" empty), `migrate`, the S3 dataset sync and `import_dataset`. Migrating at every boot would race when two instances start.

## Stages

Each stage: `fmt`, `validate`, `plan` saved to a file, the plan read aloud (creations, replacements, deletions, public exposure, IAM, NAT, Multi-AZ, cost), the user approves, `apply`, then an acceptance check and an entry in `evidence/aws-build-runbook.md` (settings, redacted `describe` output, time, cost). A successful apply is not evidence; the acceptance check is.

| Stage | Creates | Acceptance | Rough cost while up |
|---|---|---|---|
| 0 | Nothing: install Terraform, `init`, provider pins | `terraform version`, `validate` | none |
| 1 | Network, security groups, S3, ECR, secret, log group, SNS | Subnets in 2 AZs; S3 public access blocked; push the image to ECR | near zero |
| 2 | RDS | Instance private, encrypted, 17.x; connect from a temporary SSM session and run `db_bootstrap` | about USD 0.02/hour |
| 3 | ACM certificate, ALB, launch template, ASG (min 1, max 1 first) | `https://<domain>/health/` returns 200; HTTP redirects; migrate and import via SSM; the shop loads | about USD 0.05/hour total |
| 4 | Target tracking, max 2, alarms, scheduler | Alarm email received; scheduler run appears in the analytics run list | same |
| 5 | Evidence runs: baseline, autoscaling, session continuity, scheduler host loss | Evidence files per the scope | same |
| 6 | `terraform destroy` | Nothing tagged `Project=inf2006` remains; final balance recorded | none |

Costs are rough on-demand estimates; check them against the AWS pricing pages and the lab balance after each stage. Destroy between working sessions if the stack will sit idle for a day.

## Things this depends on

- **A domain** for stage 3. The user is buying one from an external registrar (cheaper than Route 53, and DNS stays outside the lab account, so it survives teardown). The purchase and DNS steps (buy, add ACM's validation CNAME, point `shop.<domain>` at the ALB) are explained in the stage 3 guide. Buying it before stage 3 is fine; nothing else needs it.
- **Application changes** before stage 3, backend-owned and through the review gate: configurable Gunicorn workers (`GUNICORN_WORKERS`, currently hardcoded 2 in the Dockerfile), and S3 media storage (`django-storages` with pre-signed URLs, only when the teammate's image fields land).
- **Stage-1 lab checks:** creating a secret and reading it from an instance with `LabInstanceProfile`; creating a budget; stage 4: whether EventBridge Scheduler accepts `LabRole`. Each result goes into the capability record.

## Review

Terraform is team infrastructure configuration. Each stage's code is self-reviewed, and before the first apply of stages 1 to 3 the configuration goes to the review gate (fresh-session Opus 5.5 or Astra Medium), findings logged in `docs/reviews/aws-terraform.md`. No apply without the user's explicit approval.

## Diagram

Drawn from this plan's resource list before stage 1, with these names; renamed only if a name changes during the build. Source `evidence/architecture.drawio`, export `evidence/architecture.png`.
