# ADR-010: Operator login in its own secret, and the `up`, `down` and `smoke` scripts

**Status:** drafted by the writing session for review (1 October 2026).

## Decision

- **Operator account.** `seed_demo --no-products` refuses to run outside local without `DEMO_OPERATOR_PASSWORD`. `jobs.sh ec2 operator` generates a random password **on the instance**, runs the command with it, and stores `{username, password}` in a fifth Secrets Manager secret, `inf2006-grp21/operator`, whose container Terraform creates in `base/`. The app never reads it; a person reads it when logging in as `demo-operator`. The job skips if the secret already holds a value, so a rerun cannot replace a password the database does not have.
- **`up.sh <stack>`**: saved plan shown, you confirm, apply that plan, `secrets.sh fill`, `jobs.sh <stack> all`, `smoke.sh`. **`down.sh <stack>`**: destroy the stack, then list leftover load balancers, instances and NAT gateways. **`smoke.sh <stack|host>`**: eight black-box checks (health, redirect, certificate, login page, products listed, three security headers), needing only `curl` and `openssl`.
- `jobs.sh ... all` is the full set for a fresh database, and is idempotent.

## Options considered

| Option | Why not |
|---|---|
| Pass the operator password as an SSM command parameter or a Terraform variable | It would be stored in the SSM command history, CloudTrail or Terraform state |
| Put it in the web secret | The app's loader refuses extra fields (`src/config/secrets.py`), and the backend is frozen |
| A fixed, committed password | A known credential on a public site |
| No operator account | The operator dashboard, a required workflow, could not be demonstrated |
| **Generated on the instance, own secret (chosen)** | The password never crosses SSM or Terraform; read access is a normal, auditable secrets call |

## Driver (shop scenario)

The operator workflow (analytics) is part of the shop and of the evidence, and the brief rewards reproducible deployment: a reviewer needs one command to a working, checked stack, and a way to take it down without leftovers.

## Consequences

- `smoke.sh` needs no AWS credentials, so a marker could run it against any deployment, and it doubles as the functional smoke evidence.
- `down.sh` leaves `base/` running by design; its output says so.
- Anyone with `secretsmanager:GetSecretValue` on the operator secret can read the operator password; in the lab that is every user of `LabRole`.

## Evidence that will back it

`jobs.sh ec2 all` output on a fresh database; `smoke.sh` output; logging in as `demo-operator` with the stored password; `down.sh` leftover lists empty.

## Revisit when

The app reads operator credentials from its own secret, or the Fargate variant needs the same job through `run-task`.
