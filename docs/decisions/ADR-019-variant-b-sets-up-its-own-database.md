# ADR-019: Variant B sets up its own database (amends ADR-017, section 2)

**Status:** decided 9 October 2026, with [ADR-018](ADR-018-final-architecture-ecs-fargate.md).

## Context

ADR-017 gave `jobs.sh fargate` four jobs (`bootstrap`, `migrate`, `check`, `refresh`) and told a new account to run `up.sh ec2` once first, because the import and the operator login needed tools the frozen image lacks. With B as the final architecture that is a defect: a person rebuilding the final system should not have to build the alternative first.

## Decision

1. **`jobs.sh fargate` gains `import`, `operator` and `all`**, as one-off ECS tasks from the unchanged image (backend and Dockerfile frozen). `boto3` and `psycopg` are already in `requirements.txt`: `import` downloads the checksum-verified dataset from the bucket and runs the app's own create-only `import_dataset`; `operator` generates the password inside the task, passes it to `seed_demo` through that one process's environment, and stores it in the operator secret with boto3. It is never printed, never on a command line, never in Terraform. Programs: `src/infrastructure/scripts/fargate_jobs/`.
2. **`up.sh fargate` handles a fresh database.** The service waits for healthy tasks (`wait_for_steady_state`) and a task cannot be healthy before the database exists, so on a fresh database it fills the secrets, applies with **zero tasks** (`bringup.auto.tfvars`, git-ignored; `min_capacity` and `desired_capacity` may now be 0), runs `jobs.sh fargate all`, removes the file and applies again with one task. An already set-up database skips this.
3. **`jobs.sh ... all` skips bootstrap when `check_database` already passes** (both variants). Bootstrap is not repeatable on an existing database; this removes the failure seen when `up.sh ec2` re-ran on 8 October.
4. **`trainer-sql` and `restart` stay on variant A only.** The trainer login serves the offline ML training in `analytics/`, not the shop.

## Alternatives not chosen

| Alternative | Why not |
|---|---|
| Keep "run A once first" | Contradicts "anyone can run B"; builds a stack the final system does not use. |
| Add `psql` and the AWS CLI to the image | Changes the frozen image and enlarges the attack surface of the running container. |
| Run the jobs from a laptop | RDS is private (no public access), so a laptop cannot reach it. |
| One apply on a fresh database | The apply would wait for tasks that cannot be healthy and fail before the jobs could run. |

## Consequences and limits

- Tested **offline** with a stubbed `aws` and `terraform` (routing, skip logic, task overrides) and with the two programs against a stubbed `boto3`. **Not run in AWS** at the time of writing; a from-nothing rebuild would also need a new domain delegation. See [REPRODUCE_CLOUD.md](../REPRODUCE_CLOUD.md) for what has and has not been proven.
- While zero tasks run, the no-healthy-hosts alarm may send one email during bring-up.
- If the first run stops between the two applies, the stack holds zero tasks until `up.sh fargate` is run again.
