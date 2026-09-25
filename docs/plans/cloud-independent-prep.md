# Cloud-independent prep

Status (25 September 2026): **started, nothing deployed.** B4's probe was run against the lab (results under B4). B6 items 1 to 3 are done. **Revised 25 September 2026: Terraform first** (B5, detailed in [aws-terraform.md](aws-terraform.md)); the console is for learning and inspection only, and the console-first build (B7) is withdrawn. Terraform work starts when the user says so. The backend and analytics batches (6a, 6b, 6c) that this track was waiting for are complete locally, so B1, B3 and B4 onward can proceed. B2 (logging) is implemented. This file lists the preparation that does not depend on the dataset or on a deployed AWS environment, so it can be picked up in any gap. Historical task descriptions below are superseded by completed Phase 0-6 runtime work in the tracker; planned cloud work is not deployed evidence. Requirements stay in the [scope](../../PROJECT_SCOPE_INF2006.md); AWS configuration rules stay in [AWS infrastructure](../AWS_INFRASTRUCTURE.md); status stays in the [implementation plan](../IMPLEMENTATION_PLAN.md).

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
- Which services and roles are actually permitted: EC2, ALB, Auto Scaling, RDS, S3, CloudWatch, IAM (roles and instance profiles), ACM, Secrets Manager, ECR, SNS, CloudTrail, WAF. Record EC2 instance roles, trust/resource policies and deployer PassRole permissions. List access proves none of these permissions.
- Instance types, quotas, and the RDS engine version available.
- HTTPS arrangement: a hostname and certificate path. The generated ALB hostname is not a team-owned certificate. This blocks exposing login traffic.
- Terraform: version and provider pins, and a single state owner per environment (two developers share infrastructure). Local versus remote state, custody, backup; state and secret-bearing plans are never committed.

Selected image route: ECR. Verify creation/push/pull permissions; resolve denied access before deployment. Secrets Manager is selected for credentials and the shared signing key; unavailable storage/retrieval blocks deployment. No plaintext user-data/launch-template fallback. Systems Manager is not selected; agree a secure administration method with the infrastructure owner.

**Teammate-reported lab probe (25 September 2026):** us-east-1 Learner Lab list/describe checks and EC2/VPC dry runs succeeded for the probed services; the vCPU quota lookup was denied. LabInstanceProfile/LabRole were available; role creation was not established. PostgreSQL default reported 18.3, while this build targets 17.x. ECR and a domain/ACM route are planned. No raw probe evidence was independently rerun during integration; redact lab-generated names before retention. Creation permissions, balance, HTTPS, WAF and role-separated secret access remain actual deployment gates.

**Tool** (step-by-step guide: [AWS_CAPABILITY_CHECK.md](../AWS_CAPABILITY_CHECK.md)): `python3 src/tools/aws_capability_check.py --region <lab region> --output evidence/aws-capability-record.md` writes most of this record in about a minute. It is read-only (list/describe calls and EC2 dry runs), so it creates no resources; it redacts account numbers and does not know the remaining balance, which is read from the lab page. Listing a service does not prove that creating it is permitted; a Terraform plan does not prove it either. Verify the authorised Terraform plan/apply and actual deployed behaviour.

**HTTPS options**, in order of preference. Terraform is written once with a `certificate_arn` input, so A and B differ only in where the ARN comes from:

| Option | Needs | Trade-off |
|---|---|---|
| A. Trusted ACM certificate on a domain the team controls, DNS-validated | ACM, plus DNS records you can create (Route 53 or the institution) | Best: real trust and no browser warnings. Blocked if ACM or DNS is unavailable |
| B. Self-signed certificate imported into ACM, attached to the ALB HTTPS listener | ACM import allowed, a matching hostname and explicit client trust | A limited test arrangement requiring lab/instructor agreement and documented client setup; not a guaranteed fallback |
| C. CloudFront's default `*.cloudfront.net` certificate in front of the ALB | CloudFront allowed | CloudFront is excluded by the scope, so this is a scope change; the CloudFront-to-ALB leg would be plain HTTP unless the ALB also has a certificate. Not recommended for credentials |
| D. HTTP only | | Not allowed by the scope for credential traffic, and the app has no setting for it (outside local mode it redirects to HTTPS and sets secure cookies) |

Confirm A with the instructor. B requires permission, hostname matching and explicit trust; if neither works, HTTPS remains blocked. HSTS configuration does not establish certificate trust.

## B5: Terraform build

**Revised 25 September 2026: Terraform first.** Terraform creates and owns every team resource; the console is for learning and inspection. The user is learning Terraform from zero, so each phase comes with a guide that explains the concepts it uses and lists explicit steps, and nothing starts until the user says so. Full plan, decisions, file layout and stages: [aws-terraform.md](aws-terraform.md). The notes below still apply.

Location: `src/terraform/`. Build in small reviewable steps that follow the setup order:

1. Provider, version pins, variables, `.gitignore` for state and plan files.
2. Network: VPC, subnets in two permitted Availability Zones, security groups (public ALB to app only; app to private RDS on 5432).
3. Persistent services: private Single-AZ RDS PostgreSQL, private S3 with public access blocked, selected Secrets Manager storage and role retrieval.
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
- **HSTS. Done 25 September 2026:** `DJANGO_HSTS_SECONDS` (default 3600 outside local mode, was a fixed year), to bound the policy lifetime; this does not make an untrusted or mismatched test certificate acceptable.
- **Application roles on RDS:** Phase 5 implemented distinct runtime/migration roles and refusal of unsafe bootstrap state. Follow the [runtime handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff) and current bootstrap command; master credentials are never given to web containers.
- **Behind the ALB:** follow the reviewed runtime handoff for non-local mode, startup secret schema, shared signing key, trusted proxy boundary, explicit application hosts/CSRF origins and narrow DJANGO_HEALTH_PROBE_HOST=<private-ip>:8000. Do not broaden ordinary allowed hosts to implement health probes.

## B7: Console build (withdrawn 25 September 2026)

The console-first build was replaced by Terraform first (B5). What carries over: names `inf2006-<component>` with tags `Project=inf2006`, `Env=evidence`, `ManagedBy=terraform`; one runbook entry per phase in `evidence/aws-build-runbook.md` (what was created, settings, acceptance check and result, redacted `describe` output, time and cost; account IDs and public IPs redacted); and the settings table below, which the Terraform code implements.

**Design and best-practice settings**

| Service | Settings |
|---|---|
| VPC | Two AZs; public subnets for the ALB and app (no NAT cost); private subnets for RDS |
| Security groups | ALB accepts 443 from the internet; app accepts 8000 from the ALB group only; RDS accepts 5432 from the app group only |
| ALB | HTTPS listener; the HTTP listener only redirects; health check `/health/`; stickiness off |
| EC2 and Auto Scaling | Launch template with IMDSv2 required, encrypted EBS and an agreed secure administration method (SSM not selected); min 1, max 2; target tracking on `ALBRequestCountPerTarget` |
| RDS | PostgreSQL, single-AZ (state the limitation), private, encrypted, TLS forced, short backup retention |
| S3 | Public access blocked, versioning, encryption, a deny-non-TLS bucket policy |
| IAM | An instance profile; no access keys on instances |
| CloudWatch / SNS | Sanitised logs with short retention, a metric filter/alarm, dashboard and verified notification |
| ECR / Secrets Manager | Verified image push/pull and role-based secret retrieval; no secrets in user data |
| CloudTrail / WAF | Verify recorded management events and scoped login protection through ALB |

**Cost rules:** plan teardown or idle settings with the shared-state owner and preserve required data/evidence; review any `terraform destroy` before execution. For shorter gaps: set the Auto Scaling group's desired capacity to 0; stop RDS (AWS restarts a stopped instance after 7 days); the ALB cannot be stopped, only deleted, and costs roughly USD 0.5 a day (estimate; verify current prices). Recalculate the remaining balance at the start and end of each session.

## Suggested order when the cloud phase starts

B4 done. Next: the architecture diagram, then B6's remaining app-side items (configurable Gunicorn workers, production `.env` template; S3 media storage once the image fields land) and B3, then B5 phase by phase when the user says to start, with B1's scripts finished before the first scaling run so the baseline and autoscaling runs use identical scenarios.
