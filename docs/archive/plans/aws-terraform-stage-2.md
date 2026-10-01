# Stage 2 plan: RDS, and the first app instance for one-off jobs

> **Superseded in part (1 October 2026): read [aws-ecs-comparison.md](../../plans/aws-ecs-comparison.md) first.** It replaces this document's layout (now `base/`, `ec2/`, `fargate/`, no single root module), the ownership rule (a Claude session writes the Terraform; the user reviews and applies), the RDS size (`db.t4g.small`, was micro) and the stage order (do not apply stage 2 from the old single folder; split into `base/` and migrate state first). The project is comparing EC2 + ASG (A) with ECS on Fargate (B).

Part of [aws-terraform.md](aws-terraform.md). Status (29 September 2026): **code written and committed (`67dc066`), review gate passed with no blocking findings, review fixes applied; not yet planned or applied.** Same routine as stage 1: each step adds one file, is explained, and passes `fmt` and `validate`; the review gate reads the code before the first apply; nothing is applied until the last step.

## Scope change from the main plan

The launch template and Auto Scaling group move here from stage 3 (decided 29 September 2026, on the stage 1 reviewer's recommendation). `db_bootstrap`, `migrate` and the trainer-login SQL need a machine inside the VPC, because RDS is private. Rather than a throwaway instance, the first real app instance does the job. This also tests the boot script one stage earlier. Stage 3 then only adds the certificate, the ALB, the target group, the listeners and the ELB health check.

With no ALB yet, the web container may restart until the database is ready. That is harmless: the ASG uses EC2 health checks only in this stage, so nothing replaces the instance.

## What gets built

| # | File | Creates |
|---|---|---|
| 1 | `database.tf` | DB subnet group (private subnets), parameter group (`rds.force_ssl = 1`), RDS PostgreSQL 17 instance |
| 2 | `data.tf` | Lookups: the AL2023 AMI (SSM public parameter), `LabInstanceProfile` |
| 3 | `user_data.sh.tftpl` | Boot script: install Docker, log in to ECR, read the private IP from IMDSv2, run the web image by digest with the `awslogs` driver |
| 4 | `compute.tf` | Launch template (IMDSv2 required, encrypted EBS, public IP, `sg-app`), ASG min = max = desired = 1 |
| 5 | `outputs.tf` | RDS endpoint, the RDS-managed master secret ARN, ASG name |
| 6 | `sql/trainer_role_create.sql`, `sql/trainer_role_grant.sql` (under `src/infrastructure/`) | The two-step trainer login (see A1): part 1 as the master, part 2 as the migration owner |
| 7 | Review gate, then plan, apply, the one-off jobs and acceptance | |

## RDS settings

| Setting | Value | Why |
|---|---|---|
| Engine | PostgreSQL, `engine_version = "17"` with `auto_minor_version_upgrade = true` | The app, CI and all verification run on 17; major-only avoids a failed apply if a minor is withdrawn. Record the actual minor in the runbook |
| Class | `db.t4g.micro` (fall back to `db.t3.micro` if the lab refuses) | About USD 0.016–0.018 per hour |
| Storage | gp3, 20 GB, `storage_encrypted = true`, no autoscaling | The minimum is plenty |
| Network | `publicly_accessible = false`, private subnet group, `sg-db` only | The design from stage 1 |
| TLS | Parameter group with `rds.force_ssl = 1` | Already the default on 17, but explicit in code and evidence. The app uses `verify-full` with the bundled CA |
| Initial database | **None** (`db_name` unset) | `db_bootstrap` creates the database owned by the migration login; an initial database would be master-owned and refused |
| Master password | `manage_master_user_password = true` | RDS generates and stores it in its own secret; it never enters Terraform state |
| Backups | `backup_retention_period = 7` (decided 29 September 2026) | Free at this size; point-in-time restore for the last 7 days. A restore test in stage 5 turns this into evidence |
| Teardown | `skip_final_snapshot = true`, `deletion_protection = false`, `delete_automated_backups = true` | Fast, clean destroy. A manual snapshot during stage 5 is better evidence than a final snapshot |
| Changes | `apply_immediately = true` | Otherwise changes wait for the maintenance window |
| Monitoring | Enhanced Monitoring off (needs an IAM role the lab cannot create). Performance Insights optional | |
| Multi-AZ | Off | Cost; the subnet group spans two AZs, so it is a one-setting change, stated in the report |

## Environment for the web container

From `config/settings.py` and `config/secrets.py`. None of these is secret; the secret values come from Secrets Manager at startup.

| Variable | Stage 2 value |
|---|---|
| `DJANGO_ENV` | `production` (the default) |
| `AWS_SECRET_ID` / `AWS_REGION` | `inf2006-grp21/web` / `us-east-1` |
| `APP_RELEASE_ID` | the image's git SHA |
| `DJANGO_HEALTH_PROBE_HOST` | `<private-ip>:8000`, read from IMDSv2 at boot |
| `DJANGO_ALLOWED_HOSTS` | `var.app_hostname`. Required and must not be `*`; until the domain exists, a placeholder hostname, since nothing reaches the app except Session Manager |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<app_hostname>` |
| `DJANGO_TRUST_PROXY` | `false` in stage 2 (no ALB); `true` from stage 3 |
| `DJANGO_HSTS_SECONDS` | `3600` (the default) |

## Fixes from the stage 1 review, done in this stage

- **A1: trainer login.** Nothing creates `inf2006_trainer`. The migration owner cannot create logins (bootstrap makes it `NOCREATEROLE`), so there are two files: `sql/trainer_role_create.sql` (as the master: `CREATE ROLE inf2006_trainer LOGIN` with no other rights) and `sql/trainer_role_grant.sql` (as the migration owner). **Revised after the stage 2 review (M1):** part 2 grants `SELECT` on only the 9 tables the trainer and verifier read, plus `id`, `is_staff`, `is_superuser` of `auth_user`, and no default privileges. `django_session` (whose keys would allow session takeover) and password hashes stay unreadable. Security tests: `INSERT`, `django_session` and `auth_user.password` are all refused.
- **A3: secret fields.** The secret loader requires **exactly** each entrypoint's fields and refuses extra ones (`config/secrets.py`):
  - `bootstrap` needs `POSTGRES_DB/HOST/USER/PASSWORD` + `MIGRATION_USER/PASSWORD` + `BOOTSTRAP_USER/PASSWORD`. Its `POSTGRES_USER/PASSWORD` must equal `web`'s; its `MIGRATION_*` must equal `migration`'s.
  - **A3b (found while planning):** `migrate` is a Django command, so it loads the full app field set. The `migration` secret therefore also needs **`DJANGO_SECRET_KEY`**, copied from `web`. Without it, `migrate` fails at startup.
  - `web` and `migration` need `POSTGRES_DB/HOST` added; `trainer` needs `POSTGRES_DB/HOST` added and nothing else.
  - All updates read the current secret back and add fields; **no password is regenerated** (the runbook warning from stage 1). A `jq` check prints only `match`/`differ` for each duplicated value before bootstrap runs.
- **A4: rotating master password.** RDS rotates its managed master secret every 7 days. Copy `username`/`password` from it into `BOOTSTRAP_USER/PASSWORD` **immediately before each bootstrap run**, and set both back to a `replace-…` placeholder straight after (review L4): the secret loader refuses placeholders, so a stray bootstrap run fails safely. The trainer SQL reads the RDS secret directly and never uses the copy.

## One-off job order

Values from the review: `jq -e` everywhere, inside `set -e` blocks, so a missing key stops the commands instead of becoming the text `null` (L2; `jq -e` alone still prints `null`, it only sets the exit code). On the laptop, the field-list and `match` checks catch the same mistake; the helper is called by its full path, because `sudo`'s path may not include `/usr/local/bin` (L7). Secret values pass between commands through environment variables (`$ENV` in `jq`), never as command-line arguments. The application database is named `inf2006`.

**0. Mark the image as a release (before the plan; review L8).** From `src/infrastructure/` on the laptop. `terraform.tfvars` then says `image_tag = "release-<sha>"`:
```bash
SHA=c19d547
MANIFEST=$(aws ecr batch-get-image --repository-name inf2006-grp21-app --image-ids imageTag=$SHA --query 'images[0].imageManifest' --output text)
aws ecr put-image --repository-name inf2006-grp21-app --image-tag "release-$SHA" --image-manifest "$MANIFEST" >/dev/null && echo "tagged release-$SHA"
```

**1. Complete the secrets (laptop, after apply).**
```bash
s()   { aws secretsmanager get-secret-value --secret-id "inf2006-grp21/$1" --query SecretString --output text; }
put() { aws secretsmanager put-secret-value --secret-id "inf2006-grp21/$1" --secret-string "$2" >/dev/null && echo "$1 updated"; }
export HOST=$(terraform output -raw db_host) DBNAME=inf2006
export W=$(s web) M=$(s migration) T=$(s trainer) B=$(s bootstrap)
put web       "$(jq -ecn '($ENV.W|fromjson) + {POSTGRES_HOST: $ENV.HOST, POSTGRES_DB: $ENV.DBNAME}')"
put migration "$(jq -ecn '($ENV.M|fromjson) + {POSTGRES_HOST: $ENV.HOST, POSTGRES_DB: $ENV.DBNAME, DJANGO_SECRET_KEY: ($ENV.W|fromjson|.DJANGO_SECRET_KEY)}')"
put trainer   "$(jq -ecn '($ENV.T|fromjson) + {POSTGRES_HOST: $ENV.HOST, POSTGRES_DB: $ENV.DBNAME}')"
put bootstrap "$(jq -ecn '($ENV.B|fromjson) + {POSTGRES_HOST: $ENV.HOST, POSTGRES_DB: $ENV.DBNAME,
  POSTGRES_USER: ($ENV.W|fromjson|.POSTGRES_USER), POSTGRES_PASSWORD: ($ENV.W|fromjson|.POSTGRES_PASSWORD),
  BOOTSTRAP_USER: "replace-before-bootstrap", BOOTSTRAP_PASSWORD: "replace-before-bootstrap"}')"
# Check: prints only match/DIFFER and the key names, never values.
export W=$(s web) M=$(s migration) T=$(s trainer) B=$(s bootstrap)
jq -rn '($ENV.W|fromjson) as $w | ($ENV.M|fromjson) as $m | ($ENV.B|fromjson) as $b | ($ENV.T|fromjson) as $t |
  [["runtime login", $w.POSTGRES_USER == $b.POSTGRES_USER and $w.POSTGRES_PASSWORD == $b.POSTGRES_PASSWORD],
   ["migration login", $m.POSTGRES_USER == $b.MIGRATION_USER and $m.POSTGRES_PASSWORD == $b.MIGRATION_PASSWORD],
   ["signing key", $w.DJANGO_SECRET_KEY == $m.DJANGO_SECRET_KEY],
   ["host and db", ([$w,$m,$t,$b] | map(.POSTGRES_HOST, .POSTGRES_DB) | unique | length) == 2]]
  | .[] | "\(.[0]): \(if .[1] then "match" else "DIFFER" end)"'
jq -rn '[$ENV.W, $ENV.M, $ENV.T, $ENV.B] | map(fromjson | keys | join(","))[]'
unset W M T B
```

**2. Bootstrap.** Copy the master login in, run, then put the placeholder back straight away.
```bash
# laptop
export B=$(s bootstrap) R=$(aws secretsmanager get-secret-value --secret-id "$(terraform output -raw db_master_secret_arn)" --query SecretString --output text)
put bootstrap "$(jq -ecn '($ENV.B|fromjson) + {BOOTSTRAP_USER: ($ENV.R|fromjson|.username), BOOTSTRAP_PASSWORD: ($ENV.R|fromjson|.password)}')"; unset R
# instance (Session Manager)
sudo /usr/local/bin/app-job bootstrap python tools/db_bootstrap.py
# laptop, immediately after
export B=$(s bootstrap)
put bootstrap "$(jq -ecn '($ENV.B|fromjson) + {BOOTSTRAP_USER: "replace-before-bootstrap", BOOTSTRAP_PASSWORD: "replace-before-bootstrap"}')"; unset B
```

**3. Migrate (instance).** `sudo /usr/local/bin/app-job migration python manage.py migrate --noinput`

**4. Trainer login (part 1 as the master, part 2 as the migration owner).** The app image has no `psql` and `src/infrastructure/` is not in the image, so the SQL files go through the bucket. Laptop: `aws s3 cp sql/ "s3://$(terraform output -raw s3_bucket_name)/ops/sql/" --recursive`. Instance, with the bucket name and the master secret ARN pasted in (names, not secrets):
```bash
( set -euo pipefail   # jq -e still prints "null" for a missing key; its exit code must stop the block
sudo dnf install -y postgresql17 jq
sudo docker run --rm --entrypoint cat "$(sudo docker inspect --format '{{.Config.Image}}' web)" /app/certs/rds-global-bundle.pem > /tmp/rds-ca.pem
aws s3 cp "s3://<bucket>/ops/sql/" /tmp/sql/ --recursive
s() { aws secretsmanager get-secret-value --secret-id "$1" --query SecretString --output text; }
T=$(s inf2006-grp21/trainer); M=$(s inf2006-grp21/migration); R=$(s "<db_master_secret_arn>")
HOST=$(jq -er .POSTGRES_HOST <<<"$T"); DB=$(jq -er .POSTGRES_DB <<<"$T")
export TRAINER_USER=$(jq -er .POSTGRES_USER <<<"$T") TRAINER_PASSWORD=$(jq -er .POSTGRES_PASSWORD <<<"$T") APP_DB=$DB
PGPASSWORD=$(jq -er .password <<<"$R") psql "host=$HOST dbname=postgres user=$(jq -er .username <<<"$R") sslmode=verify-full sslrootcert=/tmp/rds-ca.pem" -f /tmp/sql/trainer_role_create.sql
PGPASSWORD=$(jq -er .POSTGRES_PASSWORD <<<"$M") psql "host=$HOST dbname=$DB user=$(jq -er .POSTGRES_USER <<<"$M") sslmode=verify-full sslrootcert=/tmp/rds-ca.pem" -f /tmp/sql/trainer_role_grant.sql
unset T M R TRAINER_PASSWORD
)
```
Verified against a disposable PostgreSQL 17 imitating RDS (29 September 2026): part 1 creates the login with every privilege flag false and is idempotent; after part 2 the trainer's real segment query runs, while `django_session`, `auth_user.password`, `SELECT *` on `auth_user`, an ungranted table and `INSERT` are all refused.

**5. Web.** `sudo docker restart web`, then `sudo /usr/local/bin/app-job web python manage.py check_database`.

**6.** Dataset import (`import_dataset` from S3) is **stage 3**, once the app is reachable and can be checked end to end.

**Accepted risk (review L3).** If a `CREATE/ALTER ROLE … PASSWORD` statement fails, PostgreSQL logs the whole statement, and the log export sends it to `/aws/rds/instance/inf2006-grp21-db/postgresql`. The scripts check before creating, so this is unlikely, and `db_bootstrap` has the same exposure. Error-statement logging stays on for the outage demo. After the jobs, search the RDS log group for `PASSWORD`; if a line appears, rotate that password and record it.

## Acceptance

- RDS: private, encrypted, engine 17.x, `rds.force_ssl = 1`, backups 7 days (redacted `describe-db-instances`).
- Instance: registered in SSM, no port 22, IMDSv2 required, container running from the ECR digest, logs arriving in `/inf2006-grp21/app`.
- Bootstrap, migrate and the trainer SQL succeed. `check_database` passes as the runtime login.
- Least privilege, tested: the runtime login cannot `CREATE TABLE`; the trainer login cannot `INSERT` or read `django_session` or `auth_user.password`.
- RDS log group searched for `PASSWORD` after the jobs (L3).
- Runbook entry with commits, redacted outputs and the lab balance.

## Open items (resolve before writing the step they affect)

- [ ] Confirm the lab accepts `db.t4g.micro` (plan will tell; apply is the proof).
- [x] `DJANGO_ALLOWED_HOSTS`: the domain exists (bought 29 September 2026 from Namecheap through the GitHub Student Developer Pack, first year free). The app hostname is `shop.<domain>`, set as `app_hostname` in `terraform.tfvars`, so no placeholder is needed.
- [ ] Session Manager on an instance **in our VPC** (step 7 only proved it in the default VPC): `sg-app` allows 443 outbound, so it should work; the acceptance check proves it.
- [x] A5 (decided 29 September 2026): the S3 CORS rule is removed; models and images stay static files served by WhiteNoise. Reasoning in [aws-terraform.md](aws-terraform.md#decisions-recorded-here), ready for report section 3.
- [ ] Decide before stage 3: the trainer image (A2).

## Cost while up

RDS about USD 0.018/hour, the t3.small about 0.021/hour, its public IPv4 address 0.005/hour: **about USD 0.045/hour, roughly USD 1.10 per day.** Destroy between sessions if the stack will sit idle for more than a day.
