# ADR-009: Database and data jobs run by `jobs.sh` through SSM Run Command

**Status:** implemented; the stacks it describes were applied and measured on 8 and 9 October 2026 (first drafted 1 October 2026). Variant A uses SSM Run Command; the Fargate branch (`aws ecs run-task`) was added with `fargate/` and amended by [ADR-019](ADR-019-variant-b-sets-up-its-own-database.md).

## Decision

`scripts/jobs.sh ec2 <job>` runs each one-off job on the stack's instance with `aws ssm send-command` (document `AWS-RunShellScript`) and prints the output. Jobs: `bootstrap`, `migrate`, `trainer-sql`, `restart` (restart the web container and run `check_database`), `check`, `import`, and `all` (bootstrap, migrate, trainer-sql, restart). `bootstrap` copies the RDS master login into the bootstrap secret for the run only and puts the placeholder back on any exit. `trainer-sql` and `import` stage their files through the private bucket, because the app image contains neither `psql`, the SQL, nor the dataset (the Docker context is `src/`). The jobs run inside the VPC on the instance, using the instance's role, so no database port is opened to the laptop.

## Options considered

| Option | Why not |
|---|---|
| Typing the commands in a Session Manager shell (done once, by hand, on 1 October) | Proven, but error-prone (a mistyped job name, a wrong path) and not repeatable; the comparison needs the same jobs on a fresh database for each variant |
| Terraform provisioners or `local-exec` | The jobs must run inside the VPC, and a provisioner would tie database state to infrastructure state |
| Run `psql` and `manage.py` from the laptop | Needs RDS reachable from outside the VPC, which `sg-db` forbids |
| Bake the jobs into user data | A job that fails would fail the boot; and they are one-time, not per instance |
| **SSM Run Command from a script (chosen)** | Inside the VPC, auditable in CloudTrail, one command per job, no interactive shell |

## Driver (shop scenario)

Each recorded run rebuilds a stack against a database that is either fresh or kept; the jobs must be a single repeatable command, and the marker's cloud-reproduction guide must list them as commands, not as typing.

## Consequences

- Needs the lab to allow `ssm:SendCommand` for the caller; if refused, the script says so and the manual session commands in the runbook still work (this is the open question the plan listed).
- Output is capped by SSM (about 24 000 characters), enough for these jobs; nothing secret is printed, because secrets are read on the instance and passed through environment variables.
- `import` is not repeatable on a namespace that already holds demo products; the others are.

## Evidence that will back it

Each job's printed output in the runbook; `check_database` returning `{"database": "ok", "migrations": "applied"}`; the bootstrap secret holding the placeholder afterwards.

## Revisit when

The lab denies `SendCommand` (use a non-interactive Session Manager session), or the Fargate variant needs a shared interface.
