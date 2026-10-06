# Plan: variant B (`fargate/`), ECS on Fargate

**Status (6 October 2026):** plan agreed. **Step 2 written, not applied:** `modules/web-entry`, `ec2/` refactored onto it, `fargate/`, ADR-014 to 017 (offline `terraform validate` passes for all three folders). Scripts, README quick start and every apply are still to do. Governed by [aws-ecs-comparison.md](aws-ecs-comparison.md) (the comparison, the fairness rules) and the design table in [AWS_INFRASTRUCTURE.md](../AWS_INFRASTRUCTURE.md#variant-b-ecs-on-fargate-designed-not-built); where this file differs from them it is newer and they get synced after the build. Measurement needs come from [load-harness.md](load-harness.md) section 10 item 3.

## 1. Goal

A second stack, `src/infrastructure/fargate/`, that serves the same shop from the same image digest and the same RDS as `ec2/`, at `https://shop-fargate.fourtytwofactors.me`, so the two can be load-tested one at a time. It must be applied and destroyed on its own, with `base/` never reading it (ADR-001).

## 2. Lab facts

- The user reports that the lab does not block Fargate, and that Application Auto Scaling should be fine. Neither was recorded from output, so the runbook will say "reported by the user". The first apply is the real test.
- Not known and learned at apply: the Fargate vCPU quota (how far B can scale), and whether `LabRole` works as both task role and execution role.

## 3. Structure: one shared module (ADR-014)

```
src/infrastructure/
  base/                 shared, stays up: VPC, RDS, DNS, certificate, ECR, S3, secrets, SNS
  modules/web-entry/    the front door both variants use (below)
  ec2/                  module call + launch template + Auto Scaling group + scaling
  fargate/              module call + ECS cluster, task definition, service + scaling
  loadgen/              the load generator, test sessions only
  scripts/
```

**`modules/web-entry/` owns:** `sg-alb` and `sg-app` with their rules and the stack's rule on `sg-db`; the ALB, HTTPS listener and 80 redirect; the target group and `/health/` check (10 s, 2 healthy, 3 unhealthy, 30 s deregistration, no stickiness); the WAF rule in `count` mode; the three alarms and two saved log queries; the stack's log group; the alias record; and one **output map of application environment variables** that both variants use. Inputs: name prefix, stack tag, hostname, target type (`instance` or `ip`), and the `base/` values it needs. This supersedes rule 4 of [aws-ecs-comparison.md](aws-ecs-comparison.md) section 8 ("no child modules"); that file is synced after the build.

**`ec2/` keeps:** launch template, Auto Scaling group, scaling policy, `user_data.sh.tftpl` (now reading the environment map), the ADR-013 settings.

**`fargate/` adds:**

| Piece | Choice |
|---|---|
| Task | 2 vCPU / 4 GB, x86_64, image by digest, `LabRole` as task and execution role, `awslogs` to the module's log group. Environment from the module's map plus `AWS_SECRET_ID` |
| Probe host | `command` override that reads the task IP from the ECS metadata endpoint, exports `DJANGO_HEALTH_PROBE_HOST=<ip>:8000` and runs the image's gunicorn command unchanged (`--workers 2`). The task fails if the lookup fails |
| Service | Desired 1; rolling deploy at 100% minimum healthy and 200% maximum; circuit breaker with rollback; health-check grace period; public IP on the task |
| Scaling | Application Auto Scaling on `ALBRequestCountPerTarget`, target `scale_target_requests` (300), min 1, max 2; scale-out and scale-in cooldowns set explicitly and recorded beside the ASG warm-up |
| Pinning | Same three variables as `ec2/`, as the scaling target's min and max; an apply resets the count, as on `ec2/` |
| Left out | ECS Exec and Container Insights (cost and permissions, no value for the comparison) |
| Outputs | `hostname`, `alb_dns_name`, `target_group_arn`, `image_digest`, `web_acl_name`, `cluster_name`, `service_name`, `alb_arn_suffix`, `target_group_arn_suffix`, `log_group_name`, `security_group_ids` (the same names on `ec2/`, where they exist) |

## 4. Scripts: a small front door

One verb per intention, all documented at the top of `src/infrastructure/README.md` in a five-line quick start; the long build-from-nothing section moves below it. The helpers stay internal.

| You type | It does |
|---|---|
| `scripts/status.sh` | Checks tools and credentials, lists which stacks are up and what is missing, and prints the next command. The first thing a new person runs |
| `scripts/up.sh base` | First-time setup: creates the S3 bucket with the CLI (the lab denies it to Terraform), writes `terraform.tfvars` from the example, applies `base/`, prints the name servers and waits for delegation |
| `scripts/up.sh ec2` or `fargate` | Pushes the image if none is selected, then plan, confirm, apply, database jobs still needed (`ec2`) or `jobs fargate check`, and the smoke test |
| `scripts/up.sh loadgen` | Applies the generator stack |
| `scripts/down.sh ec2\|fargate\|loadgen` | Destroys the stack and lists leftovers |
| `scripts/smoke.sh ec2\|fargate` | Eight checks, no credentials |

Helpers called by those: `tf.sh`, `secrets.sh`, `jobs.sh`, `push-image.sh`. `migrate-state.sh` (done) and `probe-lab-comparison.sh` (stale) are deleted; git history keeps them. Terraform state stays local, one folder per stack: each person's lab is a separate account, so each laptop owns that account's state.

### `jobs.sh fargate`

On EC2 each job runs inside the instance through SSM. On Fargate each job is a one-off task started with `aws ecs run-task` (command override and `AWS_SECRET_ID` override), then the script waits for it to stop, prints its logs and fails on a non-zero exit code.

| Job | On Fargate |
|---|---|
| `check`, `migrate`, `refresh`, `bootstrap` | Built: they need only the app image and a secret |
| `trainer-sql`, `import`, `operator` | **Not offered:** they need `psql`, the AWS CLI or a data folder that the frozen image does not have. Run them on variant A |
| `restart` | Not applicable (a service restarts with `update-service --force-new-deployment`) |

**Limit to state in the report:** a brand-new database is seeded through variant A once. Reproduction order: `base`, then `ec2`, then `fargate`.

## 5. Decisions to record (ADRs, drafted by the writing session, numbering provisional)

| ADR | Decision |
|---|---|
| 014 | The shared `web-entry` module (written) |
| 015 | The Fargate task and service: size, task and execution role, public IP, deployment settings, no ECS Exec or Container Insights |
| 016 | The health-probe host override, including the duplicated CMD and how drift is caught |
| 017 | Fairness pairings (scaling cooldowns against ASG warm-up, matched numbers), the reduced `jobs.sh fargate` scope, and the script front door |

## 6. Order of work

Each step stops for the user's review before anything is committed; the user runs every plan and apply.

1. This plan and ADR-014 approved.
2. `modules/web-entry`, then `ec2/` refactored onto it, validated offline; ADR-015 to 017 with `fargate/`.
3. Script front door (`status.sh`, `up.sh base|loadgen|fargate`, `down.sh fargate`, `jobs.sh fargate`) and the README quick start, tested offline as far as possible (the fake-`aws` method used before).
4. User: `up.sh ec2` (first apply of the module and the ADR-013 settings; smoke 8 of 8), then `up.sh fargate`.
5. Runbook entry, README update and the cost recorded; then the independent review gate for the module, `ec2/`, `fargate/` and the scripts (a fresh session).

## 7. Acceptance

For each variant: healthy behind its ALB over HTTPS at its own hostname; no port 22; the image digest equals the one the other variant runs; logs reach CloudWatch; `smoke.sh` 8 of 8. For Fargate also: `jobs.sh fargate check` passes, a stopped task is replaced by the service, scaling is registered. For the module: the two plans show the same module resources.

## 8. Not decided here

- Fargate cost per hour (about USD 0.099 for 2 vCPU / 4 GB, from memory, unverified; the runbook records the measured cost).
- Whether a difference between A and B comes from ECS or Fargate: unmeasured (ECS on EC2 was dropped for time).
- The domain is the one input that is not portable: another account needs its own domain in `domain_name` (the user has theirs).
