# Architecture decision records

One line per record. The final architecture is variant B, ECS on Fargate ([ADR-018](ADR-018-final-architecture-ecs-fargate.md)); variant A (EC2) is the evaluated alternative.

| ADR | Title | Status |
|---|---|---|
| [001](ADR-001-split-terraform-into-base-and-stacks.md) | Split Terraform into `base/`, `ec2/` and `fargate/`, one local state each | Partly superseded by ADR-014 (the "no child modules" rule); the rest stands |
| [002](ADR-002-migrate-stage-1-state-with-state-mv.md) | Migrate stage 1 into `base/` with `terraform state mv`, recreate the rest, gate on a clean plan | Drafted 1 Oct; implements ADR-001 |
| [003](ADR-003-route53-zone-in-base.md) | Route 53 hosted zone in `base/`, delegated from Namecheap, time-boxed | Drafted 1 Oct |
| [004](ADR-004-one-rds-instance-db-t4g-small.md) | One RDS PostgreSQL 17 instance, `db.t4g.small`, shared by both variants | Drafted 1 Oct |
| [005](ADR-005-small-scripts-for-plan-image-and-secrets.md) | Three small scripts for plan/apply, the image, and the secrets | Drafted 1 Oct |
| [006](ADR-006-one-acm-certificate-two-hostnames.md) | One ACM certificate for the two shop hostnames, validated in Terraform | Drafted 1 Oct |
| [007](ADR-007-ec2-compute-c5-large-public-subnets.md) | Variant A compute: `c5.large`, one instance, public subnets, no NAT | Drafted 1 Oct |
| [008](ADR-008-alb-and-health-check-settings.md) | ALB, TLS and health-check settings | Drafted 1 Oct |
| [009](ADR-009-database-jobs-by-ssm-run-command.md) | Database and data jobs run by `jobs.sh` through SSM Run Command | Drafted 1 Oct; variant A only |
| [010](ADR-010-operator-secret-and-one-command-deploy.md) | Operator login in its own secret, and the `up`, `down` and `smoke` scripts | Drafted 1 Oct |
| [011](ADR-011-target-tracking-on-request-count.md) | Scale on requests per instance (target tracking), 1 to 2 instances | Drafted 1 Oct |
| [012](ADR-012-alarms-and-login-rate-limit.md) | Three alarms, saved log queries, and a WAF rate limit on `POST /login/` | Drafted 1 Oct |
| [013](ADR-013-load-generator-stack-and-measurement-settings.md) | A separate load-generator stack, one-minute monitoring and capacity pinning | Drafted 6 Oct |
| [014](ADR-014-shared-web-entry-module.md) | One shared module for the web front door, used by both variants | Drafted 6 Oct; supersedes the "no child modules" part of ADR-001 |
| [015](ADR-015-fargate-task-and-service.md) | The Fargate task and service | Drafted 6 Oct |
| [016](ADR-016-fargate-health-probe-host-override.md) | Start the Fargate task with a command that sets the health-probe host | Drafted 6 Oct |
| [017](ADR-017-fargate-fairness-pairings-and-jobs-scope.md) | Matched settings between the variants, the reduced Fargate jobs, and the script front door | Drafted 6 Oct; section 2 amended by ADR-019 |
| [018](ADR-018-final-architecture-ecs-fargate.md) | The final architecture is variant B (ECS on Fargate); variant A stays as the evaluated alternative | Decided 9 Oct |
| [019](ADR-019-variant-b-sets-up-its-own-database.md) | Variant B sets up its own database | Decided 9 Oct; amends ADR-017 section 2 |
