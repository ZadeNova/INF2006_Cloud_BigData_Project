# AWS infrastructure in Terraform

Status (25 September 2026): planned, not started. Terraform is not installed on the development machine yet, nothing is written and nothing is applied. Replaces the console-first order in [cloud-independent-prep.md](cloud-independent-prep.md) B7 and the "reproduce afterwards" framing of B5.

**How this is built.** The user has no Terraform experience and is learning it while building. Work goes one stage at a time, and **nothing starts until the user says so**. Each stage begins with a guide that explains the Terraform concepts that stage uses (starting from what Terraform is in stage 0), then lists explicit steps; the user runs `plan` and `apply` and approves every change.

Integration note (26 September 2026): Terraform-first sequencing and the teammate's lab observations are retained. The current scope and reviewed [runtime handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff) govern service selection and application startup: WAF remains selected; SSM, EventBridge Scheduler and Lambda are not selected. S3 media delivery is proposed work, not implemented by the ML remediation. Lab observations below are teammate-reported, not independently rerun during Git integration.

**Decisions revised by the user (26 September 2026), superseding the integration note where they differ:** Systems Manager Session Manager is reinstated for administration and one-off jobs; a scheduler is an optional side quest after stage 5; WAF stays, narrowed to one login rate rule; the user is the Terraform owner and the only person who runs `apply`. Details in the table below.

## Decisions recorded here

| Decision | Detail |
|---|---|
| **Build method (changed 25 September 2026)** | Terraform creates and owns every team resource. The console is for watching and learning (reading settings, logs, metrics, CloudTrail) and for the few steps Terraform cannot do: the ACM validation record at an external registrar, confirming the SNS email subscription, and reading the lab balance. Anything created by hand is imported into Terraform or deleted, so there is no drift. Replaces "console first, then reproduce in Terraform". |
| Region and account | `us-east-1`, AWS Academy Learner Lab (`voclabs` role); the lab offers no Singapore region. Two Availability Zones (the ALB requires at least two). One member's account is the integration account. **Documented lab constraint:** the story is a Singapore shop, so the report states the added latency for Singapore customers (measure it rather than assume), that production would use `ap-southeast-1` (a one-variable change in Terraform), and that the data is synthetic (PDPA's Transfer Limitation Obligation would otherwise apply to overseas storage). Analytics keeps Singapore business dates regardless. |
| Ownership | **The user writes the Terraform and is the single state owner and the only person who runs `apply`.** The application owner supplies the image and the runtime contract ([handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff)). |
| IAM | **Role, user and policy creation is denied (verified 26 September 2026).** Terraform references `LabInstanceProfile` and `LabRole` through data sources and contains no `aws_iam_*` resources. Every instance and every job therefore runs as `LabRole`, so per-job IAM separation (web, migration, trainer, bootstrap) cannot be enforced at the IAM layer: any instance can read any team secret and the bucket. Least privilege is enforced where the lab allows it: separate database roles (runtime, migration, bootstrap), a separate secret per job so each container is only handed its own, security groups, S3 Block Public Access and TLS-only policy, no access keys anywhere. The intended per-job policies are written as reference JSON under `src/infrastructure/iam-reference/` (not applied) so the report can show the production design. Service roles needed by AWS itself (Auto Scaling's service-linked role, the scheduler's execution role) are checked in stage 1 and stage 'Optional'; RDS Enhanced Monitoring (needs its own role) is not used. |
| Database | RDS PostgreSQL pinned to **17.x** (the lab default is 18.3; the app, CI and all verification run on 17). Pick the newest 17 minor the lab offers. Single-AZ, private, encrypted, TLS forced. Master password managed by RDS in Secrets Manager (`manage_master_user_password`), so it never enters Terraform state. |
| Secrets | Terraform creates secret resources without values. Provision exact per-entrypoint schemas outside Terraform; the application startup loader retrieves its own secret using role credentials. Separate runtime, migration, trainer and bootstrap access as specified in the runtime handoff. Web instances must not read the master/bootstrap secret. |
| Object storage | **One S3 bucket**, prefixes `data/` (dataset), `exports/` (analytics exports), `media/images/`, `media/models/` (`.glb` shoe models). Block Public Access, versioning, SSE-S3, a deny-non-TLS policy. Browsers read media through short-lived pre-signed GET URLs. |
| CORS | Required for the `.glb` models (a 3D viewer fetches them from JavaScript; `<img>` does not need it). Rule: `GET` and `HEAD` from the application's HTTPS origin only, never `*`. Upload models with `Content-Type: model/gltf-binary`. |
| Image registry | ECR, immutable tags (git SHA), scan on push, keep the last 10 images. |
| HTTPS | ACM certificate on a team-owned domain with DNS validation at the registrar. Certificate ARN is a variable, so everything else can be applied before the domain exists. A test certificate fallback requires confirmed import permission, hostname matching and explicit client trust; it is not guaranteed. |
| Audit | CloudTrail **event history** (on by default, 90 days, free). Nothing created; shown on the diagram and cited in the threat-control map. |
| Administration access | **Systems Manager Session Manager (reinstated 26 September 2026).** Admins and developers open a shell on an instance with no inbound ports, no SSH keys and no bastion; every session is recorded in CloudTrail. Used for debugging (container logs, connectivity) and for one-off jobs. Needs the SSM agent (preinstalled on Amazon Linux 2023) and SSM permissions on `LabInstanceProfile`, to be confirmed in stage 1. No port 22. |
| Batch operations | Explicitly triggered refresh, train, export, import and maintenance commands (`db_bootstrap`, `migrate`, S3 sync and `import_dataset`, `refresh_analytics`, `clearsessions`), run by hand through Session Manager on one designated instance, following the runbook and the role-separated secrets in the runtime handoff. |
| Scheduler | **Optional side quest, after stage 5.** EventBridge Scheduler invoking SSM Run Command on a tagged instance, if the lab accepts `LabRole` as the scheduler's role. Until then jobs are triggered by hand, which the scope allows. |
| WAF | **Selected, narrow.** One regional web ACL on the ALB with one rate-based rule on `POST /login/` (credential stuffing, threat T7), Count mode first, then Block. No managed rule sets. The Locust source is exempted or the limit raised during scaling runs, and that is recorded. Lab permission to be confirmed in stage 1. |
| Not built | Lambda, CloudFront, NAT gateway, ElastiCache, EKS, a customer-managed KMS key (AWS-managed keys encrypt at rest), or a separate analytics service. EventBridge Scheduler only as the optional side quest above. |

## Layout

`src/infrastructure/` (decided 26 September 2026: the name already reserved by the runtime contract, excluded from the image by `src/.dockerignore` and checked by the ignore test in `tests/README.md`; it also holds the boot-script template and reference IAM policies, not only Terraform), one root module, one file per concern, no child modules (easier to read and learn):

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

Require IMDSv2 and verify the hop limit/role delivery needed by the container. Administration is through Systems Manager Session Manager; no SSH key and no port 22.

One-off operations run by hand through Session Manager on one designated instance, not on every ASG boot: db_bootstrap, coordinated migrate, S3 dataset sync and import_dataset. Use the separate secret schemas and commands in the runtime handoff.

## Stages

Each stage: `fmt`, `validate`, `plan` saved to a file, the plan read aloud (creations, replacements, deletions, public exposure, IAM, NAT, Multi-AZ, cost), the user approves, `apply`, then an acceptance check and an entry in `evidence/aws-build-runbook.md` (settings, redacted `describe` output, time, cost). A successful apply is not evidence; the acceptance check is.

| Stage | Creates | Acceptance | Rough cost while up |
|---|---|---|---|
| 0 | Nothing: install Terraform, `init`, provider pins | `terraform version`, `validate` | none |
| 1 | Network, security groups, S3, ECR, secret, log group, SNS | Subnets in 2 AZs; S3 public access blocked; push the image to ECR | near zero |
| 2 | RDS | Instance private, encrypted, 17.x; run `db_bootstrap` through Session Manager on a temporary instance or the first app instance | about USD 0.02/hour |
| 3 | ACM certificate, ALB, launch template, ASG (min 1, max 1 first) | `https://<domain>/health/` returns 200; HTTP redirects; run coordinated migrations and import; the shop loads | about USD 0.05/hour total |
| 4 | Target tracking, max 2, alarms, WAF | Alarm email received; scoped WAF rules verified; explicit batch run verified | verify selected services against current pricing |
| 5 | Evidence runs: baseline, autoscaling, session continuity, batch failure/retry recovery | Evidence files per the scope | same |
| Optional | EventBridge Scheduler plus SSM Run Command for `refresh_analytics` and `clearsessions` | A scheduled run appears in the analytics run list | small |
| 6 | `terraform destroy` | Nothing tagged `Project=inf2006` remains; final balance recorded | none |

Costs are rough on-demand estimates; check them against the AWS pricing pages and the lab balance after each stage. Destroy between working sessions if the stack will sit idle for a day.

## Things this depends on

- **A domain** for stage 3. The user is buying one from an external registrar (cheaper than Route 53, and DNS stays outside the lab account, so it survives teardown). The purchase and DNS steps (buy, add ACM's validation CNAME, point `shop.<domain>` at the ALB) are explained in the stage 3 guide. Buying it before stage 3 is fine; nothing else needs it.
- **Application changes** before stage 3, backend-owned and through the review gate: configurable Gunicorn workers (`GUNICORN_WORKERS`, currently hardcoded 2 in the Dockerfile), and S3 media storage (`django-storages` with pre-signed URLs, only when the teammate's image fields land).
- **Stage-1 lab checks:** secret creation and retrieval with `LabInstanceProfile`; Session Manager access to an instance; budget and WAF permissions. Record actual results; listing APIs does not establish creation permission.

## Reference IAM policies (planned 26 September 2026; written in stage 1, never applied)

**Why.** The lab denies IAM role, user and policy creation, so every job runs as `LabRole` and per-job least privilege cannot be enforced (see the IAM row above). The brief grades "least privilege" explicitly. Writing the policies we *would* attach in production shows the design was done and the limit is the platform's, not ours. About an hour; high return for the Security criterion.

**Where.** `src/infrastructure/iam-reference/`, one JSON file per role plus a short `README.md`. These files are documentation: Terraform does not read them, `terraform plan` must show no `aws_iam_*` resources, and the README says so in its first line.

| File | Production role for | Allows (scoped to named resources, no `*` actions) |
|---|---|---|
| `web-runtime.json` | Web instances in the Auto Scaling group | `secretsmanager:GetSecretValue` on the **web runtime secret only**; `ecr:GetAuthorizationToken` plus pull actions on the `inf2006-app` repository; `s3:GetObject` on `media/*` (for pre-signed URLs); `logs:CreateLogStream`/`PutLogEvents` on the app log group; the AWS-managed `AmazonSSMManagedInstanceCore` for Session Manager |
| `migration.json` | The one-off migration run | `GetSecretValue` on the **migration secret only**; ECR pull; logs. No S3 |
| `bootstrap.json` | The one-off `db_bootstrap` run | `GetSecretValue` on the **bootstrap secret only**; ECR pull; logs. Nothing else |
| `maintenance.json` | One-off Django commands: `import_dataset`, `refresh_analytics`, `load_customer_segments`, `clearsessions` | `GetSecretValue` on the **web runtime secret** (these are Django management commands, per the runtime handoff); `s3:GetObject` on `data/*` and `exports/*`; logs |
| `batch-trainer.json` | Standalone training and the refresh verifier | `GetSecretValue` on the **trainer/verifier secret only** (no Django signing key); `s3:GetObject` on `data/*`; `s3:GetObject`/`PutObject` on `exports/*`; logs |
| `scheduler.json` (optional side quest) | EventBridge Scheduler's execution role | `ssm:SendCommand` limited to the `AWS-RunShellScript` document and instances tagged `Project=inf2006` |

Each file also carries its trust policy (who may assume the role: `ec2.amazonaws.com`, or `scheduler.amazonaws.com` for the scheduler). Secret and bucket ARNs are written with placeholders (`<account>`, `<region>`), which also satisfies the redaction rule.

**How it is used as evidence.**
- Threat-control map: rows T8 and T9 (secrets, database and storage access) show status "Partial, lab constraint", citing these files as the intended control and listing what *is* enforced (separate database roles, a separate secret per job, security groups, S3 Block Public Access and TLS-only policy, no access keys).
- Report §4: one paragraph, "designed per-job roles; the lab permits only `LabRole`; here is what enforces least privilege instead".
- Validation (cheap and optional): run each file through IAM Access Analyzer's policy validation (`aws accessanalyzer validate-policy`) if the lab allows it, and record the output next to the files. A policy that validates cleanly is stronger evidence than one that only looks right.

**Acceptance.** Six JSON files that parse; a README stating they are not applied and why; no `aws_iam_*` resource in any plan; the threat-map rows cite them.

## Review

Terraform is team infrastructure configuration. Each stage's code is self-reviewed, and before the first apply of stages 1 to 3 the configuration goes to the review gate (fresh-session Opus 5.5 or Astra Medium), findings logged in `docs/reviews/aws-terraform.md`. No apply without the user's explicit approval.

## Diagram

Drawn from this plan's resource list before stage 1, with these names; renamed only if a name changes during the build. Source `evidence/architecture.drawio`, export `evidence/architecture.png`.
