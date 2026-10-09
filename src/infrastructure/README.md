# AWS infrastructure: how to run it

Terraform and scripts that deploy 42Factors to AWS (Learner Lab, `us-east-1`) in two variants that are compared: **A, EC2 with an Auto Scaling group**, and **B, containers on ECS Fargate**. Decisions are in [docs/decisions/](../../docs/decisions/) (ADR-001 to ADR-017), the plan in [aws-ecs-comparison.md](../../docs/plans/aws-ecs-comparison.md) and [fargate-variant.md](../../docs/plans/fargate-variant.md), and what was actually applied, with dates and results, in [evidence/aws-build-runbook.md](../../evidence/aws-build-runbook.md).

**Status (9 October 2026).** `base/` is applied and stays up. Variant A was applied and verified on 1 October: `https://shop-ec2.fourtytwofactors.me` served the shop, with `smoke.sh` passing 8 of 8. Since then the front door shared by both variants moved into a module (`modules/web-entry`), the Fargate stack (`fargate/`) and the load-generator stack (`loadgen/`) were written, and the scripts were extended. **All of that passed `terraform validate`.** Variant A and the load-generator stack were applied and used on 8 October (evidence in [evidence/README.md](../../evidence/README.md), the apply record in [aws-build-runbook.md](../../evidence/aws-build-runbook.md)); variant B (`fargate/`) was applied, measured and torn down on 9 October (the final architecture, [ADR-018](../../docs/decisions/ADR-018-final-architecture-ecs-fargate.md)). The earlier `up.sh` stop at `db_bootstrap` on an already-bootstrapped database is fixed in code (ADR-019, not re-run in AWS). Between work sessions the stacks are torn down to save money.

## Quick start

Run everything from the **repository root**, on the laptop that holds the Terraform state, in a terminal with lab credentials (see [credentials](#tools-and-credentials)).

| I want to | Run |
|---|---|
| See what is running, and what to do next | `src/infrastructure/scripts/status.sh` |
| Set up from nothing (first time only) | `src/infrastructure/scripts/up.sh base` |
| Start variant A (EC2) | `src/infrastructure/scripts/up.sh ec2` |
| Start variant B (Fargate) | `src/infrastructure/scripts/up.sh fargate` |
| Check that a running shop works | `src/infrastructure/scripts/smoke.sh ec2` (or `fargate`) |
| Stop a stack (always do this when you finish) | `src/infrastructure/scripts/down.sh ec2` (or `fargate`) |
| Start or stop the load-test machine | `src/infrastructure/scripts/up.sh loadgen` / `down.sh loadgen` |

A normal session:

```bash
labcreds                                     # paste the lab credentials (below)
src/infrastructure/scripts/status.sh         # what is up, what is missing
src/infrastructure/scripts/up.sh ec2         # shows the plan, you type yes, then it builds and checks everything
# ... work, test ...
src/infrastructure/scripts/down.sh ec2       # shows what it will destroy, you type yes
```

Every script says what it is doing, shows the Terraform plan before changing anything, stops at the first error, and is safe to run again.

## Contents

1. [Layout](#layout)
2. [Rules](#rules)
3. [Tools and credentials](#tools-and-credentials)
4. [Start a variant](#start-a-variant)
5. [Stop a stack](#stop-a-stack)
6. [The load generator](#the-load-generator)
7. [If you are not on the apply laptop](#if-you-are-not-on-the-apply-laptop)
8. [Build everything from nothing in a new account](#build-everything-from-nothing-in-a-new-account)
9. [Command reference](#command-reference)
10. [Cost](#cost)
11. [Troubleshooting](#troubleshooting)
12. [Final teardown](#final-teardown)
13. [What comes next](#what-comes-next)

## Layout

```
src/infrastructure/
  base/                 shared, stays up
  modules/web-entry/    the front door both variants use
  ec2/                  variant A
  fargate/              variant B
  loadgen/              the load-test machine
  scripts/              the commands above
  sql/                  the trainer login's two SQL files (run by jobs.sh trainer-sql)
```

| Folder | What it owns | State |
|---|---|---|
| `base/` | VPC and subnets, `sg-db`, Route 53 zone, ACM certificate, RDS PostgreSQL 17, ECR, S3 bucket settings, the five secrets, SNS alarm topic. Stays up between experiments | `base/terraform.tfstate` |
| `modules/web-entry/` | Everything in front of the app, identical for both variants by construction ([ADR-014](../../docs/decisions/ADR-014-shared-web-entry-module.md)): the `sg-alb` and `sg-app` security groups, ALB with HTTPS and the 80 redirect, target group and `/health/` check, WAF rate rule, alarms and saved log queries, log group, DNS alias, and the app's non-secret environment. Not applied by itself: each stack calls it ([README](modules/web-entry/README.md)) | none |
| `ec2/` | Variant A: the module plus the launch template, Auto Scaling group (1 to 2 instances) and scaling policy. Hostname `shop-ec2.fourtytwofactors.me` | `ec2/terraform.tfstate` |
| `fargate/` | Variant B: the module plus an ECS cluster, task definition (2 vCPU / 4 GB), service and Application Auto Scaling (1 to 2 tasks). Hostname `shop-fargate.fourtytwofactors.me` | `fargate/terraform.tfstate` |
| `loadgen/` | The load generator for the benchmarks ([ADR-013](../../docs/decisions/ADR-013-load-generator-stack-and-measurement-settings.md)): one `c5.large`, no inbound rules, Session Manager only. Up only during test sessions | `loadgen/terraform.tfstate` |

The stacks read `base/` through `terraform_remote_state` (`../base/terraform.tfstate`); `base/` never reads a stack, so a stack can be destroyed without touching the database. Both variants use the **same** database and the **same** image digest, so they can be load-tested one at a time.

**There is no Terraform directly in `src/infrastructure/`.** The single-folder version from stages 1 and 2 was split into `base/` and `ec2/` on 1 October 2026 (one-time migration script, since deleted; it stays in git history) and its files removed afterwards.

## Rules

1. **One apply device.** The owner's Fedora laptop holds the state files and is the only machine that runs `plan`, `apply` or `destroy`. Other devices write and review code through git. Never create a second state for the same resources.
2. **Apply only committed code.** `scripts/tf.sh` (which every `up.sh` uses) refuses a dirty tree and refuses a plan made from another commit.
3. **Never commit** `*.tfstate*`, `*.tfvars` (except `*.tfvars.example`), `*.tfplan` or secret values. They are git-ignored; keep it that way.
4. **Back up state after every apply.** `tf.sh apply` writes `terraform.tfstate.<date>.<commit>.bak`; copy it off the laptop (USB or a private drive, never git).
5. **Read every plan before applying it.** Anything replaced or destroyed that you did not expect: stop.
6. **Tear the stack down when you stop for the day** ([cost](#cost)).

## Tools and credentials

Installed on the apply laptop (versions used); `scripts/status.sh` checks them:

| Tool | Version | Used for |
|---|---|---|
| Terraform | 1.16.4 (needs 1.10 or newer) | every folder |
| AWS CLI v2 | 2.37 | every script |
| Session Manager plugin | 1.2 | `aws ssm start-session` (manual debugging, the load generator) |
| `jq`, `openssl`, `curl`, `git`, `python3` | any recent | scripts |
| Docker | any recent | building the app image (`push-image.sh`, run by `up.sh` when no image is chosen) |

**Lab credentials** expire after about 4 hours and every script checks them first. In the Learner Lab: Start Lab, then AWS Details, then Show next to AWS CLI. Add this function to `~/.bashrc` once, then run `labcreds` in each new terminal and paste the block, followed by an empty line:

```bash
labcreds() {
  echo "Paste the AWS Details 'aws_access_key_id=...' block, then press Enter on an empty line:"
  local line
  while IFS= read -r line && [ -n "$line" ]; do
    case "$line" in
      aws_access_key_id=*)     export AWS_ACCESS_KEY_ID="${line#aws_access_key_id=}" ;;
      aws_secret_access_key=*) export AWS_SECRET_ACCESS_KEY="${line#aws_secret_access_key=}" ;;
      aws_session_token=*)     export AWS_SESSION_TOKEN="${line#aws_session_token=}" ;;
    esac
  done
  export AWS_DEFAULT_REGION=us-east-1
  aws sts get-caller-identity
}
```

It prints your account and an `assumed-role/voclabs/...` ARN when it worked. Do not screenshot or paste these credentials anywhere.

## Start a variant

With `base/` applied (`status.sh` says so), on the apply laptop:

```bash
labcreds
src/infrastructure/scripts/up.sh ec2        # variant A
src/infrastructure/scripts/up.sh fargate    # variant B
```

**What `up.sh ec2` does**

1. If no image is chosen for the stack, builds and pushes the app image (`push-image.sh`).
2. `tf.sh ec2 plan` prints the plan. **Read it.** After a teardown it should show about 25 to add, 0 to change, 0 to destroy (expected, not yet confirmed after the module refactor). Type `yes`.
3. `tf.sh ec2 apply` builds it (about 3 to 5 minutes, mostly the ALB) and backs up the state.
4. `secrets.sh fill` adds any missing secret field; it never changes an existing password.
5. `jobs.sh ec2 all` runs every database job in order on the new instance through SSM. On the existing database each one finds its work already done and changes nothing (the import reports `created=0 unchanged=...`). It waits for the instance to register with Systems Manager first.
6. `smoke.sh ec2` checks the site from outside. Expect `All checks passed.` (8 of 8).

**What `up.sh fargate` does**

1. Same image step. Then it decides whether the shared database is fresh (the shared secrets are incomplete or there is no operator login yet). **On a fresh database nothing else is needed, no variant A**: it fills the secrets, creates the stack with zero tasks (the apply would otherwise wait for tasks that cannot be healthy before the database exists), runs `jobs.sh fargate all` as one-off tasks, then applies again with one task. An already set-up database skips this and goes straight to the next step.
2. `tf.sh fargate plan` (first checking that the Dockerfile's start command and the copy in `fargate/ecs.tf` agree, [ADR-016](../../docs/decisions/ADR-016-fargate-health-probe-host-override.md)), then your `yes`, then apply. The apply returns when the service is steady, so a task that cannot start fails the apply instead of looping quietly. Expect about 27 to add.
3. `jobs.sh fargate check` runs `check_database` as a one-off task, proving a task can reach the database.
4. `smoke.sh fargate`.

The Fargate database jobs run from the unchanged image: `import` downloads the dataset from the bucket with boto3 and loads it, and `operator` generates the password inside the task and stores it in the operator secret with boto3 (never printed; [`scripts/fargate_jobs/`](scripts/fargate_jobs/)). `trainer-sql` stays on variant A: the trainer login only serves the offline ML training. **Status:** tested offline with a stubbed `aws` (routing, skip logic, task overrides, the two programs against a stubbed boto3). **Not yet run in AWS**, and a run from a completely empty account would need a new domain delegation, so it cannot be fully proven here.

The shops are at **https://shop-ec2.fourtytwofactors.me** and **https://shop-fargate.fourtytwofactors.me**. A hostname follows a new load balancer automatically.

Faster, when you know the database is intact: `scripts/tf.sh ec2 plan`, `scripts/tf.sh ec2 apply`, `scripts/smoke.sh ec2`.

**Operator login** (`demo-operator`, for `/analytics/`):

```bash
aws secretsmanager get-secret-value --secret-id inf2006-grp21/operator --query SecretString --output text
```

**Fixed or free capacity.** Both stacks have `min_capacity`, `max_capacity` and `desired_capacity` (default 1, 2, 1). For a fixed-capacity load run use `scripts/evidence.sh <stack> pin MIN MAX DESIRED count` (it writes the git-ignored `<stack>/session.auto.tfvars`, plans, applies and waits for the healthy count; `evidence.sh <stack> down` removes the file), or set the three in `<stack>/terraform.tfvars` by hand and clear them afterwards. An apply resets the count to these values ([ADR-013](../../docs/decisions/ADR-013-load-generator-stack-and-measurement-settings.md)).

## Stop a stack

```bash
labcreds
src/infrastructure/scripts/down.sh ec2        # or fargate, or loadgen
```

Terraform lists everything it will destroy; type `yes`. The script then prints leftover load balancers, instances, ECS clusters and NAT gateways; all lists must be empty. The database, its data, the zone, the certificate, the image and the secrets stay ([cost](#cost)).

## The load generator

Used only for the benchmarks ([load-harness.md](../../docs/plans/load-harness.md), [tests/load/README.md](../../tests/load/README.md)):

```bash
src/infrastructure/scripts/up.sh loadgen      # one c5.large, no inbound rules
aws ssm start-session --target <the instance id it prints>
src/infrastructure/scripts/down.sh loadgen    # when the test session ends
```

## If you are not on the apply laptop

You cannot plan or apply against the team's stacks: the state is on the owner's laptop, and a second state would fight over the same resources. You can:

- **Write and check code:** `terraform -chdir=src/infrastructure/fargate init -backend=false` then `terraform -chdir=src/infrastructure/fargate validate` (no credentials needed; same for `ec2`, `loadgen`, `base`), commit, and ask the owner to plan and apply.
- **Check a live site** (no credentials needed): `src/infrastructure/scripts/smoke.sh shop-ec2.fourtytwofactors.me`.
- **Read the record:** [evidence/aws-build-runbook.md](../../evidence/aws-build-runbook.md).

If the apply laptop is lost or unavailable, use the next section in your own Learner Lab account; never copy the owner's state to another machine.

## Build everything from nothing in a new account

For a teammate's own lab account, or to reproduce the build. About 45 minutes, most of it waiting. Everything is created fresh; nothing is shared with the team's account. You need a **domain you control** (HTTPS needs a certificate and the app enforces HTTPS); the team's `fourtytwofactors.me` can be delegated to only one Route 53 zone at a time, so another account must use its own domain.

1. **Clone and credentials**
   ```bash
   git clone <repo-url> && cd <repo> && git checkout <branch>
   labcreds
   src/infrastructure/scripts/status.sh      # tools and credentials ok? it says what to do next
   ```

2. **Set up the shared part**
   ```bash
   src/infrastructure/scripts/up.sh base
   ```
   It asks for an alarm email address and your domain, creates the S3 bucket with the CLI (the lab denies a read Terraform's bucket resource needs; Terraform then manages every setting on it), writes `base/terraform.tfvars`, shows the plan (about 38 to add) and applies it. The RDS database takes about 9 minutes. **While the apply waits for the certificate, it prints four name servers: set them at your registrar** (Namecheap: Domain List, Manage, Nameservers, Custom DNS, enter the four, click the green tick). The apply then finishes by itself within minutes. Click the confirmation link in the email AWS sends (check spam).

   Check delegation by hand if you like: `dig NS <domain> @a0.nic.me +norec | grep -A8 'AUTHORITY SECTION'` should show the AWS servers.

3. **Start variant B, the final architecture** (builds and pushes the image, fills the secrets, creates the stack with zero tasks, bootstraps and migrates the database, imports the dataset built from `data/raw/` and checked against `data/derived/shoes/checksums.txt`, creates the operator, refreshes the analytics, then starts one task and smoke-tests; no variant A needed, [ADR-019](../../docs/decisions/ADR-019-variant-b-sets-up-its-own-database.md)):
   ```bash
   src/infrastructure/scripts/up.sh fargate
   ```

4. **Variant A** (the evaluated alternative) only if you want to reproduce the comparison:
   ```bash
   src/infrastructure/scripts/up.sh ec2
   ```
   If step 3 fails on your account, the order we actually ran is the fallback: `up.sh ec2` first (it sets up the database), then `up.sh fargate`.

The recorded evidence used the image `release-c19d547` (digest `sha256:fa72e949...cb481`); a rebuild has a different digest, so record yours.

## Command reference

All scripts are under `src/infrastructure/scripts/`, stop at the first error, and need `labcreds` except `status.sh` (it reports instead of stopping) and `smoke.sh`.

| Command | Does | When |
|---|---|---|
| `status.sh` | tools, credentials, what each folder has built and whether AWS agrees, what to run next. Changes nothing | first, any time |
| `up.sh base` | first-time setup: questions, bucket, tfvars, plan, apply, name-server prompt | once per account |
| `up.sh <ec2\|fargate\|loadgen> [--yes]` | image, plan, confirm, apply, then the stack's jobs and smoke test | start of a session |
| `down.sh <ec2\|fargate\|loadgen>` | destroy the stack, list leftovers | end of a session |
| `smoke.sh <ec2\|fargate\|hostname>` | 8 outside-in checks, no credentials needed | after any change |
| `jobs.sh ec2 <job>` | one job on the instance through SSM: `bootstrap`, `migrate`, `trainer-sql`, `restart`, `check`, `import`, `operator`, `refresh`, `all` | fresh database; `check` any time |
| `jobs.sh fargate <job>` | one job as a one-off ECS task: `bootstrap`, `migrate`, `check`, `import`, `operator`, `refresh`, `all` (`trainer-sql` and `restart` are variant A only) | fresh database; `check` any time |
| `tf.sh <base\|ec2\|fargate\|loadgen> plan\|apply` | fmt check, validate, saved plan, records the commit; applies only that plan, then backs up the state | used by `up.sh`; use directly for a faster or partial run |
| `secrets.sh fill\|check` | complete or check the secrets (prints key names and match/DIFFER only) | `up.sh ec2` runs `fill`; `check` any time |
| `secrets.sh master-in\|master-out` | used by `jobs.sh bootstrap`; do not run by hand | |
| `push-image.sh [sha]` | build (only if the tag is missing), push, release-tag, record the digest for the stacks | per image change; `up.sh` runs it if no image is chosen |
| `evidence.sh preflight`, `evidence.sh <ec2\|fargate> up\|security\|func\|pin\|alarm\|waf\|logs\|down` | records the cloud evidence identically for both variants: dated, redacted files in `evidence/raw/` (FUNC-03, SEC-09 to 11, 17, 18, MON-01 to 03); `pin MIN MAX DESIRED count\|block` sets capacity and WAF mode for load runs | evidence sessions, [runbook](../../docs/plans/evidence-session.md) |

**Manual access** (debugging only; no SSH, no port 22):

```bash
# variant A: a shell on the instance
INSTANCE=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names inf2006-grp21-ec2-asg \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)
aws ssm start-session --target "$INSTANCE"
sudo docker logs --tail 50 web          # the app
sudo cat /var/log/cloud-init-output.log # the boot script

# variant B: logs and service events (there is no shell on a task)
aws logs tail /inf2006-grp21-fargate/app --since 30m
aws ecs describe-services --cluster inf2006-grp21-fargate-cluster --services inf2006-grp21-fargate-service \
  --query 'services[0].events[:5].message'
```

## Cost

US East list prices, rounded and from memory; verify before relying on them. Read the lab balance (Learner Lab page) at the start and end of each session.

| Running | About |
|---|---|
| `base/` only (RDS `db.t4g.small` and storage, secrets, zone) | USD 1.2 per day |
| plus the `ec2` stack (one `c5.large`, ALB, public IPv4 addresses, WAF) | plus USD 0.13 per hour, about USD 3 per day |
| plus the `fargate` stack (one 2 vCPU / 4 GB task, ALB, public IPv4 addresses, WAF) | about USD 0.15 per hour (unverified) |
| a second instance or task while scaled out | plus USD 0.085 (instance) or 0.10 (task) per hour |
| `loadgen` (one `c5.large`) | about USD 0.09 per hour |

Everything running continuously is about USD 4 per day for one variant; the lab budget is USD 50. **Tear the stacks down when you stop** and keep `base/` up: rebuilding a stack takes about 5 minutes, rebuilding `base/` means re-bootstrapping and re-importing.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `no working lab credentials`, `ExpiredToken`, `InvalidToken` | Credentials expired. `labcreds` again |
| `uncommitted changes in src/infrastructure; commit first` | `tf.sh` only applies committed code. Commit (or stash), then plan again |
| `the plan was made from commit X, HEAD is Y` | You committed after planning. Plan again |
| A plan shows a replace (`-/+`) or destroy you did not expect | Stop and ask; do not apply |
| `STOP: src/Dockerfile's CMD is not the command in fargate/ecs.tf` | Someone changed the Dockerfile's start command. Make `web_command` in `fargate/ecs.tf` match it ([ADR-016](../../docs/decisions/ADR-016-fargate-health-probe-host-override.md)) |
| `up.sh fargate` stops partway on a fresh database | Run `up.sh fargate` again: finished jobs are skipped. If it stopped between the two applies, the stack may hold zero tasks until the rerun finishes |
| `jobs.sh ec2`: `is not Online in Systems Manager` | The instance is still booting (about 3 to 4 minutes after launch). Rerun |
| Variant A: target unhealthy, site returns 502/503 | Start a session (above) and read `docker logs web` and the cloud-init log |
| Variant B: the apply fails or waits on the service | `aws ecs describe-services` (events, above) and `aws logs tail` show why the task stopped (image pull, role, the probe-host lookup) |
| `down.sh fargate` waits a long time on a security group | A stopped task's network interface is still releasing; Terraform retries by itself |
| `smoke.sh`: `/products/ lists 0 product links` | The database has no data. `scripts/jobs.sh ec2 import` |
| `app-job: usage: ...` | Job name mistyped; it is `bootstrap`, not `boostrap` |
| A security group rule fails with `Invalid rule description` | AWS rejects some characters (an apostrophe, for one) in descriptions |

More history: the "Problems met" lists in the [build runbook](../../evidence/aws-build-runbook.md).

## Final teardown

Only after all evidence is exported (plan section 13: pre-destroy export checklist). In this order:

```bash
src/infrastructure/scripts/down.sh fargate
src/infrastructure/scripts/down.sh ec2
src/infrastructure/scripts/down.sh loadgen
terraform -chdir=src/infrastructure/base destroy        # database, zone, certificate, registry, secrets
# The bucket is not Terraform's: empty every object version, then delete it.
B=<bucket name>
aws s3api list-object-versions --bucket "$B" --output json \
  | jq '{Objects: ([.Versions[]?, .DeleteMarkers[]?] | map({Key, VersionId}))}' > /tmp/v.json
jq -e '.Objects | length > 0' /tmp/v.json >/dev/null && aws s3api delete-objects --bucket "$B" --delete file:///tmp/v.json
aws s3api delete-bucket --bucket "$B"
```

Skip a `down.sh` for a stack that is already down (`status.sh` shows). `delete-objects` takes at most 1,000 entries per call; this bucket holds far fewer. Then set the registrar's name servers back to its own DNS if the domain is reused.

## What comes next

In order (plans: [aws-ecs-comparison.md](../../docs/plans/aws-ecs-comparison.md) sections 7 and 9, [fargate-variant.md](../../docs/plans/fargate-variant.md)):

> **Update (9 October 2026):** steps 1 to 3 were carried out on 8 October (variant A) and 9 October (variant B), at one repeat per condition ("indicative, n = 1") and not every item listed below; what was run is in [evidence/README.md](../../evidence/README.md). Both stacks are torn down; only `base/` remains. The Fargate database jobs and the fresh-database bring-up were tested offline only, not run in AWS.

1. **Apply and verify both variants** (`up.sh ec2`, then `up.sh fargate`), record both in the runbook with the measured cost, then the independent review of the module, both stacks and the scripts.
2. **Benchmark variant A.** The harness is in `tests/load/`; the generator runs in-region from `loadgen/`.
   - **RDS pilot:** one run at the 1,000-user step with RDS CPU, connections, memory and credits captured; size up once (`db.t4g.medium`) only if the database is the limit.
   - **The ladder:** 1, 10, 100 and 1,000 users, at least 3 repeats each, plus a separate saturation run.
   - **Scale-out:** time from the scaling trigger to a healthy second instance.
   - **Recovery:** kill an instance, then record the alarm, the replacement time and the error window.
   - **Rollout:** time for an instance refresh to a new image.
   - **The rest:** WAF block-mode test, Logs Insights export, Multi-AZ failover test.

   Results go to `evidence/raw/` and `evidence/test-performance.md`, `evidence/test-resilience.md`.
3. **Benchmark variant B** with the identical harness, ladder and repeats, one variant taking load at a time; then the comparison (criteria and weights fixed before the first comparison run): scale-out time, recovery, rollout, latency and throughput, cost per hour and per 1,000 requests, and operational burden.
4. **Write-up pieces:** `docs/REPRODUCE_CLOUD.md` (based on this file), the architecture diagram check, the threat-control map update, reference IAM policies, then final teardown.
