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

Not tested: whether a running instance survives a Learner Lab session boundary. Not yet tested: Route 53 hosted-zone creation, Multi-AZ, ECS and Fargate task roles (the professor confirmed ECS and Fargate work), SSM `SendCommand`, `c5.large`. Lab balance at 29 September 2026: USD 0.20 of USD 50.00 used.
