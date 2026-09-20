# Cloud-independent prep

Status: **not started, deliberately deferred.** Sequencing decided with the user: finish the backend and analytics batches (6a, 6b, 6c) first, then the cloud work. This file lists the preparation that does not depend on the dataset or on a deployed AWS environment, so it can be picked up in any gap. Nothing here is implemented, and nothing here is evidence. Requirements stay in the [scope](../../PROJECT_SCOPE_INF2006.md); AWS configuration rules stay in [AWS infrastructure](../AWS_INFRASTRUCTURE.md); status stays in the [implementation plan](../IMPLEMENTATION_PLAN.md).

Constraints that apply to every item (from [INF2003 baseline](../INF2003_BASELINE.md) rules 1, 2 and 7): the app must run without AWS, anything that touches an AWS service sits behind configuration with a local fallback, Terraform lives in one subdirectory under `src/`, and load scripts take a configurable base URL.

| # | Item | Depends on | Size |
|---|---|---|---|
| B1 | Locust load scenarios | seeded users and products | M |
| B2 | Structured application logging | nothing | S |
| B3 | Metric emission behind configuration | B2 (if using log-based metrics) | S |
| B4 | AWS lab capability check | user and teammate, lab access | S |
| B5 | Terraform skeleton | B4 | L |
| B6 | Deployment mechanics (image, migrations, config) | B4, B5 | M |

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

## B5: Terraform skeleton

Location: one dedicated directory under `src/` (name fixed at scaffolding, for example `src/terraform/`). The user is also learning Terraform, so build in small reviewable steps that follow the setup order:

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

## Suggested order when the cloud phase starts

B4 first (it can start any time and unblocks everything), then B2 and B3 (small, local), B5 in stages with B6 decisions, and B1 scripts finished before the first scaling run so the baseline and autoscaling runs use identical scenarios.
