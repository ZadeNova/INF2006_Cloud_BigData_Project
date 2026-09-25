# AWS infrastructure contract

Status: planned, not deployed. Read [scope](../PROJECT_SCOPE_INF2006.md) for budget and risks. Verify actual lab permissions and regional prices before deployment. Lab capability probe run 25 September 2026 (`us-east-1`, AWS Academy Learner Lab): every service in the baseline is reachable; only `LabRole` and `LabInstanceProfile` are available for IAM; the vCPU quota lookup is denied.

## Baseline

- Terraform under src/; concrete subdirectory/provider versions established during scaffolding.
- HTTPS ALB across two permitted Availability Zones, health-checked EC2 targets in an ASG.
- Same container image, signing configuration and database sessions on every instance; stickiness disabled.
- Private Single-AZ RDS PostgreSQL, inbound only from application security group. State its availability limitation.
- Private S3 for checked inputs/optional exports; block public access and restrict object permissions. Retain local input mode.
- CloudWatch sanitised logs/metrics with short retention.
- IAM runtime roles and Secrets Manager for database credentials/shared Django signing key; unavailable storage or retrieval blocks deployment. No baked-in access keys or plaintext user-data/launch-template secrets.
- ECR is the selected image route. SNS, CloudTrail, regional WAF, EventBridge Scheduler and Lambda are included; verify lab permissions, roles, costs and actual behaviour before claiming readiness. Systems Manager is not selected.
- Offline ML training exists; versioned saved-model inference and scheduled Lambda integration remain unimplemented. Preserve local training/loading and keep ML libraries outside the web image.

Initial/minimum ASG capacity one, default test maximum two. Have two healthy targets before failure demonstration. Additional capacity requires quota/cost checks. Budget baseline: EC2 public subnets with application ingress restricted to ALB to avoid mandatory NAT cost; RDS private. Restrict management access separately through permitted facilities.

## Early gates and deployment

Verify region, service/role permissions, instance types, quotas and actual balance. Credits are separate, not a pooled USD 200. Establish hostname/certificate validation for HTTPS; the generated ALB hostname is not a team-owned certificate arrangement.

Foundation supplies GET/HEAD /health/ as database-independent process liveness (200, no-store), with allowed-host validation and internal HTTPS-redirect exemption. The separate check_database management command verifies PostgreSQL and applied migrations for operator/deployment readiness. Never use database readiness to replace all app instances during shared RDS failure. Local Compose uses a 10s probe interval, 2s request timeout, 3s process timeout, three retries and 10s start period; local startup was verified, but these are not calibrated AWS settings. The later deployment must resolve ALB probe Host/allowed-host handling (default probes may use target IPs), and measure its own thresholds/timeouts/warmup. No AWS deployment is claimed.

Deploy repeatable images and run migrations once through a coordinated step, not racing on every instance boot. Test compatibility/recovery before rollout. Terraform state can contain secrets and stays outside source/submission.

Use target tracking with ALBRequestCountPerTarget as the scoped baseline. CPU target tracking is an alternative requiring a documented scope decision. Fix numeric targets before final comparison. Record desired/in-service/healthy capacity, latency percentiles, throughput, errors and scaling delay. Allow startup and health checks. Scale-in drains requests; abrupt crashes can still fail them.

## Conditional cache

ElastiCache is not required yet. If selected, record engine/version, lab access, security settings and regional cost. Use shared cache-aside for catalogue/sales summaries, bounded expiry, after-commit invalidation and period/run-aware keys. No authoritative stock, sessions or carts in cache.

Explicitly handle cache read/write connection failures and timeouts; fall back to RDS and temporarily bypass repeated failures. Authorise privileged requests before cache access. Compare disabled, warmed and unavailable cache at fixed app capacity, including fallback database pressure. Multi-AZ replicas require a separate cost decision.

## Operations and teardown

Monitor latency/errors, target health, DB pressure and analytics freshness. Capture dated outputs and interpretation for an operational query/alert. Start with a USD 30 planning cap against the integration account's initial USD 40, reserve USD 10, and recalculate actual remaining funds.

Develop locally and deploy for bounded tests. Inventory charges: compute, ALB, RDS, IPv4, storage/snapshots, S3 versions, logs, secrets, ECR, SNS, CloudTrail, WAF, Scheduler and Lambda. Capture evidence before teardown. Stopping EC2 does not stop all charges. Verify lab-end behaviour and delete only intended test resources. Do not claim uninterrupted availability.

## Setup order and verification

Use dependency order and small reviewable changes, not an unexamined full deployment. **Deployment method (revised 25 September 2026): Terraform first.** Terraform creates and owns every team-managed resource (named `inf2006-<component>`, tagged `ManagedBy=terraform`). The console is for learning and inspection only: reading settings, logs, metrics and CloudTrail event history, plus the few steps Terraform cannot do (the ACM validation record at the external domain registrar, confirming the SNS email subscription, reading the lab balance). Anything created by hand is imported into Terraform or deleted, so there is no drift. This replaces the earlier "console first, then reproduce in Terraform" decision. The user is learning Terraform while building it, so the work goes phase by phase with a guide per phase, and it starts only when the user says so. Pre-existing lab roles (`LabRole`, `LabInstanceProfile`) are referenced as external dependencies, never recreated. Record authorised emergency/manual changes and reconcile configuration afterwards. Plan and decisions: [aws-terraform.md](plans/aws-terraform.md).

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

With two infrastructure developers, choose one state owner/writer per environment. Prefer appropriately secured shared state with locking when lab capabilities permit. If using local state, agree custody and secure backup/handover; never create independent states managing the same resources. State/plan files may contain secrets and must not be committed or submitted. After any approved change, preserve a sanitised record, verify expected behaviour and coordinate teardown with the other developer.
