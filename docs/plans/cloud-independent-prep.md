# Cloud-independent prep

Status (25 September 2026): **started, nothing deployed.** B4's probe was run against the lab (results under B4). B6 items 1 to 3 are done. **Revised 25 September 2026: Terraform first** (B5, detailed in [aws-terraform.md](aws-terraform.md)); the console is for learning and inspection only, and the console-first build (B7) is withdrawn. Terraform work starts when the user says so. The backend and analytics batches (6a, 6b, 6c) that this track was waiting for are complete locally, so B1, B3 and B4 onward can proceed. B2 (logging) is implemented. This file lists the preparation that does not depend on the dataset or on a deployed AWS environment, so it can be picked up in any gap. Nothing here is implemented, and nothing here is evidence. Requirements stay in the [scope](../../PROJECT_SCOPE_INF2006.md); AWS configuration rules stay in [AWS infrastructure](../AWS_INFRASTRUCTURE.md); status stays in the [implementation plan](../IMPLEMENTATION_PLAN.md).

Constraints that apply to every item (from [INF2003 baseline](../INF2003_BASELINE.md) rules 1, 2 and 7): the app must run without AWS, anything that touches an AWS service sits behind configuration with a local fallback, Terraform lives in one subdirectory under `src/`, and load scripts take a configurable base URL.

| # | Item | Depends on | Size |
|---|---|---|---|
| B1 | Locust load scenarios | seeded users and products | M |
| B2 | Structured application logging | nothing | S |
| B3 | Metric emission behind configuration | B2 (if using log-based metrics) | S |
| B4 | AWS lab capability check | user and teammate, lab access | S |
| B5 | Terraform build, phase by phase ([aws-terraform.md](aws-terraform.md)) | B4, B6 | L |
| B6 | Deployment mechanics (image, migrations, config) | B4 | M |
| B7 | ~~Console build and runbook~~ withdrawn 25 September 2026; replaced by B5 | | |

## B1: Locust load scenarios

Purpose: the scalability criterion needs repeated, comparable workload runs with real numbers (latency percentiles, throughput, error rate) against a fixed-capacity baseline and then autoscaling. The scripts can be written and validated locally now; the numbers that count come from the cloud runs.

- Location: `tests/load/locustfile.py` (submission tree keeps `tests/`). Base URL from the Locust `--host` argument or an environment variable; no AWS assumptions.
- Scenarios and weights (initial proposal): browse catalogue (most common), view product pages and paginate, log in, add to cart, view cart, checkout, view order history, operator analytics page (few users).
- Handle CSRF and sessions the way a browser does: read the token from the form or cookie, send it on POST. Do not disable CSRF for load tests.
- Users: a disposable load fixture, never the shared demo database (DOC-002: load fixtures run in a separate disposable database). Load users get a known password created by a fixture command; imported customers keep unusable passwords. Needs enough product stock that checkout does not just return 409, plus a dedicated scenario for insufficient stock and for a retried (double-submitted) checkout.
- Record per run: fixed capacity, request rate, p50/p95/p99, errors by type, and the RDS metrics captured during the run (see B3 and the monitoring evidence).
- Local dry run against Docker Compose validates the scripts only. Label any local numbers as such; they are not scaling evidence.

Open decision: which endpoints count as "the workload" for the autoscaling comparison. Recommendation: browse-heavy mix with a small checkout share, because checkout serializes on shared product rows and would measure lock contention, not scaling.

## B2: Structured application logging

**Implemented** as review fix SEC-001 (`config/jsonlog.py`, `RequestLoggingMiddleware`, the `LOGGING` setting, `tests/test_request_logging.py`); the field list is in [SECURITY.md](../SECURITY.md). Still to do in the cloud phase: confirm the lines reach CloudWatch Logs and write a Logs Insights query as monitoring evidence. The original plan follows.

`docs/SECURITY.md` requires request IDs, durations and sanitised errors, and no credentials, cookies or raw personal payloads. `src/config/settings.py` currently has no `LOGGING` configuration.

- JSON or key-value logs to stdout (containers and CloudWatch both read it): timestamp, request ID, method, path (no query string values that could carry secrets), status, duration, user ID (not name or email), and exception class for errors.
- A small middleware assigns or propagates a request ID and adds it to the response header.
- Gunicorn access log aligned to the same fields.
- Tests: a request produces one log line with an ID and duration; a login POST logs no password or cookie value; an exception is logged without its request body.

## B3: Metric emission behind configuration

Wanted for the operational evidence: at least one custom application metric (for example checkouts completed, or analytics refresh duration and data freshness, which the infrastructure contract lists under monitoring).

- Preferred: CloudWatch Embedded Metric Format, which is just a structured log line the platform turns into a metric. It needs no AWS SDK in the app and is a plain no-op locally.
- Alternative: a `boto3` call behind a setting that does nothing when unset. More code and a dependency, and it needs IAM permissions to be confirmed first (B4).
- Either way: unconfigured means silent, tested locally with no AWS credentials present.

## B4: AWS lab capability check

Mostly the user's and teammate's actions; this is the tracker's open Phase 1 infrastructure item. Follow stage 1 of the [setup order](../AWS_INFRASTRUCTURE.md#setup-order-and-verification). Produce a short written capability record covering:

- Account, region, and actual remaining balance. Credits are separate, not pooled. Budget rule: USD 30 planning cap of the integration account's initial USD 40, USD 10 reserved.
- Which services and roles are actually permitted: EC2, ALB, Auto Scaling, RDS, S3, CloudWatch, IAM (roles and instance profiles), ACM, Secrets Manager. The scope warns some of IAM, ACM and Secrets Manager may be unavailable.
- Instance types, quotas, and the RDS engine version available.
- HTTPS arrangement: a hostname and certificate path. The generated ALB hostname is not a team-owned certificate. This blocks exposing login traffic.
- Terraform: version and provider pins, and a single state owner per environment (two developers share infrastructure). Local versus remote state, custody, backup; state and secret-bearing plans are never committed.

Decision needed: where does the container image come from (a registry the lab allows, or built on the instance)? Record it here because it changes B6.

**Result (25 September 2026, `us-east-1`, AWS Academy Learner Lab, principal `assumed-role/voclabs`):** allowed: availability zones (6), VPC create and instance launch dry runs, t3.micro/small/medium, the Amazon Linux 2023 AMI, and listing ALB, Auto Scaling, RDS, S3, Secrets Manager, ACM, Route 53, ECR, SSM, CloudWatch, SNS and Budgets. Denied: the vCPU quota lookup. Instance profiles: `LabInstanceProfile` (and EMR ones); roles: `LabRole` and lab-generated ones, so role creation is assumed denied and roles are referenced, not created. RDS default engine 18.3; the build pins 17.x. Still to record: the balance from the lab page, and whether creating a secret, a budget and an EventBridge schedule with `LabRole` actually works (tested during the build). Before the record is saved to `evidence/`, replace the lab-generated role names with `<lab-generated>`. Image route: ECR. HTTPS: option A, the user is buying a domain.

**Tool** (step-by-step guide: [AWS_CAPABILITY_CHECK.md](../AWS_CAPABILITY_CHECK.md)): `python3 src/tools/aws_capability_check.py --region <lab region> --output evidence/aws-capability-record.md` writes most of this record in about a minute. It is read-only (list/describe calls and EC2 dry runs), so it creates nothing and costs nothing; it redacts account numbers and does not know the remaining balance, which is read from the lab page. Listing a service does not prove that creating it is permitted; that is proved by the Terraform plan and apply in stages 2 and 3.

**HTTPS options**, in order of preference. Terraform is written once with a `certificate_arn` input, so A and B differ only in where the ARN comes from:

| Option | Needs | Trade-off |
|---|---|---|
| A. Trusted ACM certificate on a domain the team controls, DNS-validated | ACM, plus DNS records you can create (Route 53 or the institution) | Best: real trust and no browser warnings. Blocked if ACM or DNS is unavailable |
| B. Self-signed certificate imported into ACM, attached to the ALB HTTPS listener | ACM import allowed | Needs no domain and credentials are still encrypted, but browsers warn and testers must accept the certificate. The scope allows this with a documented limitation |
| C. CloudFront's default `*.cloudfront.net` certificate in front of the ALB | CloudFront allowed | CloudFront is excluded by the scope, so this is a scope change; the CloudFront-to-ALB leg would be plain HTTP unless the ALB also has a certificate. Not recommended for credentials |
| D. HTTP only | | Not allowed by the scope for credential traffic, and the app has no setting for it (outside local mode it redirects to HTTPS and sets secure cookies) |

Ask the instructor for A now; plan for B as the guaranteed fallback.

## B5: Terraform build

**Revised 25 September 2026: Terraform first.** Terraform creates and owns every team resource; the console is for learning and inspection. The user is learning Terraform from zero, so each phase comes with a guide that explains the concepts it uses and lists explicit steps, and nothing starts until the user says so. Full plan, decisions, file layout and stages: [aws-terraform.md](aws-terraform.md). The notes below still apply.

Location: `src/terraform/`. Build in small reviewable steps that follow the setup order:

1. Provider, version pins, variables, `.gitignore` for state and plan files.
2. Network: VPC, subnets in two permitted Availability Zones, security groups (public ALB to app only; app to private RDS on 5432).
3. Persistent services: private Single-AZ RDS PostgreSQL, private S3 with public access blocked, permitted secret storage.
4. ALB (HTTPS listener once B4 settles it), launch template, ASG (minimum 1, test maximum 2, stickiness off), target group health check on `/health/`.
5. Target tracking on `ALBRequestCountPerTarget`, numeric target fixed before the final comparison.

Rules for every plan: inspect creations, replacements and deletions; broad IAM; public exposure; unexpected NAT gateways; Multi-AZ choices; capacity and cost. A successful `apply` is not evidence. No apply without the user's explicit approval. Pre-existing lab roles are recorded as external dependencies, not recreated.

Acceptance for the skeleton stage: `terraform validate` passes and a reviewed `plan` exists; nothing applied.

## B6: Deployment mechanics

Decisions the infrastructure contract leaves open, to settle after B4:

- Image build and distribution (see B4).
- Migrations run once through a coordinated step, not on every instance boot.
- Configuration and secrets injection: environment variables or permitted secret storage; `.env.example` stays placeholder-only.
- ALB health check Host handling: default probes may use target IPs, so `ALLOWED_HOSTS` handling must be resolved (the `/health/` endpoint validates allowed hosts today).
- Expired-session cleanup (`clearsessions`) needs a trigger; see the analytics scheduler decision, which is deferred until the refresh command exists.
- Dataset delivery: files synced from private S3 to a local directory before `import_dataset` (the import command reads local paths only).
- **Database TLS. Done 25 September 2026 ([deploy-readiness.md](deploy-readiness.md)):** the AWS RDS global bundle is vendored at `src/certs/` (source and SHA-256 recorded) and the image sets `POSTGRES_SSLROOTCERT=/app/certs/rds-global-bundle.pem`.
- **HSTS. Done 25 September 2026:** `DJANGO_HSTS_SECONDS` (default 3600 outside local mode, was a fixed year), so the self-signed HTTPS fallback stays usable and a short-lived domain is not pinned for a year.
- **Application role on RDS. Done 25 September 2026:** `src/tools/db_bootstrap.py` creates the non-superuser application role and its database once with the master credentials (`BOOTSTRAP_USER`/`BOOTSTRAP_PASSWORD`, never given to web containers); safe to rerun.
- **Behind the ALB the app needs:** `DJANGO_TRUST_PROXY=true` (otherwise Django sees plain HTTP and redirects forever), `DJANGO_ENV` not `local`, one shared `DJANGO_SECRET_KEY`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://<hostname>`, and `DJANGO_ALLOWED_HOSTS` containing the hostname and the instance's own private IP (the launch script reads it from instance metadata, so Django stays free of AWS calls) for the ALB health probe.

## B7: Console build (withdrawn 25 September 2026)

The console-first build was replaced by Terraform first (B5). What carries over: names `inf2006-<component>` with tags `Project=inf2006`, `Env=evidence`, `ManagedBy=terraform`; one runbook entry per phase in `evidence/aws-build-runbook.md` (what was created, settings, acceptance check and result, redacted `describe` output, time and cost; account IDs and public IPs redacted); and the settings table below, which the Terraform code implements.

**Design and best-practice settings**

| Service | Settings |
|---|---|
| VPC | Two AZs; public subnets for the ALB and app (no NAT cost); private subnets for RDS |
| Security groups | ALB accepts 443 from the internet; app accepts 8000 from the ALB group only; RDS accepts 5432 from the app group only |
| ALB | HTTPS listener; the HTTP listener only redirects; health check `/health/`; stickiness off |
| EC2 and Auto Scaling | Launch template with IMDSv2 required, encrypted EBS and SSM instead of SSH; min 1, max 2; target tracking on `ALBRequestCountPerTarget` |
| RDS | PostgreSQL, single-AZ (state the limitation), private, encrypted, TLS forced, short backup retention |
| S3 | One bucket; public access blocked, versioning, encryption, a deny-non-TLS bucket policy; CORS `GET`/`HEAD` from the application origin for `.glb` models |
| Secrets Manager | `DJANGO_SECRET_KEY` and the application database password (value set outside Terraform); RDS manages its own master password |
| IAM | `LabInstanceProfile` referenced, not created; no access keys on instances |
| CloudWatch | Log group with short retention, a metric filter on `status >= 500` with an alarm to SNS email, a dashboard |

**Cost rules:** because Terraform can recreate the stack in minutes, prefer `terraform destroy` over leaving it idle for a day. For shorter gaps: set the Auto Scaling group's desired capacity to 0; stop RDS (AWS restarts a stopped instance after 7 days); the ALB cannot be stopped, only deleted, and costs roughly USD 0.5 a day (estimate; verify current prices). Recalculate the remaining balance at the start and end of each session.

## Suggested order when the cloud phase starts

B4 done. Next: the architecture diagram, then B6's remaining app-side items (configurable Gunicorn workers, production `.env` template; S3 media storage once the image fields land) and B3, then B5 phase by phase when the user says to start, with B1's scripts finished before the first scaling run so the baseline and autoscaling runs use identical scenarios.
