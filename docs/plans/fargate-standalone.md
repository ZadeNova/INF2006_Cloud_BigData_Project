# Plan: variant B (Fargate) stands alone

Decision (9 Oct 2026): variant B is the final architecture; variant A stays as the evaluated alternative. Goal: a person
with an AWS Learner Lab and a domain rebuilds B from this repository alone: `up.sh base`, then `up.sh fargate`.

## Gap (found in the code)
- `up.sh fargate` refuses a fresh database ("run up.sh ec2 once first").
- `jobs.sh fargate` offers only bootstrap, migrate, check, refresh. `import` and `operator` exist only on A.
- `jobs.sh ... all` runs bootstrap even when the database is already set up, and bootstrap is not repeatable.
- The Fargate service waits for healthy tasks (`wait_for_steady_state`), so on a fresh database the first apply would
  fail: the jobs need the cluster and task definition, which only the apply creates.

## Changes
1. `fargate/variables.tf`: `min_capacity` and `desired_capacity` may be 0 (bring-up only; the default stays 1).
2. `scripts/jobs.sh`:
   - `fargate import` and `fargate operator` run as one-off tasks from the unchanged image (boto3 and psycopg are already
     in requirements.txt): the dataset comes from the bucket, the operator password is generated in the task and
     stored in the operator secret by boto3, never printed.
   - `all` works on both variants and skips bootstrap when `check_database` already passes (repeatable).
   - `trainer-sql` and `restart` stay A-only: the trainer login only serves offline ML training.
3. `scripts/up.sh fargate`: on a fresh database (shared secrets incomplete, or no operator secret) it fills the secrets,
   applies the stack with zero tasks (`bringup.auto.tfvars`, git-ignored), runs `jobs.sh fargate all`, removes the
   file, applies again (one task), checks and smoke-tests. On an existing database nothing changes.
4. Docs: README, GUIDE, runbook procedures, then ADR-018, REPRODUCE_CLOUD.md and RUN_LOADTEST.md.

## Verification
- `bash -n`, shellcheck if present, offline tests of the job command builders.
- One cloud session on B (about 30 minutes): `jobs.sh fargate all` against the existing database proves permissions and
  that every job is a safe no-op; it does NOT prove a from-nothing build (that needs a new domain delegation). State that.
