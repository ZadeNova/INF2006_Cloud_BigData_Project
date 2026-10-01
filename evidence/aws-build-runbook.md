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
| Teardown `down.sh ec2` | `12d0e44` and later | To be recorded |

Not yet done: the WAF block-mode test, any alarm firing, a scale-out, a recovery test and the Logs Insights export; these are the evidence runs.

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
