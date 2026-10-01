# ADR-005: Three small scripts for plan/apply, the image, and the secrets

**Status:** drafted by the writing session for review (1 October 2026).

## Decision

Repeated, error-prone steps are scripts under `src/infrastructure/scripts/`, small and idempotent, with no framework, each stopping at its first failure:

- `tf.sh <folder> plan|apply`: refuses a dirty tree, runs `fmt -check`, `init`, `validate`, a saved plan, and records the commit it was made from; `apply` runs only that saved plan and only if HEAD is still that commit, then backs up the state.
- `push-image.sh [sha]`: builds only the current commit and only if its tag is absent from ECR, pushes, adds the protected `release-<sha>` tag, prints the digest, and writes `image_tag` for both stacks.
- `secrets.sh fill|check|master-in|master-out`: adds missing secret fields, never changes a stored password or key, re-derives the copies the secrets contract requires, prints only key names and `match`/`DIFFER`.

Terraform builds infrastructure; scripts run the jobs around it. No Terraform provisioners, because the one-off database jobs must run inside the VPC.

## Options considered

| Option | Why not |
|---|---|
| Documented commands only | The earlier stages went wrong in the commands: a literal `...` pasted as a credential, `null` stored as a value, a password echoed. Scripts stop on the first failure and check first |
| Terraform provisioners or `aws_secretsmanager_secret_version` | A secret value set in Terraform lands in state in plain text |
| CI/CD pipeline | The lab cannot create the IAM role or OIDC link a pipeline needs; the image push stays manual by necessity |
| A task runner or framework | More moving parts than three short shell scripts |

## Driver (shop scenario)

Each experiment run rebuilds a stack, so every manual step is repeated many times; a mistake in one (a stale plan, a regenerated database password, an image rebuilt under an old tag) invalidates evidence. The scripts make the safe path the short one and put the applied commit into the record.

## Consequences

- A password is never regenerated, because after `db_bootstrap` the database holds the stored one. `master-in` is run only immediately before bootstrap, because RDS rotates the master password every 7 days.
- Secret values pass through environment variables and a private temporary file, never through command-line arguments.
- `push-image.sh` never rebuilds a tag that exists, so the recorded digest stays the same across variants.

## Evidence that will back it

Tested offline against a fake `aws`: a first `fill` gives exactly the field sets the loader accepts and all checks `match`; a second `fill` changes nothing; `master-in` and `master-out` round-trip. Then run for real, with the output in the runbook.

## Revisit when

A step needs branching logic the scripts cannot express in a few lines, or the lab allows a pipeline.
