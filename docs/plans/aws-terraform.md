# AWS infrastructure in Terraform

Status (25 September 2026): planned, not started. Terraform is not installed on the development machine yet, nothing is written and nothing is applied. Replaces the console-first order in [cloud-independent-prep.md](cloud-independent-prep.md) B7 and the "reproduce afterwards" framing of B5.

**How this is built.** The user has no Terraform experience and is learning it while building. Work goes one stage at a time, and **nothing starts until the user says so**. Each stage begins with a guide that explains the Terraform concepts that stage uses (starting from what Terraform is in stage 0), then lists explicit steps; the user runs `plan` and `apply` and approves every change.

Integration note (26 September 2026): Terraform-first sequencing and the teammate's lab observations are retained. The current scope and reviewed [runtime handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff) govern service selection and application startup: WAF remains selected; SSM, EventBridge Scheduler and Lambda are not selected. S3 media delivery is proposed work, not implemented by the ML remediation. Lab observations below are teammate-reported, not independently rerun during Git integration.

## Decisions recorded here

| Decision | Detail |
|---|---|
| **Build method (changed 25 September 2026)** | Terraform creates and owns every team resource. The console is for watching and learning (reading settings, logs, metrics, CloudTrail) and for the few steps Terraform cannot do: the ACM validation record at an external registrar, confirming the SNS email subscription, and reading the lab balance. Anything created by hand is imported into Terraform or deleted, so there is no drift. Replaces "console first, then reproduce in Terraform". |
| Region and account | `us-east-1`, AWS Academy Learner Lab (`voclabs` role). One member's account is the integration account; one person applies. |
| IAM | Role creation is assumed denied. Reference `LabInstanceProfile` and `LabRole` through data sources; never create IAM roles. Recorded as external dependencies. |
| Database | RDS PostgreSQL pinned to **17.x** (the lab default is 18.3; the app, CI and all verification run on 17). Pick the newest 17 minor the lab offers. Single-AZ, private, encrypted, TLS forced. Master password managed by RDS in Secrets Manager (`manage_master_user_password`), so it never enters Terraform state. |
| Secrets | Terraform creates secret resources without values. Provision exact per-entrypoint schemas outside Terraform; the application startup loader retrieves its own secret using role credentials. Separate runtime, migration, trainer and bootstrap access as specified in the runtime handoff. Web instances must not read the master/bootstrap secret. |
| Object storage | **One S3 bucket**, prefixes `data/` (dataset), `exports/` (analytics exports), `media/images/`, `media/models/` (`.glb` shoe models). Block Public Access, versioning, SSE-S3, a deny-non-TLS policy. Browsers read media through short-lived pre-signed GET URLs. |
| CORS | Required for the `.glb` models (a 3D viewer fetches them from JavaScript; `<img>` does not need it). Rule: `GET` and `HEAD` from the application's HTTPS origin only, never `*`. Upload models with `Content-Type: model/gltf-binary`. |
| Image registry | ECR, immutable tags (git SHA), scan on push, keep the last 10 images. |
| HTTPS | ACM certificate on a team-owned domain with DNS validation at the registrar. Certificate ARN is a variable, so everything else can be applied before the domain exists. A test certificate fallback requires confirmed import permission, hostname matching and explicit client trust; it is not guaranteed. |
| Audit | CloudTrail **event history** (on by default, 90 days, free). Nothing created; shown on the diagram and cited in the threat-control map. |
| Batch operations | Explicitly triggered refresh/train/export/import and maintenance commands on one designated authorised runner. No EventBridge Scheduler, Lambda or SSM. Agree secure runner access with the infrastructure owner before deployment; no automatic scheduling is implemented. |
| Not built | EventBridge Scheduler, Lambda, Systems Manager, CloudFront, NAT gateway, ElastiCache, EKS or a separate analytics service. WAF remains selected and requires deployed verification. |

## Layout

`src/terraform/`, one root module, one file per concern, no child modules (easier to read and learn):

```
versions.tf        provider and Terraform version pins
providers.tf       aws provider, default_tags Project=inf2006 Env=evidence ManagedBy=terraform
variables.tf       region, domain, certificate ARN, alarm email, instance type, scaling target, flags
data.tf            AZs, explicitly selected AL2023 AMI, LabInstanceProfile, LabRole
network.tf         VPC 10.0.0.0/16, 2 public + 2 private subnets, IGW, route tables
security_groups.tf sg-alb (443/80 from internet), sg-app (8000 from sg-alb), sg-db (5432 from sg-app)
storage.tf         S3 bucket + policies + CORS, ECR repository + lifecycle
secrets.tf         Secrets Manager secret (value set outside Terraform)
database.tf        DB subnet group, parameter group, RDS instance
load_balancer.tf   ALB, target group (/health/), HTTPS listener, HTTP→HTTPS redirect
compute.tf         launch template (IMDSv2, encrypted EBS), ASG, target-tracking policy
user_data.sh.tftpl boot script
monitoring.tf      log group (7-day retention), SNS topic + email, alarms, 5xx metric filter
waf.tf             regional WAF association and scoped rules, subject to permission and plan review
outputs.tf         ALB DNS name, ECR URL, bucket name, RDS endpoint
```

Names follow `inf2006-<component>` (`inf2006-alb`, `inf2006-db`, `inf2006-app-asg`), and the diagram uses the same names.

**State.** Local state on the applying machine, never committed (`.gitignore` gains `*.tfstate*`, `*.tfplan`, `.terraform.lock.hcl` is committed). The scope forbids submitting state with secrets, and the design above keeps secret values out of it anyway. A remote S3 backend is not worth it for one applier and a two-week stack.

**Credentials.** The Learner Lab issues temporary credentials (from "AWS Details") that expire with the session. Export them before each `plan` or `apply`; an expired token mid-apply leaves a partial apply that the next run completes.

## Boot script (what every instance does)

1. Install Docker; log in to ECR with the instance profile.
2. Pass nonsecret AWS_SECRET_ID/AWS_REGION and required configuration to the container. The existing startup loader retrieves its entrypoint-specific secret. Do not read the RDS master secret or create a second secret loader in user data.
3. Read the private IP through IMDSv2 and set the exact DJANGO_HEALTH_PROBE_HOST=<private-ip>:8000 exception. Keep ordinary DJANGO_ALLOWED_HOSTS restricted to approved application hostnames; follow the runtime handoff.
4. Run the approved ECR image digest with DJANGO_TRUST_PROXY=true only behind the documented ALB/network boundary, and send sanitised logs to CloudWatch.

Require IMDSv2 and verify the hop limit/role delivery needed by the container. Systems Manager is not selected. A permitted secure administration path must be agreed before deployment; do not open public SSH by default.

One-off operations run on the designated authorised maintenance runner, not on every ASG boot: db_bootstrap, coordinated migrate, S3 dataset sync and import_dataset. Use the separate role/secret schemas and commands in the runtime handoff. Secure runner access remains an infrastructure prerequisite.

## Stages

Each stage: `fmt`, `validate`, `plan` saved to a file, the plan read aloud (creations, replacements, deletions, public exposure, IAM, NAT, Multi-AZ, cost), the user approves, `apply`, then an acceptance check and an entry in `evidence/aws-build-runbook.md` (settings, redacted `describe` output, time, cost). A successful apply is not evidence; the acceptance check is.

| Stage | Creates | Acceptance | Rough cost while up |
|---|---|---|---|
| 0 | Nothing: install Terraform, `init`, provider pins | `terraform version`, `validate` | none |
| 1 | Network, security groups, S3, ECR, secret, log group, SNS | Subnets in 2 AZs; S3 public access blocked; push the image to ECR | near zero |
| 2 | RDS | Instance private, encrypted, 17.x; connect through the agreed authorised maintenance runner and run `db_bootstrap` | about USD 0.02/hour |
| 3 | ACM certificate, ALB, launch template, ASG (min 1, max 1 first) | `https://<domain>/health/` returns 200; HTTP redirects; run coordinated migrations and import; the shop loads | about USD 0.05/hour total |
| 4 | Target tracking, max 2, alarms, WAF | Alarm email received; scoped WAF rules verified; explicit batch run verified | verify selected services against current pricing |
| 5 | Evidence runs: baseline, autoscaling, session continuity, batch failure/retry recovery | Evidence files per the scope | same |
| 6 | `terraform destroy` | Nothing tagged `Project=inf2006` remains; final balance recorded | none |

Costs are rough on-demand estimates; check them against the AWS pricing pages and the lab balance after each stage. Destroy between working sessions if the stack will sit idle for a day.

## Things this depends on

- **A domain** for stage 3. The user is buying one from an external registrar (cheaper than Route 53, and DNS stays outside the lab account, so it survives teardown). The purchase and DNS steps (buy, add ACM's validation CNAME, point `shop.<domain>` at the ALB) are explained in the stage 3 guide. Buying it before stage 3 is fine; nothing else needs it.
- **Application changes** before stage 3, backend-owned and through the review gate: configurable Gunicorn workers (`GUNICORN_WORKERS`, currently hardcoded 2 in the Dockerfile), and S3 media storage (`django-storages` with pre-signed URLs, only when the teammate's image fields land).
- **Stage-1 lab checks:** secret creation and role-separated retrieval with available lab profiles; budget and WAF permissions. Record actual results; listing APIs does not establish creation permission.

## Review

Terraform is team infrastructure configuration. Each stage's code is self-reviewed, and before the first apply of stages 1 to 3 the configuration goes to the review gate (fresh-session Opus 5.5 or Astra Medium), findings logged in `docs/reviews/aws-terraform.md`. No apply without the user's explicit approval.

## Diagram

Drawn from this plan's resource list before stage 1, with these names; renamed only if a name changes during the build. Source `evidence/architecture.drawio`, export `evidence/architecture.png`.
