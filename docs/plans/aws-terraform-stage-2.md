# Stage 2 plan: RDS, and the first app instance for one-off jobs

Part of [aws-terraform.md](aws-terraform.md). Status (29 September 2026): **planned, not started.** Same routine as stage 1: each step adds one file, is explained, and passes `fmt` and `validate`; the review gate reads the code before the first apply; nothing is applied until the last step.

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
| 6 | `sql/trainer_role.sql` (under `src/infrastructure/`) | The two-step trainer login (see A1) |
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

- **A1: trainer login.** Nothing creates `inf2006_trainer`. The migration owner cannot create logins (bootstrap makes it `NOCREATEROLE`), so `sql/trainer_role.sql` has two parts: as the master, `CREATE ROLE inf2006_trainer LOGIN` with no other rights; as the migration owner, `GRANT CONNECT`, schema `USAGE`, `SELECT` on all tables and matching default privileges. Security test: an `INSERT` as the trainer fails with `permission denied`.
- **A3: secret fields.** The secret loader requires **exactly** each entrypoint's fields and refuses extra ones (`config/secrets.py`):
  - `bootstrap` needs `POSTGRES_DB/HOST/USER/PASSWORD` + `MIGRATION_USER/PASSWORD` + `BOOTSTRAP_USER/PASSWORD`. Its `POSTGRES_USER/PASSWORD` must equal `web`'s; its `MIGRATION_*` must equal `migration`'s.
  - **A3b (found while planning):** `migrate` is a Django command, so it loads the full app field set. The `migration` secret therefore also needs **`DJANGO_SECRET_KEY`**, copied from `web`. Without it, `migrate` fails at startup.
  - `web` and `migration` need `POSTGRES_DB/HOST` added; `trainer` needs `POSTGRES_DB/HOST` added and nothing else.
  - All updates read the current secret back and add fields; **no password is regenerated** (the runbook warning from stage 1). A `jq` check prints only `match`/`differ` for each duplicated value before bootstrap runs.
- **A4: rotating master password.** RDS rotates its managed master secret every 7 days. Copy `username`/`password` from it into `BOOTSTRAP_USER/PASSWORD` **immediately before each bootstrap run**, never ahead of time.

## One-off job order (over Session Manager, on the ASG instance)

1. Complete the secrets (A3, A4) and run the match check.
2. `docker run --rm -e AWS_SECRET_ID=inf2006-grp21/bootstrap -e AWS_REGION=us-east-1 <image> python tools/db_bootstrap.py`
3. `docker run --rm -e AWS_SECRET_ID=inf2006-grp21/migration ... <image> python manage.py migrate --noinput`
4. Trainer login: part 1 as the master, part 2 as the migration owner (`sql/trainer_role.sql`).
5. Restart the web container; `python manage.py check_database` with the `web` secret.
6. Dataset import (`import_dataset` from S3) is **stage 3**, once the app is reachable and can be checked end to end.

## Acceptance

- RDS: private, encrypted, engine 17.x, `rds.force_ssl = 1`, backups 7 days (redacted `describe-db-instances`).
- Instance: registered in SSM, no port 22, IMDSv2 required, container running from the ECR digest, logs arriving in `/inf2006-grp21/app`.
- Bootstrap, migrate and the trainer SQL succeed. `check_database` passes as the runtime login.
- Least privilege, tested: the runtime login cannot `CREATE TABLE`; the trainer login cannot `INSERT`.
- Runbook entry with commits, redacted outputs and the lab balance.

## Open items (resolve before writing the step they affect)

- [ ] Confirm the lab accepts `db.t4g.micro` (plan will tell; apply is the proof).
- [x] `DJANGO_ALLOWED_HOSTS`: the domain exists (bought 29 September 2026 from Namecheap through the GitHub Student Developer Pack, first year free). The app hostname is `shop.<domain>`, set as `app_hostname` in `terraform.tfvars`, so no placeholder is needed.
- [ ] Session Manager on an instance **in our VPC** (step 7 only proved it in the default VPC): `sg-app` allows 443 outbound, so it should work; the acceptance check proves it.
- [x] A5 (decided 29 September 2026): the S3 CORS rule is removed; models and images stay static files served by WhiteNoise. Reasoning in [aws-terraform.md](aws-terraform.md#decisions-recorded-here), ready for report section 3.
- [ ] Decide before stage 3: the trainer image (A2).

## Cost while up

RDS about USD 0.018/hour, the t3.small about 0.021/hour, its public IPv4 address 0.005/hour: **about USD 0.045/hour, roughly USD 1.10 per day.** Destroy between sessions if the stack will sit idle for more than a day.
