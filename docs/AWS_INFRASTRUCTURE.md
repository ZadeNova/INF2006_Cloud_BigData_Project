# AWS infrastructure contract

> Final architecture: variant B (ECS on Fargate), ADR-018. Variant A (EC2) = evaluated alternative.

> **Note (updated 9 October 2026):** this document describes both variants: A (EC2 + Auto Scaling group, the evaluated alternative, measured on 8 October) and B (ECS on Fargate, measured on 9 October). The final architecture is variant B, recorded in [ADR-018](decisions/ADR-018-final-architecture-ecs-fargate.md) (index: [docs/decisions/](decisions/README.md)).

**Which AWS file owns what.** Link to the owner rather than copy.

| Question | Owner |
|---|---|
| What the deployed system is: baseline, runtime contract, secrets, TLS, health, both variants | this file |
| Why we chose it: each decision, options and driver | [decisions/](decisions/) (one ADR per decision) |
| How the comparison is run, the schedule and the carried-forward decisions | [plans/aws-ecs-comparison.md](plans/aws-ecs-comparison.md) |
| How the load runs are built | [plans/load-harness.md](plans/load-harness.md) |
| How to bring it up, take it down and recover | [src/infrastructure/README.md](../src/infrastructure/README.md) |
| What was applied, when, with what result, and the lab capability record | [evidence/aws-build-runbook.md](../evidence/aws-build-runbook.md) |
| Independent review of the Terraform | [reviews/aws-terraform.md](reviews/aws-terraform.md) |

Status (9 October 2026): **`base/` and variant A (`ec2/`) are written and were applied and verified on 1 October 2026** in the team's Learner Lab account: `https://shop-ec2.fourtytwofactors.me` served the shop with the dataset imported, the operator account created, analytics refreshed, scaling, alarms and the WAF in place, and `smoke.sh` passing 8 of 8. The `ec2/` stack is torn down between work sessions; `base/` (RDS, zone, certificate, ECR, secrets) stays up. **Variant B (`fargate/`) was applied and measured on 9 October 2026 (results in the evidence index).** Variant A was applied again and measured on 8 October 2026 (load, scale-out, replacement, alarms, deployed security checks; one repeat each): see [evidence/README.md](../evidence/README.md). Records: [build runbook](../evidence/aws-build-runbook.md) (as-built log and lab capability record), [how to run it](../src/infrastructure/README.md), [decisions](decisions/). Read [scope](../PROJECT_SCOPE_INF2006.md) for budget and risks. Verify actual lab permissions and regional prices before each deployment; the lab capability record in the runbook lists what was observed and what was learned by apply.

## Baseline

- Terraform lives in `src/infrastructure/` (confirmed 26 September 2026), owned by the user, with the AWS provider pinned to 6.x and locked in `.terraform.lock.hcl`. State is local on one apply device (below).
- HTTPS ALB across two permitted Availability Zones, health-checked targets: EC2 instances in an ASG (variant A) or ECS Fargate tasks (variant B).
- Same container image, signing configuration and database sessions on every instance; stickiness disabled.
- Private Single-AZ RDS PostgreSQL, inbound only from application security group. State its availability limitation. A controlled Multi-AZ failover test was planned ([plan](plans/aws-ecs-comparison.md), section 3) and was not run; RDS stayed single-AZ ([test-resilience.md](../evidence/test-resilience.md)).
- One private S3 bucket for checked inputs and optional exports (`data/`, `exports/`); block public access, versioning, encryption and a TLS-only policy, all in Terraform. The bucket itself is created with the CLI and looked up as a data source, because the Learner Lab's service control policy denies `s3:GetBucketObjectLockConfiguration`, which the `aws_s3_bucket` resource reads on every plan. Product images and `.glb` models are static files in the image served by WhiteNoise, not S3 media (decided 29 September 2026). Retain local input mode.
- CloudWatch sanitised logs/metrics with short retention.
- IAM runtime roles and Secrets Manager for database credentials/shared Django signing key; unavailable storage or retrieval blocks deployment. No baked-in access keys or plaintext user-data/launch-template secrets.
- ECR is the selected image route. SNS and a regional WAF (one rate-based rule on `POST /login/`, count mode first) are applied by Terraform; CloudTrail is the account's default event history (90 days), not a Terraform resource. Verify lab permissions, roles, costs and actual behaviour before claiming readiness. **Systems Manager Session Manager is selected (reinstated 26 September 2026)** for administration and one-off jobs, with no SSH and no inbound admin ports; the database and data jobs run through SSM Run Command ([ADR-009](decisions/ADR-009-database-jobs-by-ssm-run-command.md)). Decisions: [docs/decisions/](decisions/) and [plan section 13](plans/aws-ecs-comparison.md); the retired stage plan is history only ([aws-terraform.md](archive/plans/aws-terraform.md)).
- Region: `us-east-1`, two Availability Zones; the lab has no Singapore region. This is a documented lab constraint against the Singapore story (latency and data-residency notes in the decision record).
- Offline ML uses an explicitly triggered batch workflow. Saved-model inference and Lambda are not part of the plan (user decision, 3 October 2026); EventBridge Scheduler (with SSM Run Command) is an optional side quest after the evidence runs. Preserve local training/loading and keep ML libraries outside the web image.

Initial/minimum ASG capacity one, default test maximum two. Have two healthy targets before failure demonstration. Additional capacity requires quota/cost checks. Budget baseline: EC2 public subnets with application ingress restricted to ALB to avoid mandatory NAT cost; RDS private. Restrict management access separately through permitted facilities.

## Variant B: ECS on Fargate (built and measured; the final architecture)

> **Status (9 October 2026):** written in `src/infrastructure/fargate/`, applied (27 resources) and measured on 9 October 2026, then torn down; results are side by side with A in [evidence/README.md](../evidence/README.md).

Status (6 October 2026, written before the first apply; see the note above for the 9 October result): **written and checked offline (`terraform validate`).** `src/infrastructure/fargate/` exists and uses the shared `modules/web-entry` ([ADR-014](decisions/ADR-014-shared-web-entry-module.md)); the choices below are recorded in ADR-015 to ADR-017 and [fargate-variant.md](plans/fargate-variant.md). Where they differ from this text, the ADRs govern until the post-sprint sync. The as-built result is in the [runbook](../evidence/aws-build-runbook.md).

**Same as variant A (so the comparison is fair).** One image digest, the same RDS from `base/`, the same ALB design and `/health/` check, app compute in the public subnets with public IPs and no NAT gateway (`sg-app` accepts port 8000 only from `sg-alb`; RDS stays private), no stickiness, the same Gunicorn settings, `LabRole` for every role (no IAM creation), the same secrets and runtime contract below, the same WAF rule on `POST /login/`, and the same request-count scaling metric. Matched compute: Fargate 2 vCPU / 4 GB against the `c5.large` (2 vCPU, 4 GiB).

**What `fargate/` owns.** Its own ALB, `sg-alb` and `sg-app`, an ECS cluster, a task definition, a service, scaling, the alias record `shop-fargate.fourtytwofactors.me` (the shared ACM certificate already names it, [ADR-006](decisions/ADR-006-one-acm-certificate-two-hostnames.md)), and a per-stack log group. It reads `base/` through `terraform_remote_state` and is applied and destroyed on its own; `base/` never reads it.

**What differs from variant A.**

| | A: EC2 + ASG | B: ECS on Fargate |
|---|---|---|
| Runs | Docker on an AL2023 instance, started by user data | ECS task, no instance to manage |
| App scaling | ASG target tracking on `ALBRequestCountPerTarget` | Application Auto Scaling on the same metric |
| Health-probe host | read from IMDSv2 at boot | read from the ECS metadata endpoint by a `command` override, with no image change |
| One-off jobs | `app-job` through SSM Run Command | `aws ecs run-task` with overrides, waiting for the exit code |
| Credentials | instance role (`iam-role`) | task role (`container-role`, already accepted by `config/secrets.py`) |
| Network | host port 8000 | `awsvpc`, one network interface per task |
| Capacity limit | instance quota | a Fargate vCPU quota the lab does not let us read; learned at apply |

**Unknown until tried.** Whether `LabRole` can act as an ECS task and execution role, whether a Fargate task can pull the ECR image and write to CloudWatch, and how far the vCPU quota lets B scale. The user reports the lab does not block Fargate or Application Auto Scaling (not recorded from output); the first apply of `fargate/` was the test (the probe script was retired). The 8 October preflight did record that `LabRole` trusts `ecs-tasks.amazonaws.com` and that the Fargate vCPU quota is not readable in the lab (`evidence/raw/PRE_2026-10-08_labrole.txt`, `PRE_2026-10-08_quota.txt`); whether B applies and scales is the 9 October result. The unmeasured question of whether a difference comes from ECS or from Fargate is stated in the report from the design, because ECS on EC2 was dropped for time.

**Acceptance for B** (same as A, plan section 10): the task is healthy behind its ALB over HTTPS at its own hostname, no port 22, running from the recorded digest, logs arriving in CloudWatch, and the database jobs pass as the runtime login. Then the load runs, which informed the final architecture (variant B, ADR-018).

## Early gates and deployment

Verify region, service/role permissions, instance types, quotas and actual balance. Credits are separate, not a pooled USD 200. Establish hostname/certificate validation for HTTPS; the generated ALB hostname is not a team-owned certificate arrangement.

Foundation supplies GET/HEAD /health/ as database-independent process liveness (200, no-store), with allowed-host validation and internal HTTPS-redirect exemption. The separate check_database management command verifies PostgreSQL and applied migrations for operator/deployment readiness. Never use database readiness to replace all app instances during shared RDS failure. Local Compose uses a 10s probe interval, 2s request timeout, 3s process timeout, three retries and 10s start period; local startup was verified, but these are not calibrated AWS settings. The opt-in exact probe Host exception below handles target IP probes while normal hosts remain strict; deployment must verify the selected target address and measure thresholds/timeouts/warmup. AWS deployments are claimed only as recorded in the [evidence index](../evidence/README.md).

Deploy repeatable images and run migrations once through a coordinated step, not racing on every instance boot. Test compatibility/recovery before rollout. Terraform state can contain secrets and stays outside source/submission.

Use target tracking with ALBRequestCountPerTarget as the scoped baseline. CPU target tracking is an alternative requiring a documented scope decision. Fix numeric targets before final comparison. Record desired/in-service/healthy capacity, latency percentiles, throughput, errors and scaling delay. Allow startup and health checks. Scale-in drains requests; abrupt crashes can still fail them.

## Conditional cache

ElastiCache is not required yet. If selected, record engine/version, lab access, security settings and regional cost. Use shared cache-aside for catalogue/sales summaries, bounded expiry, after-commit invalidation and period/run-aware keys. No authoritative stock, sessions or carts in cache.

Explicitly handle cache read/write connection failures and timeouts; fall back to RDS and temporarily bypass repeated failures. Authorise privileged requests before cache access. Compare disabled, warmed and unavailable cache at fixed app capacity, including fallback database pressure. Multi-AZ replicas require a separate cost decision.

## Operations and teardown

Monitor latency/errors, target health, DB pressure and analytics freshness. Capture dated outputs and interpretation for an operational query/alert. Use a USD 30 planning cap against the integration account's USD 50 allocation, reserve roughly USD 20, and recalculate actual remaining funds. The team keeps this conservative cap even though the Learner Lab page showed USD 50 on 29 September 2026.

Develop locally and deploy for bounded tests. Inventory charges: compute, ALB, RDS, IPv4, storage/snapshots, S3 versions, logs, secrets, ECR, SNS, CloudTrail, WAF. Capture evidence before teardown. Stopping EC2 does not stop all charges. Verify lab-end behaviour and delete only intended test resources. Do not claim uninterrupted availability.

## Setup order and verification

The table below is the dependency order the build follows; the order actually executed, with commits, results and costs, is the [runbook](../evidence/aws-build-runbook.md) and the schedule is [plan section 9](plans/aws-ecs-comparison.md). Use dependency order and small reviewable changes, not an unexamined full deployment. **Deployment method: Terraform first.** Terraform creates and owns every team-managed resource (named `inf2006-grp21-<component>`, tagged `Project=inf2006-grp21` and `ManagedBy=terraform`), in `base/` (long-lived) and one folder per variant. The console is for inspection only: reading settings, logs, metrics and CloudTrail event history, plus the few steps Terraform cannot do (the ACM validation record at the external domain registrar, confirming the SNS email subscription, reading the lab balance). Anything created by hand is imported into Terraform or deleted, so there is no drift. Pre-existing lab roles (`LabRole`, `LabInstanceProfile`) are referenced as external dependencies, never recreated. Record authorised emergency/manual changes and reconcile configuration afterwards.

| Stage | Work and verification |
|---|---|
| 1. Access and bootstrap | Verify account/region/permissions and HTTPS path; configure provider, variables, version pins and state handling. Ignore state files and secret-bearing plans from the start. |
| 2. Network and runtime access | Create VPC/subnets/security groups and permitted instance-role/logging setup. Check actual SG references: public ALB to app only, app to private RDS on 5432. Use port 80 only for redirect or a non-sensitive placeholder probe, never login traffic. |
| 3. Persistent services/configuration | Create private Single-AZ RDS, private S3 and Secrets Manager storage/access. Establish a bounded backup/retention policy and costs. Verify allowed connectivity from the intended app role/SG and denied anonymous S3 access; one successful DB connection does not prove isolation. |
| 4. Minimal app smoke deployment | Deploy ALB/ASG with a minimal app image, health checks and logs; prove application-to-RDS connectivity during Phase 1. A static placeholder can isolate routing problems but is not the final smoke acceptance test. |
| 5. Real workflow | Roll out the app with coordinated migrations, tested HTTPS, secure session settings and S3 import; verify permissions, shared sessions and app behaviour. HTTPS must be ready before exposing authentication or credentials. |
| 6. Scaling/recovery evidence | Measure the fixed-capacity baseline then autoscaling, failure and monitoring outcomes. Keep cost and permission limits visible. |
| 7. Conditional enhancements | Consider ElastiCache only after required services/tests work and its selection is justified. Use the documented cache-aside pattern, not an assumed automatic database fallback. |

IAM/runtime credentials and logs must exist before dependent verification; do not postpone all observability to the final stage. Reuse an authorised smoke instance for probes where practical instead of adding unnecessary disposable infrastructure.

Before an AWS mutation, inspect the Terraform plan for creations/replacements/deletions, broad IAM, public exposure, unexpected NAT gateways, Multi-AZ DB choices, capacity and costs. Terraform success is not functional/security evidence. Honour existing user authorisation; if a plan exceeds it or disrupts shared resources, present the concrete plan and obtain the missing approval before applying. No blanket apply/destroy permission is implied by this document.

With two infrastructure developers, choose one state owner/writer per environment. **Decided 28 to 30 September 2026: local state on one apply device (the owner's laptop), which alone runs plan, apply and destroy; other developers write and validate code through git.** A remote S3 backend was considered and not chosen: a committed backend block would make `terraform init` fail for a reviewer without the team's account (the brief requires the project to be runnable without a cloud login), and the state bucket would have to survive teardown; a production deployment would use an S3 backend with versioning and locking. Custody: apply only committed code, back the state up after every apply to a private location off the laptop, never through git, and never create independent states managing the same resources. State/plan files may contain secrets and must not be committed or submitted. After any approved change, preserve a sanitised record, verify expected behaviour and coordinate teardown with the other developer.

## Database runtime preparation

The application and standalone `analytics/segment_customers.py`, `analytics/verify_refresh.py`
(including `--database-url`) share `src/config/database.py`. `DJANGO_ENV` defaults to
`production`: connections require explicit database/user/password/host, `verify-full`,
a readable CA bundle, and certificate hostname verification. GSS encryption fallback is
disabled so it cannot replace this TLS check. DSNs accept only database/user/password/host/port
and TLS mode/CA fields; service/address indirection is refused. The image vendors the RDS CA
at `/app/certs/rds-global-bundle.pem`; standalone tools use `POSTGRES_SSLROOTCERT` pointing
to that public file or an approved read-only CA mount. Explicit `DJANGO_ENV=local` preserves
local PostgreSQL without TLS. This policy is local preparation, not proof of RDS connectivity.

`python tools/db_bootstrap.py` is a coordinated one-off operation for a dedicated PostgreSQL
17 application database, never an ASG startup action. Its inputs are `POSTGRES_HOST/PORT/DB`,
`POSTGRES_USER/PASSWORD` (runtime), `MIGRATION_USER/PASSWORD` (schema owner), and
`BOOTSTRAP_USER/PASSWORD` (administration); the three identities must differ. The same TLS
policy applies; `BOOTSTRAP_SSLMODE` cannot weaken it. Credential delivery remains the Secrets
Manager startup handoff; no real secret values belong in commands, images or launch templates.

Bootstrap preflights both managed roles before changing passwords: no administrative attributes
or parent-role memberships, no runtime-owned objects, database/schema creation rights or explicit database TEMPORARY grant,
no excessive migration-owner global/public default privileges for runtime/PUBLIC, and no foreign
database owner or unrelated public-schema object owner. Normal PUBLIC TEMPORARY defaults are
removed during setup; an explicit runtime grant is refused before passwords change. Existing mismatches are
refused, not silently adopted or reconciled. Use a new dedicated database, or separately plan
an authorised migration of an old owner-role deployment. Leave the RDS initial database blank.
The master manages roles but does not remain able to SET ROLE/inherit application ownership:
PostgreSQL 17 creator ADMIN memberships remain for idempotent password updates, with INHERIT
and SET false; temporary SET for database creation is restored. Unexpected broader pre-existing
master memberships are refused. Membership direction is master-to-managed-role, never runtime
to migration/master. CREATE DATABASE is not transactional: a failed run can leave safely scoped
roles/database behind; inspect the sanitised failure and rerun after correcting its cause.

The migration login owns the database/public schema and all migration-created objects. Bootstrap
grants runtime CONNECT, schema USAGE, table SELECT/INSERT/UPDATE/DELETE, and sequence USAGE/SELECT;
matching owner default privileges cover future migrations. PUBLIC schema CREATE and database
TEMPORARY are revoked. Runtime cannot create/alter tables, create temporary tables, or SET ROLE
to the owner. Functions/triggers remain migration-owned; ordinary invoker functions use runtime
DML grants. Run `manage.py migrate --noinput` once using the migration credential profile, then
`manage.py check_database` and the web process with the runtime profile. Never deliver migration
or bootstrap credentials to web containers. Local Compose intentionally retains its existing
single local owner/developer role and requires no AWS configuration.

**Trainer login.** `db_bootstrap` creates only the runtime and migration logins, so the read-only login for the standalone trainer and refresh verifier is created by two SQL files in `src/infrastructure/sql/`, run once from the instance with `psql` and `verify-full` TLS: `trainer_role_create.sql` as the RDS master (login only, every privilege flag false) and `trainer_role_grant.sql` as the migration owner. The grant is narrow on purpose: `SELECT` on the nine tables `analytics/segment_customers.py` and `verify_refresh.py` read, plus `id`, `is_staff` and `is_superuser` of `auth_user`, and no default privileges, so `django_session` (whose keys would allow session takeover), password hashes and later tables stay unreadable. Tested on a disposable PostgreSQL 17 (the real segment query runs; `INSERT`, `django_session` and `auth_user.password` are refused; see [the stage 2 review](reviews/aws-terraform.md)) and then run on the real RDS instance on 1 October 2026 through `jobs.sh trainer-sql` (runbook, variant A acceptance).

## Secrets Manager startup and ALB boundary

The Terraform for these secrets is applied as empty containers (`inf2006-grp21/web`, `/migration`, `/trainer`, `/bootstrap`; values are set with the CLI so they never enter state) and the launch template and user data that deliver them are applied in `ec2/` (variant A; the Fargate task definition for variant B is not written). The following is the
application handoff contract, not a claim of compatible infrastructure or deployed verification.
`AWS_SECRET_ID` and `AWS_REGION` are required nonsecret configuration outside `DJANGO_ENV=local`.
One `config/secrets.py` loader retrieves `SecretString` once per process/startup through the SDK's
role credential providers, uses bounded timeouts/retries and normal HTTPS certificate verification,
and ignores configured custom service endpoints. Static environment/shared-file AWS credentials
are refused. SDK/config/payload failures are sanitised and stop startup, with no plaintext fallback.
Local mode reads its existing environment and neither imports nor calls the AWS SDK.

Use distinct secrets and IAM access for these caller-required JSON schemas (all values strings,
nonempty and non-placeholder; extra fields are refused). Identifiers below are configuration keys,
not provisioned secret names or ARNs:

| Caller | Required JSON keys | Optional JSON key |
|---|---|---|
| Django web and management commands | `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY` | `POSTGRES_PORT` |
| Standalone batch trainer and refresh verifier | `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `POSTGRES_PORT` |
| One-off bootstrap only | DB keys above plus `MIGRATION_USER`, `MIGRATION_PASSWORD`, `BOOTSTRAP_USER`, `BOOTSTRAP_PASSWORD` | `POSTGRES_PORT` |

The web secret names the unprivileged runtime login; the one-off migration secret has the same
app schema but names the migration owner. The web instance role must have GetSecretValue only
on its runtime secret, never migration/bootstrap secrets. The migration and bootstrap runners
receive separate permitted roles/secret selection; the bootstrap aggregate secret is confined
to the one-off privileged runner. Standalone training/verification use a separate DB-only secret
and read-only DB identity; no Django signing key is delivered to that process. All app instances
receive the same signing key. Owner credentials must never reach a web container. The schema
cannot prove a database identity's privileges: bootstrap/integration checks and IAM boundaries
are required. Rotation takes effect after coordinated process replacement, not on each request.

A caller's retrieved secret replaces ambient values for its schema. Production `verify_refresh.py
--database-url` is refused so URL credentials cannot bypass secret selection; explicit local DSNs
remain supported. CA path, allowed hosts, trusted CSRF origins, proxy switch, release identity and
probe Host remain nonsecret deployment configuration. `APP_RELEASE_ID` is a required bounded
nonsecret identifier in production (for example the deployed commit or image identity). The WSGI
worker emits one startup JSON event with release/environment through existing stdout logging.
It does not log secret IDs, values or customer data.

Allow inbound TCP 8000 to app instances only from the ALB security group, not the internet or
other workload groups. Set `DJANGO_TRUST_PROXY=true` only at that boundary where ALB supplies
`X-Forwarded-Proto`; the app does not trust `X-Forwarded-Host`. Configure explicit application
hostnames in `DJANGO_ALLOWED_HOSTS` and matching HTTPS `DJANGO_CSRF_TRUSTED_ORIGINS`.
Set `DJANGO_HEALTH_PROBE_HOST` per instance to its exact private IPv4 address followed by `:8000`.
The optional early middleware accepts that Host only for GET/HEAD `/health/`, returning the same
no-store, database-independent liveness response before HTTPS redirection. Existing request logging
wraps Host validation so rejected normal requests retain their request ID in the response and security event. Wrong IP/port, other
methods and every normal route retain allowed-host validation. The configured IP is not added
to general allowed hosts; arbitrary IP ranges/wildcards and forwarded Host are not accepted.
The probe exception is not authentication; its safety also depends on the ALB-only network rule.
Keep `check_database` as an operator readiness step so an RDS outage does not recycle all app
instances. Actual ALB headers, TLS trust, role access and denied access still require AWS evidence.

Primary references: [ALB probe Host](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html),
[ALB forwarded protocol](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html),
[GetSecretValue permissions](https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html),
[SDK role credentials](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).
Grant `kms:Decrypt` only when needed for the selected customer-managed key; provision/access
failures block deployment rather than permitting plaintext launch configuration.

## Image and infrastructure-owner handoff

Build from `src/` with its Dockerfile. The `.dockerignore` excludes the dedicated infrastructure
directory (and common `infra`/`terraform` alternatives), nested state/plans/variable values,
local environment/credential files and private keys. Only the vendored public RDS PEM is allowed.
Git ignores sensitive state/plans/tfvars while preserving safe example variables and provider
lockfiles. Keep all infrastructure in its dedicated directory; an arbitrary filename is not a
secret classification system. Never bake retrieved secrets into an image, build argument or layer.

| Owner input / step | Required handoff |
|---|---|
| Image and launch | Pin the published ECR digest after authorised publication; set the same nonsecret release ID on every instance. Run the image's nonroot Gunicorn CMD on port 8000; no per-instance migrations. A local Docker image ID is not an ECR deployment result. |
| Network / HTTPS | ALB-only instance ingress, exact instance probe Host, explicit public application hosts/CSRF origins, trusted ALB protocol boundary and permitted certificate/hostname/client trust. Verify real headers and probes. |
| Database / credentials | Private RDS endpoint, read-only CA delivery, role-separated secrets/IAM and coordinated bootstrap then migration then runtime readiness according to the contracts above. Verify both required access and forbidden access. |
| Operations | Collect existing stdout JSON logs, retain release identity and readiness results, and verify replacement instances share signing/session state. Retain measured thresholds and teardown ownership. |

Use the existing [security log-field contract](SECURITY.md): request ID, status, duration and
sanitised exception class support request/error correlation; startup events add release/environment.
The infrastructure owner must wire and calibrate failure/alert conditions for secret/config startup
failure, failed migrations/readiness, unhealthy targets or process exits, elevated 5xx/database 503
rates or latency, and failed/stale batch runs. Batch freshness is judged against the explicitly
selected completed run and agreed operational age, not an assumed recurring scheduler. Thresholds,
CloudWatch/SNS wiring and alert delivery remain unverified infrastructure work. Never use customer
IDs as metric dimensions or emit secret values/personal payloads; no additional telemetry is added here.

Reproducible local image/sentinel/TLS procedures are in [tests/README.md](../tests/README.md#local-runtime-image-and-tls-verification)
and [the executable helper](../tests/verify_runtime_image.py). Exact locally built image identities,
executed results and remaining integration limitations are recorded in the
[runtime review](reviews/runtime-aws-security.md), not inferred from a successful build.
The tests do not establish AWS permissions, region/budget, real Secrets Manager delivery,
certificate availability, security groups, ALB/RDS behavior or ECR publication.


## Joint integration checklist after Phase 6

The [Phase 6 release record](reviews/ml-local-release-readiness.md) owns the exact locally tested source/image and limits. Local completion does not clear the following joint gates. The infrastructure owner implements the cloud configuration; the application owner supplies the reviewed image/contracts and checks behavior together with that owner. This checklist does not authorise an apply or deployment.

**Status of the checklist on variant A (3 October 2026; evidence in the [runbook](../evidence/aws-build-runbook.md)).** Items 1 to 3 are done: permissions and region recorded, the image published and pinned by digest, the role-separated secrets wired, `db_bootstrap`, `migrate` and the trainer SQL run over SSM, and the denied actions checked (runtime login cannot `CREATE TABLE`, trainer login cannot `INSERT` or read `auth_user.password`). Item 4 is partly done: HTTPS, the health probe and `smoke.sh` (8 of 8) pass; session and cart continuity across two instances is not yet shown. Item 5 is partly done: the dataset import from S3 and the analytics refresh ran; the segmentation train and load on AWS and the failure and retry cases are not recorded. Item 6 is partly done: three alarms, two saved log queries and the WAF (count mode) are applied, but no alarm has fired, the WAF block-mode test has not run and there is no scaling or recovery evidence. Item 7 continues through the runbook. Update, 9 October 2026: on 8 October the alarms fired (a forced `target-5xx` alarm reached the email subscription; the scaling alarm fired under load), scale-out and replacement were measured, and the deployed security cases SEC-09, SEC-10, SEC-11 and SEC-18 passed on variant A ([evidence/README.md](../evidence/README.md)); the WAF block-mode test (SEC-17) was run on variant B only. Variant B was run the same way on 9 October 2026 (SEC-09, SEC-10, SEC-11, SEC-18 and the WAF block test SEC-17 pass; scale-out, replacement and saturation measured).

1. Confirm actual lab region, account, budget, service/role permissions and the permitted certificate/hostname/client-trust route. Review Terraform plan and costs; preserve shared-state coordination and teardown ownership.
2. After separate publication authorisation, publish the tested application image through the agreed ECR route, record the registry manifest digest, and pin that digest plus the same release ID on every instance. A local Docker image ID is not this evidence.
3. Wire the role-separated Secrets Manager schemas above, required KMS access if applicable and private RDS networking. Coordinate bootstrap, one migration and runtime readiness in that order. Verify runtime access and denied owner/bootstrap actions, trainer read-only access, real RDS hostname/CA validation and refused insecure configuration.
4. Verify HTTPS and exact ALB health Host handling on port 8000, ALB-only application ingress, explicit hosts/CSRF origins, trusted forwarded protocol and private RDS. Prove sessions/carts/signing continuity across two instances without sticky sessions.
5. Store the accepted checksummed input and authorised batch exports in private S3. Verify permitted reads and anonymous denial; reproduce import, explicit completed analytics run, separate training/export and exact-file import with role separation. Check own-run loaded/unavailable display and failure/retry preservation. No Scheduler or Lambda is selected; agree operational freshness thresholds without claiming persisted orchestration state.
6. Wire sanitised release/request logs, CloudWatch thresholds and SNS delivery, WAF's scoped login rule and CloudTrail. Exercise both allowed and denied requests and an actual failure/alert path. Calibrate fixed-capacity load before ASG comparisons; retain scaling, instance-loss, database-outage and recovery evidence.
7. Record exact source, ECR digest, configuration, data checksums, command results, costs and limitations in the existing evidence records. Keep hosted CI, submission artefact completion and deployed behavior distinct. Teardown only the jointly owned test resources after retaining redacted evidence.
