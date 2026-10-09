# AWS build runbook

One dated entry per Terraform stage: what was applied, from which commit, the acceptance checks and their actual results, problems met, and the lab balance. Built per [aws-ecs-comparison.md](../docs/plans/aws-ecs-comparison.md) (the AWS plan). The procedures, lab capability record and as-built entries for all stages live in this one file. Account IDs are redacted as `<account>`; no public IP addresses or tokens are recorded.

## Stage 1: network, security groups, storage, secrets, monitoring (29 September 2026)

**Applied from:** Terraform 1.16.4, AWS provider 6.66.0, region `us-east-1`, on the single apply device (the owner's Fedora laptop).

| Step | Commit | Result |
|---|---|---|
| Plan `stage1.tfplan` | `8f2e89b` | 39 to add, 0 to change, 0 to destroy. Passed the review gate ([log](../docs/reviews/aws-terraform.md#stage-1-network-security-groups-storage-secrets-monitoring)) |
| Apply `stage1.tfplan` | `8f2e89b` | **Partial: 32 of 39 created**, then failed (below) |
| Plan `stage1b.tfplan` | fix applied from the working tree, committed afterwards (see note) | 6 to add, 0 to change, 0 to destroy; `aws_s3_bucket.main` removed from state without being destroyed; no drift on the 32 existing resources |
| Apply `stage1b.tfplan` | same | Complete. 38 resources managed; the bucket is looked up as a data source |

**Problem: S3 object lock read denied by the lab.** The first apply created the bucket, then failed reading it back:

```
Error: reading S3 Bucket (inf2006-grp21-data-<suffix>) object lock configuration:
... api error AccessDenied: User: arn:aws:sts::<account>:assumed-role/voclabs/<session>
is not authorized to perform: s3:GetBucketObjectLockConfiguration ...
with an explicit deny in a service control policy
```

The `aws_s3_bucket` resource makes this call on every read, so no later plan could succeed while Terraform managed the bucket. A probe of 16 bucket read calls with the CLI showed `GetObjectLockConfiguration` is the **only** one denied. Fix: the bucket became `data "aws_s3_bucket"` (looked up by name), a `removed` block with `destroy = false` dropped it from state, and all six bucket settings stay Terraform resources. Consequence: `terraform destroy` will not delete the bucket; stage 6 empties and deletes it with the CLI. The CLI procedure is under [Procedures](#procedures) below.

**Note on the apply rule.** The plan requires applying committed code only. The bucket fix was planned and applied from the working tree before it was committed, to recover from the failed apply in the same session. It is committed immediately after, unchanged; this entry records the exception.

### Acceptance

| Check | Command | Expected | Actual |
|---|---|---|---|
| Subnets in two AZs | `aws ec2 describe-subnets --filters Name=tag:Project,Values=inf2006-grp21` | public and private subnets in `us-east-1a` and `us-east-1b` | Pass: `inf2006-grp21-public-a`/`private-a` in `us-east-1a`, `public-b`/`private-b` in `us-east-1b` |
| Anonymous S3 access denied | `curl -s -o /dev/null -w '%{http_code}' https://<bucket>.s3.amazonaws.com/anything` | 403 | Pass: 403 |
| SNS email subscription confirmed | `aws sns list-subscriptions-by-topic` | a subscription ARN, not `PendingConfirmation` | Pass, after confirming. The confirmation email was delivered to **Gmail spam**; the sender was marked not-spam so stage 4 alarm emails arrive |
| No drift after apply | `terraform plan` | no changes | Pass (the stage 1b plan refreshed all 32 existing resources with no changes) |

### Image and secret values (step 8.5 and 8.6)

| Step | Command | Result |
|---|---|---|
| Build and push the image | `docker build -t <ecr-url>:<git-sha> -f ../Dockerfile ..`, then `docker push` after `aws ecr get-login-password \| docker login` | Pushed `inf2006-grp21-app:c19d547` (the commit it was built from), digest `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481`. The repository's tags are immutable, so this tag always means this image |
| Set the non-database secret fields | `put-secret-value` per secret; passwords and `DJANGO_SECRET_KEY` generated with Python's `secrets` module and passed through shell variables, never typed or printed | Pass. Keys present (checked with `jq 'keys'`, which prints no values): `web` = `DJANGO_SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`; `migration` and `trainer` = `POSTGRES_USER`, `POSTGRES_PASSWORD`; `bootstrap` = `MIGRATION_USER`, `MIGRATION_PASSWORD` |

Database logins chosen: `inf2006_web` (runtime), `inf2006_migration` (schema owner), `inf2006_trainer` (read-only). They do not exist in a database yet; `db_bootstrap` creates them in stage 2 with these passwords. **Do not regenerate these values after bootstrap**: the database would keep the old passwords. Stage 2 reads each secret back and adds `POSTGRES_HOST` and `POSTGRES_DB`, plus `BOOTSTRAP_USER`/`BOOTSTRAP_PASSWORD` copied from the secret RDS creates for its master login.

**Stage 1 complete.**

### Cost

Lab balance after stage 1: USD 0.20 of USD 50.00 used (read from the Learner Lab page, 29 September 2026; the figure updates with a delay, so same-day charges may not show yet). Nothing in stage 1 bills hourly; the four secrets cost about USD 0.05 per day together. The stack is left running between sessions.

## State split, base/ and variant A (1 October 2026)

Per [aws-ecs-comparison.md](../docs/plans/aws-ecs-comparison.md) and decisions [ADR-001 to ADR-008](../docs/decisions/). Applied with Terraform 1.16.4, AWS provider 6.66.0, from the owner's Fedora laptop, using `scripts/tf.sh` (plan from a clean tree, apply only that saved plan from the same commit).

| Step | Commit | Result |
|---|---|---|
| Migration `scripts/migrate-state.sh run` | `308fb28` | 10 resources destroyed (`sg-alb`, `sg-app`, their 7 rules, app log group; nothing was attached) and 28 moved into `base/` with `terraform state mv`. **Gate:** the first `base/` plan showed 27 unchanged and one replace, the ECR lifecycle policy, which was an unapplied change from `f634a9c` (not a migration fault). Applied it; the next plan: **no changes** |
| `base/` zone | `1931e27` | Route 53 zone for `fourtytwofactors.me`: 1 added, 16 tag-only updates (`Stack = base`). **The lab allows hosted-zone creation.** Name servers set at Namecheap; the `.me` registry showed the four Route 53 servers the same evening |
| `base/` RDS | `894ce13` | 4 added in 8m35s. **The lab allows `db.t4g.small` and an RDS-managed master password.** PostgreSQL 17.9, private, encrypted, `rds.force_ssl = 1`, 7-day backups |
| `base/` certificate | `3fe8b02` | 4 added. ACM certificate for `shop-ec2` and `shop-fargate`, DNS-validated in Terraform; issued within seconds because delegation was live |
| Secrets, image | scripts `f6d528d` | `secrets.sh fill`: all four secrets hold exactly the loader's field sets; the runtime login, migration login, signing key and host/db checks all `match`. `push-image.sh c19d547`: nothing rebuilt; `release-c19d547` tagged; digest `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (unchanged from stage 1) |
| `ec2/` | `eb9fd70`, fix `b8e936d` | 17 resources. First apply created 16 and failed on one: AWS rejected an apostrophe in a security-group rule description. Fixed, replanned (1 to add), applied. **The lab allows `c5.large`**; the instance registered with Session Manager and the target went healthy without the database being ready |

### Acceptance (variant A)

| Check | Result |
|---|---|
| Target healthy behind the ALB | Pass: `healthy` before any database job (`/health/` is database-independent) |
| `db_bootstrap` | Pass: "Application database roles and grants configured." Run over Session Manager inside the VPC, with the RDS master login copied into the bootstrap secret only for the run and replaced by the placeholder straight after |
| `migrate` | Pass: all migrations applied, including the `reporting` views and permissions |
| Trainer login | Pass: both `psql` runs used `sslmode=verify-full` with the RDS CA bundle. Role has every privilege flag false; read on the 9 granted tables and some `auth_user` columns; `can_write` false on all 10 |
| `check_database` as the runtime login | Pass: `{"database": "ok", "migrations": "applied"}` |
| Runtime login cannot `CREATE TABLE` | Pass: `permission denied for schema public` |
| Trainer login cannot `INSERT` | Pass: `permission denied for table catalogue_product` |
| Trainer cannot read `auth_user.password` | Pass: `permission denied for table auth_user` |
| HTTPS at its own hostname | Pass: `https://shop-ec2.fourtytwofactors.me/health/` and `/login/` both return 200 |

Not yet done: HTTP-to-HTTPS redirect check (`curl -I http://...`), a PASSWORD search of the RDS log group, the dataset import, scaling, alarms and WAF.

### Problems met

- ECR lifecycle policy was an unapplied change when the gate ran. The gate caught it, as designed.
- `rds.force_ssl`: AWS stores `pending-reboot`, the provider default was `immediate`, so every plan showed a change. Fixed by declaring it (`33280df`).
- `tf.sh` wrote an untracked marker file, so the next plan saw a dirty tree. Fixed by ignoring it (`3fe8b02`).
- Security-group rule descriptions reject an apostrophe (above).

### Cost

Lab balance: to be read from the Learner Lab page and added here. Running now: RDS `db.t4g.small`, one `c5.large`, one ALB, the Route 53 zone, four secrets. Rough rate while both are up: about USD 0.20 per hour.

## Variant A: operations, scaling, alarms and WAF (1 October 2026, evening)

| Step | Commit | Result |
|---|---|---|
| `jobs.sh ec2 import` (first real run of `jobs.sh`) | `1d0f62d` | **The lab allows SSM `SendCommand`.** The first attempt failed: only `checksums.txt` and `product_map.csv` of the derived dataset are committed, so the rest was not on disk. `import` now rebuilds it from `data/raw/` and checks it against `checksums.txt` (all 5 files OK). Loaded 20,000 customers, 200 products, 100,000 orders, 237,537 lines, **0 rejected** |
| Import rerun | same | Several runs were started and two interrupted on the laptop (the job keeps running on the instance). A clean rerun reported `created=0 unchanged=<full count>` for every table: the data is complete and the importer is idempotent |
| `base/` operator secret | `c4ae7c4` | 1 added (`inf2006-grp21/operator`) |
| `ec2/` scaling, alarms, queries, WAF | `c4ae7c4` | 8 added, 1 changed (ASG max 1 to 2): target tracking on requests per target (300), 3 alarms to SNS, 2 saved Logs Insights queries, WAF web ACL in count mode and its association with the ALB. **The lab allows WAFv2 web ACLs on an ALB, CloudWatch alarms and query definitions** |
| `jobs.sh ec2 operator` | `c4ae7c4` | `demo-operator` created; the password was generated on the instance and stored in the operator secret |
| `jobs.sh ec2 refresh` | `c4ae7c4` | Run `5d191a3b` completed: 41,345 daily rows from 71,079 order lines, business dates 2025-01-01 to 2026-01-01, 3.0 s |
| `smoke.sh ec2` | `c4ae7c4` | 8 of 8 passed: `/health/` 200, HTTP 301 to HTTPS, certificate verifies, `/login/` 200, `/products/` lists products, HSTS, `nosniff`, `X-Frame-Options` |
| Teardown `down.sh ec2` | `0cccb09` | 25 destroyed (the whole `ec2/` stack). Checked afterwards: no `inf2006-grp21-ec2` load balancer, no instance tagged `Stack=ec2`, `ec2/` state empty. `base/` (database and data, zone, certificate, registry, secrets) left running by design, about USD 1.2 per day |

Not yet done: the WAF block-mode test, any alarm firing, a scale-out, a recovery test and the Logs Insights export; these are the evidence runs.

## Variant A: the evidence session (8 October 2026, UTC)

Run by the owner from the laptop with `scripts/evidence.sh`; raw output in `raw/` (names below). The load generator was a `c5.large` in us-east-1 (Session Manager shell, `tmux`). Image `release-c19d547`, digest `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481`, unchanged from stage 1. Results and interpretation are in [test-performance.md](test-performance.md), [test-security.md](test-security.md), [monitoring.md](monitoring.md) and [load-summary.md](load-summary.md); this entry is the build and operations record.

**Lab balance at start:** USD 7.2 of USD 50 used. **Lab balance at end of both sessions (A on 8 October, B on 9 October):** USD 9.8 of USD 50 used, read by the owner from the Learner Lab page. The increase of about USD 2.6 covers the A and B sessions together, including the shared base's daily cost; it is not split between the sessions.

### What ran, with times

| Time (UTC) | Step | Commit | Result | Raw file |
|---|---|---|---|---|
| 14:32 to 14:35 | Preflight: image in the registry, `LabRole` trust, Fargate quota, service-linked roles, alarm email | `81c0e2a` | Image present. `LabRole` trusts `ecs-tasks.amazonaws.com`. The Fargate quota **cannot be read** (`AccessDenied`). The ECS service-linked roles were missing; `create-service-linked-role` created both (14:33:40 and 14:33:42); a second attempt at 14:35 failed harmlessly with "already taken". Alarm email subscription confirmed | `PRE_2026-10-08_*.txt` |
| 14:36:48 | `up.sh ec2`, first attempt | `81c0e2a` | **Stopped silently after 4 s, exit 2** (defect 1) | `OPS_2026-10-08_ec2_up.txt` |
| 14:38:50 to 14:52:22 | `up.sh ec2` after the fix (13 min 32 s including plan review, typing `yes`, apply and the first jobs) | `74d394a` | Plan 25 to add; **apply complete, 25 added**. Slowest resources: ALB 2 min 16 s, Route 53 record 33 s, Auto Scaling group 23 s. Secrets checks all `match`. Then `db_bootstrap` **failed**, exit 1 (defect 2) | `OPS_2026-10-08_ec2_up_rerun.txt` |
| 15:01:43 to 15:02:29 | `jobs.sh ec2 migrate`, `check`, then `smoke.sh` by hand (46 s) | `74d394a` | migrate ok; `{"database": "ok", "migrations": "applied"}`; smoke 8 of 8 | `OPS_2026-10-08_ec2_jobs.txt` |
| 15:04:46 to 15:05:43 | Security evidence and resource IDs | `74d394a` | SEC-09, SEC-10, SEC-11 PASS | `SEC-09_*`, `SEC-10_*`, `SEC-11_*`, `SESSION_2026-10-08_ec2_ids.txt` |
| 15:10:27 | Analytics refresh | `74d394a` | 41,345 daily rows from 71,079 lines, 3.1 s | `DATA-01_2026-10-08_aws_refresh.txt` |
| 15:57:49 to 15:59:19 | FUNC-03 part 1 (75 s smoke run, summary) | `74d394a` | 2 orders, 0 errors | `FUNC-03_2026-10-08_ec2_summary.txt`, `LOAD-ec2-smoke-r1_2026-10-08/` |
| 16:48:08 to 17:11:10 | RES-03a scale-out (23 min) | `81c0e2a` | Alarm 299 s after the step, healthy 460 s after the step | `RES-03-ec2-scaleout-r1_2026-10-08/` |
| 17:18:07 to 17:19:06 | Pin to 2 / 2 / 2 (plan 20 s, apply 11 s) | `4e06901` | Plan: 1 to change (`min_size` 1 to 2; the group was still at 2 after the scale-out) | `OPS_2026-10-08_ec2_pin-2-2-2-count_{plan,apply}.txt` |
| 17:23:18 to 17:43:20 | RES-03b replacement (20 min); graceful removal at 17:29:37.9 | `81c0e2a` | Two healthy again after 114 s, 0 errors | `RES-03-ec2-replace-r1_2026-10-08/` |
| 17:48 to 17:50 | MON-03 forced alarm, history | `4e06901` | ALARM and OK with SNS actions; ALARM email received | `MON-03_2026-10-08_ec2_*.txt` |
| 17:52:01 to 17:52:24 | Database state reset 1 (dry run, then apply) | `4e06901` | 37 load orders removed and stock restored; left 0 orders, 0 lines, 0 carts | `OPS_2026-10-08_ec2_reset-{dry,apply}.txt` |
| 17:52:44 to 17:53:06 | First log queries (MON-01, MON-02, SEC-18) | `4e06901` | Taken before the saturation run; superseded by the 18:51 reruns | `MON-01_*`, `MON-02_*`, `SEC-18_*` without `_rerun` |
| 17:59:08 to 18:02:45 | Pin to 1 / 1 / 1 (plan 18 s, apply 13 s) | `4e06901` | Desired 2 to 1, max 2 to 1, min 2 to 1 | `OPS_2026-10-08_ec2_pin-1-1-1-count_{plan,apply}.txt` |
| 18:20:58 to 18:41:00 | LOAD-03 saturation (20 min), 1 to 512 users | `81c0e2a` (dirty) | Practical capacity 16 users; maximum 118.8 requests/s; 0 errors | `LOAD-ec2-saturation-r1_2026-10-08/` |
| 18:49:54 to 18:50:12 | Database state reset 2 | `3c910b8` | 274 load orders removed and stock restored; left 0 | `OPS_2026-10-08_ec2_reset-{dry2,apply2}.txt` |
| 18:51:18 to 18:51:34 | Log queries rerun over the whole session | `3c910b8` | MON-01 sample and status table ok; MON-02 query 2 fails (defect 4); SEC-18 0 matches | `MON-01_*_rerun`, `MON-02_*_rerun`, `SEC-18_*_rerun` |
| 18:51:45 to 18:53:56 | `down.sh ec2` (2 min 11 s; the Auto Scaling group alone took 1 min 44 s) | `3c910b8` | **25 destroyed.** Leftover lists (load balancers, instances, NAT gateways) empty. `base/` left running | `OPS_2026-10-08_ec2_down.txt` |

From the first preflight to the end of `down`: 4 hours 22 minutes. The loadgen stack's own start and stop were not recorded by `evidence.sh` (no `OPS_*_loadgen_*` file); its times, and whether it was torn down, are for the owner to add. Terraform state backups written by `tf.sh` (`ec2/terraform.tfstate.*.bak`) hold resource IDs and must stay off the repository.

### Defects found during the session

| # | Defect | Effect | Status |
|---|---|---|---|
| 1 | `tf.sh` exited silently with status 2 when the other variant's stack had no image tag yet (variant B had none) | The first `up.sh ec2` stopped after 4 s with no message | **Fixed** in `74d394a` (`src/infrastructure/scripts/tf.sh`); rerun succeeded two minutes later |
| 2 | `db_bootstrap` cannot be repeated on an existing database: it refuses a database that already has the roles and ownership (`FAIL: unsafe bootstrap configuration, existing privileges/ownership, or database operation`) | `up.sh` stopped with exit 1 at the bootstrap step because the database was already bootstrapped; the migrate, check and smoke steps after it did not run and were done by hand | **Open.** Work-around used: `jobs.sh ec2 migrate`, `check` and `smoke.sh` by hand. A fix would belong in `up.sh` (skip bootstrap when the database exists), not in the frozen application code |
| 3 | The log and metric redaction rule rewrote any 12 digits after a decimal point as `<ACCOUNT>`, so a 12-decimal metric value was mangled | `locust_stats.csv`, `locust_stats_history.csv` and `report.html` of the smoke, scale-out and replacement exports show `<ACCOUNT>` inside some averages; request logs unaffected | **Fixed** in `tests/load/common.py` (`0276f52`, with a self-test); the three exported folders were not edited |
| 4 | The saved query `errors-and-warnings-per-minute` in `modules/web-entry/alarms.tf` (lines 79 to 80) is rejected by Logs Insights (`MalformedQueryException`) | MON-02 query 2 cannot run; the same module serves variant B | **Open** (Terraform change not made in the documentation pass) |
| 5 | The saturation steps up to 512 were edited into `run.py` on the generator, so the run records `git_dirty_harness: true` | Provenance of that run needs the explanation in this file | Committed afterwards in `0276f52` |
| 6 | No scale-in in the scale-out run: the 5-minute low phase ended before the group scaled in | The scale-in part of the RES-03a expectation is unmet | Reported, not rerun |
| 7 | The first `evidence.sh` log queries ran at 17:52, before the saturation run | Their window missed the saturation traffic | Rerun at 18:51; both sets kept |

Not a defect, but worth knowing: the scaling target of 300 requests per target per minute is about 4 percent of the measured one-unit ceiling and was set before any data (see [test-resilience.md](test-resilience.md)).

### Cost

Estimate at the list prices in `tests/load/prices.json` (written 3 October 2026, **not verified**; excludes storage, data transfer, load-balancer capacity units, WAF requests, CloudWatch and public IPv4 addresses). Variant A stack, 4.25 hours (14:38:50 to 18:53:56): first `c5.large` 4.25 h at USD 0.085 per hour, second `c5.large` about 1.1 h (16:57 to about 18:03), ALB 4.25 h at USD 0.0225 per hour, RDS `db.t4g.small` 4.25 h at USD 0.032 per hour, so about USD 0.7 in total, of which RDS runs all day regardless. Load generator: USD 0.085 per hour while up. The real figure is the difference between the lab balance at the start (USD 7.2 used) and at the end of both sessions (USD 9.8 used), which the owner read; it covers A, B and the base together.

## Variant B: the evidence session (9 October 2026, UTC)

Run by the owner from the laptop with `scripts/evidence.sh`, the same way as variant A; raw output in `raw/` (index: [raw/INDEX.md](raw/INDEX.md)). Same image digest `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481`, same RDS, same generator type (`c5.large`, us-east-1). Results are in the same test records as A, in side-by-side columns: [test-performance.md](test-performance.md), [test-security.md](test-security.md), [monitoring.md](monitoring.md), [test-resilience.md](test-resilience.md), [load-summary.md](load-summary.md). Lab balance: see the A entry above (one reading for both sessions).

### What ran, with times

| Time (UTC) | Step | Commit | Result | Raw file |
|---|---|---|---|---|
| 01:53:18 to 02:01:51 | `up.sh fargate` (8 min 33 s including plan review, typing `yes`, apply and the first job) | `33963c5` | Plan 27 to add; **apply complete, 27 added, 0 failed**. Slowest resources: ALB 2 min 16 s, ECS service 1 min 30 s. `jobs fargate check` ok; smoke 8 of 8. No bootstrap step ran, so defect 2 of the A entry did not occur | `OPS_2026-10-09_fargate_up.txt` |
| 02:02:43 to 02:04:30 | Resource IDs, SEC-10, SEC-09, SEC-11 (the app check is a one-off task, 68 s) | `33963c5` | SEC-09, SEC-10, SEC-11 PASS | `SESSION_2026-10-09_fargate_ids.txt`, `SEC-09_*`, `SEC-10_*`, `SEC-11_*` |
| 02:04:53 to 02:06:21 | FUNC-03 part 1 (75 s smoke run, summary) | `33963c5` | 2 orders, 0 errors | `FUNC-03_2026-10-09_fargate_summary.txt`, `LOAD-fargate-smoke-r1_2026-10-09/` |
| 02:07:58 | CPU model of the Fargate hardware (one-off task) | | Intel Xeon Platinum 8259CL @ 2.50 GHz | `RES-03-fargate-scaleout-r1_2026-10-09/cpu.json` |
| 02:27:15 to 02:50:17 | RES-03a scale-out (23 min) | `81c0e2a` (dirty) | Alarm 305 s after the step, healthy 407 s after the step | `RES-03-fargate-scaleout-r1_2026-10-09/` |
| 02:59:07 | Pin to 2 / 2 / 2, first plan | `33963c5` | **Failed attempt, exit 1**: `tf.sh` refused to plan with an uncommitted change in `src/infrastructure` (the guard worked as designed); the change was committed as `e4bc928` and the plan rerun | `OPS_2026-10-09_fargate_pin-2-2-2-count_plan.txt` |
| 03:03:08 | The scale-out task is stopped (scale-in) | | Seen in the service events printed at 03:10 | `SESSION_2026-10-09_fargate_service-events.txt` |
| 03:04:04 to 03:08:07 | Pin to 2 / 2 / 2: plan rerun (20 s), apply (61 s, which waits for the service to be steady) | `e4bc928` | 2 changes | `OPS_2026-10-09_fargate_pin-2-2-2-count_plan_rerun.txt`, `…_apply.txt` |
| 03:12:27 to 03:32:29 | RES-03b replacement (20 min); graceful stop at 03:17:34.5 | `81c0e2a` (dirty) | Two healthy again after 50 s, 0 errors | `RES-03-fargate-replace-r1_2026-10-09/` |
| 04:11:15 to 04:13:23 | MON-03 forced alarm, history | `e4bc928` | ALARM and OK with SNS actions; OK email received | `MON-03_2026-10-09_fargate_*.txt` |
| 06:07:35 | Pin to 1 / 1 / 1, first plan | `e4bc928` | **Failed attempt, exit 1**: AccessDenied errors reading the lab role, registry, ECS, load balancer, log group, security groups and WAF, each with "an explicit deny in an identity-based policy: `voc-cancel-cred`". That policy name suggests the lab session's credentials had been cancelled (an inference from the name); the plan began about three hours after the replacement run. Rerun after the credentials were refreshed | `OPS_2026-10-09_fargate_pin-1-1-1-count_plan.txt` |
| 06:17:53 to 06:19:43 | Pin to 1 / 1 / 1: plan rerun (19 s), apply (16 s) | `e4bc928` | 2 changes | `OPS_2026-10-09_fargate_pin-1-1-1-count_plan_rerun.txt`, `…_apply.txt` |
| 06:23:24 to 06:43:26 | LOAD-03 saturation (20 min), 1 to 512 users | `81c0e2a` (dirty) | Practical capacity 8 users; maximum 105.5 requests/s; 0 errors; at 512 users the task failed health checks twice and ECS replaced it | `LOAD-fargate-saturation-r1_2026-10-09/` |
| 06:45:52 to 06:48:13 | Database state reset 1 (dry run, then apply) | `e4bc928` | 299 load orders removed and stock restored; left 0 | `OPS_2026-10-09_fargate_reset-{dry,apply}.txt` |
| 06:49:14 to 06:49:53 | Pin to block mode (plan 19 s, apply 11 s) | `e4bc928` | 1 changed (the WAF rule action) | `OPS_2026-10-09_fargate_pin-1-1-1-block_{plan,apply}.txt` |
| 06:54:14 to 07:02:56 | SEC-17 WAF burst, metrics, sampled requests | `e4bc928` | Attempts 1 to 24 HTTP 200, 25 to 29 HTTP 403 from the load balancer, browsing 200; `BlockedRequests` 5 | `SEC-17_2026-10-09_fargate_*.txt` |
| 07:06:03 to 07:10:19 | Database state reset 2 (dry run, then apply) | `e4bc928` | Nothing left to remove | `OPS_2026-10-09_fargate_reset-{dry,apply}_rerun.txt` |
| 07:11:14 to 07:11:39 | Log queries (MON-01, MON-02, SEC-18) | `e4bc928` | MON-02 query 2 fails as on A; SEC-18 0 matches in 77,326 records | `MON-01_2026-10-09_*`, `MON-02_2026-10-09_*`, `SEC-18_2026-10-09_*` |
| 07:14:26 to 07:18:55 | `down.sh fargate` (4 min 29 s; the ECS service alone took 2 min 36 s) | `e4bc928` | **27 destroyed.** Leftover lists (load balancers, instances, NAT gateways) empty. `base/` left running | `OPS_2026-10-09_fargate_down.txt` |

From `up` to the end of `down`: 5 hours 25 minutes. Two tasks were pinned from the apply at 03:08:07 to the apply at 06:19:43. As for A, the loadgen stack's own start and stop are not in an `OPS_*` file, and the owner cannot confirm the times afterwards, so the generator's running hours (and its cost, USD 0.085 per hour at the unverified list price) are not stated.

### Defects and observations from the B session

| # | Item | Effect | Status |
|---|---|---|---|
| 1 | MON-02 query 2 (`errors-and-warnings-per-minute`) is malformed (`modules/web-entry/alarms.tf` lines 79 to 80), as predicted for the shared module | Cannot run on B either | **Open** (same as A) |
| 2 | First capacity-pin plans failed twice: uncommitted infrastructure change (guard working), then AccessDenied errors (lab credentials cancelled, by the policy name) | Each rerun succeeded | Kept as failed attempts; no action |
| 3 | At 512 users the single task failed load-balancer health checks twice and ECS replaced it (`ecs_events.json` 06:43:30 UTC) | The run's request log still shows 0 errors; the replacement registered after the run ended | Observation, not a defect; A showed a shorter health dip with no replacement |
| 4 | The shop data was reset after, not between, B's runs | B's saturation run started with the orders of its earlier runs present (299 load orders at the first reset) | Stated as a limit in [test-performance.md](test-performance.md) |

## Procedures

Carried forward from the retired stage guides (archived under `docs/archive/`). Commands run from `src/infrastructure/` unless stated; lab credentials must be exported first.

### S3 bucket (created with the CLI; lab constraint, 29 September 2026)

The lab's service control policy denies `s3:GetBucketObjectLockConfiguration`, which the `aws_s3_bucket` resource calls on every read, so the bucket is created once with the CLI and looked up with `data "aws_s3_bucket"`. Its public access block, ownership controls, versioning, encryption, lifecycle rule and TLS-only policy stay Terraform resources. On a fresh account, before the first apply:

```bash
B="inf2006-grp21-data-$(openssl rand -hex 8)"
aws s3api create-bucket --bucket "$B" --region us-east-1
aws s3api put-bucket-tagging --bucket "$B" --tagging \
  'TagSet=[{Key=Name,Value=inf2006-grp21-data},{Key=Project,Value=inf2006-grp21},{Key=Env,Value=evidence},{Key=ManagedBy,Value=cli}]'
echo "s3_bucket_name = \"$B\"" >> terraform.tfvars
```

`terraform destroy` removes the bucket's settings but not the bucket: empty it (all object versions) and delete it with the CLI afterwards.

### Secrets (containers by Terraform, values by CLI so they never enter state)

| Secret | JSON keys |
|---|---|
| `inf2006-grp21/web` | `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER` (runtime role), `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY` |
| `inf2006-grp21/migration` | the same keys; `POSTGRES_USER` is the migration owner. `migrate` is a Django command, so it needs `DJANGO_SECRET_KEY` too (copied from `web`) |
| `inf2006-grp21/trainer` | `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (read-only identity), nothing else |
| `inf2006-grp21/bootstrap` | the DB keys plus `MIGRATION_USER`, `MIGRATION_PASSWORD`, `BOOTSTRAP_USER`, `BOOTSTRAP_PASSWORD` |

The loader requires **exactly** each entrypoint's fields and refuses extra ones (`src/config/secrets.py`); `POSTGRES_PORT` is optional. Bootstrap's `POSTGRES_USER/PASSWORD` must equal `web`'s and its `MIGRATION_*` must equal `migration`'s. Always read the current secret back and add fields; **never regenerate a password after bootstrap**. Check the duplicated values with `jq` printing only `match` or `differ`. RDS rotates its managed master secret every 7 days: copy its `username` and `password` into `BOOTSTRAP_USER` and `BOOTSTRAP_PASSWORD` **immediately before each bootstrap run**, never ahead of time.

### Image build and push

```bash
docker build -t <ecr-url>:<git-sha> -f ../Dockerfile ..
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ecr-registry>
docker push <ecr-url>:<git-sha>
```

Tags are immutable, so a git-SHA tag always means one image; stacks run it by digest.

### One-off database jobs (order matters; on an instance or task inside the VPC)

1. Complete the secrets and run the `match` check.
2. `db_bootstrap`: `python tools/db_bootstrap.py` with the `bootstrap` secret (creates the runtime and migration logins and the database owned by the migration login; there is **no** initial database in RDS, because bootstrap refuses databases owned by another login).
3. `migrate`: `python manage.py migrate --noinput` with the `migration` secret.
4. Trainer login: part 1 (`src/infrastructure/sql/trainer_role_create.sql`) as the RDS master, part 2 (`trainer_role_grant.sql`) as the migration owner. The app image has no `psql` and `src/infrastructure/` is not in the image, so the two files go through the bucket (`aws s3 cp src/infrastructure/sql/ s3://<bucket>/ops/sql/ --recursive`), then on the host: install `postgresql17` and `jq`, copy the CA bundle out of the image (`docker run --rm --entrypoint cat <image> /app/certs/rds-global-bundle.pem`), fetch each secret, and run `psql` with `sslmode=verify-full` for each part, passing passwords through environment variables and unsetting them afterwards. Use `jq -er` so a missing key fails instead of becoming the text `null`.
5. Restart the web container or task; run `python manage.py check_database` with the `web` secret.
6. Dataset import (`import_dataset` from S3) once the app is reachable.

Least-privilege checks to record: the runtime login cannot `CREATE TABLE`; the trainer login cannot `INSERT`.

### Domain and DNS

Domain `fourtytwofactors.me` (Namecheap, GitHub Student Developer Pack, bought 29 September 2026). The AWS plan uses a Route 53 hosted zone, delegated from Namecheap once the zone exists (see the plan's DNS decision). Fallback: ACM validation CNAME and one CNAME per ALB at Namecheap, where the **Host** field must not include the domain (enter `_abc123.shop-ec2`, not `_abc123.shop-ec2.fourtytwofactors.me`), or the certificate stays pending. If HTTPS is late, build with an HTTP-only listener and do not claim HTTPS until it works.

## Lab capability record

Read-only probe of 25 September 2026 (`src/tools/aws_capability_check.py`; list/describe calls and EC2 dry runs only; nothing created), region `us-east-1`. Allowed: identity, availability zones (6), VPCs, creating a VPC (dry run), the AL2023 AMI lookup, launching an instance (dry run), listing ALBs, Auto Scaling groups, RDS, S3, instance profiles (`EMR_EC2_DefaultRole`, `LabInstanceProfile`), roles (including `LabRole`), Secrets Manager, ACM, Route 53 hosted zones, ECR, SSM, CloudWatch logs and alarms, SNS and Budgets. Default PostgreSQL engine version offered: 18.3 (the project pins 17). **Denied:** reading the on-demand vCPU service quota. Instance types: the probe tested only `t3.micro`, `t3.small` and `t3.medium` (all offered); other types such as `c5.large` are untested. Listing a service proves the API is reachable, not that creating it is permitted; creation is proved only by plan and apply.

Active checks of 29 September 2026, from a throwaway `t3.micro` under `LabInstanceProfile` (terminated afterwards, not part of the stack):

| Area | Check | Result |
|---|---|---|
| Identity | instance identity under `LabInstanceProfile` | allowed: `assumed-role/LabRole/<instance-id>` |
| Management | SSM agent registration, then `start-session` | allowed: `PingStatus: Online` in 1 to 2 minutes, no SSH key or port 22; the local `session-manager-plugin` is required |
| Secrets | create, retrieve and force-delete a secret from the instance | allowed (this is the exact call the app's startup loader makes) |
| WAF | create and delete a regional Web ACL | allowed |
| Cost | create and delete an AWS Budget | allowed |

Not tested: whether a running instance survives a Learner Lab session boundary. Learned by apply on 1 October 2026: Route 53 hosted-zone creation, `db.t4g.small`, an RDS-managed master password and `c5.large` are all allowed; Session Manager works inside the project VPC. Not yet tested: Multi-AZ, ECS and Fargate task roles (the professor confirmed ECS and Fargate work), SSM `SendCommand`. Lab balance at 29 September 2026: USD 0.20 of USD 50.00 used.
