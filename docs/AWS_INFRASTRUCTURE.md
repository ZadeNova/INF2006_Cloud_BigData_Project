# AWS infrastructure contract

Status: planned, not deployed. Read [scope](../PROJECT_SCOPE_INF2006.md) for budget and risks. Verify actual lab permissions and regional prices before deployment.

## Baseline

- Terraform under src/; concrete subdirectory/provider versions established during scaffolding.
- HTTPS ALB across two permitted Availability Zones, health-checked EC2 targets in an ASG.
- Same container image, signing configuration and database sessions on every instance; stickiness disabled.
- Private Single-AZ RDS PostgreSQL, inbound only from application security group. State its availability limitation.
- Private S3 for checked inputs/optional exports; block public access and restrict object permissions. Retain local input mode.
- CloudWatch sanitised logs/metrics with short retention.
- IAM instance roles and Secrets Manager where permitted; no baked-in access keys.

Initial/minimum ASG capacity one, default test maximum two. Have two healthy targets before failure demonstration. Additional capacity requires quota/cost checks. Budget baseline: EC2 public subnets with application ingress restricted to ALB to avoid mandatory NAT cost; RDS private. Restrict management access separately through permitted facilities.

## Early gates and deployment

Verify region, service/role permissions, instance types, quotas and actual balance. Credits are separate, not a pooled USD 200. Establish hostname/certificate validation for HTTPS; the generated ALB hostname is not a team-owned certificate arrangement.

Define lightweight app health checks and dependency policy. Avoid replacing all app instances merely because shared RDS is down. Record final thresholds/timeouts/warmup against measured startup behaviour.

Deploy repeatable images and run migrations once through a coordinated step, not racing on every instance boot. Test compatibility/recovery before rollout. Terraform state can contain secrets and stays outside source/submission.

Use target tracking with a measured request-count or CPU target. Fix numeric targets before final comparison. Record desired/in-service/healthy capacity, latency percentiles, throughput, errors and scaling delay. Allow startup and health checks. Scale-in drains requests; abrupt crashes can still fail them.

## Conditional cache

ElastiCache is not required yet. If selected, record engine/version, lab access, security settings and regional cost. Use shared cache-aside for catalogue/sales summaries, bounded expiry, after-commit invalidation and period/run-aware keys. No authoritative stock, sessions or carts in cache.

Explicitly handle cache read/write connection failures and timeouts; fall back to RDS and temporarily bypass repeated failures. Authorise privileged requests before cache access. Compare disabled, warmed and unavailable cache at fixed app capacity, including fallback database pressure. Multi-AZ replicas require a separate cost decision.

## Operations and teardown

Monitor latency/errors, target health, DB pressure and analytics freshness. Capture dated outputs and interpretation for an operational query/alert. Start with a USD 30 planning cap against the integration account's initial USD 40, reserve USD 10, and recalculate actual remaining funds.

Develop locally and deploy for bounded tests. Inventory charges: compute, ALB, RDS, IPv4, storage/snapshots, S3 versions, logs and secrets. Capture evidence before teardown. Stopping EC2 does not stop all charges. Verify lab-end behaviour and delete only intended test resources. Do not claim uninterrupted availability.
