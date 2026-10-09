# Reproducing the project

Final architecture: variant B, ECS on Fargate ([ADR-018](decisions/ADR-018-final-architecture-ecs-fargate.md)). This page says what a marker or teammate can reproduce, with what, at what cost, and **what has and has not been proven**. Marking needs only level 1.

| Level | What you reproduce | You need | Cost |
|---|---|---|---|
| **1. Offline** | The application, its tests, the analytics, and the load-test tables from the recorded raw files | Docker, Python 3 | none |
| **2. Cloud, variant B** | The deployed shop, built from the Terraform and scripts | An AWS Academy Learner Lab, a domain you control, the tools below | about USD 3.5 per day while running, plus about USD 1.2 per day for the shared base (list prices checked 9 October 2026) |
| **3. Load test** | A run of the load harness against your own stack B | Level 2, plus one more small instance | about USD 0.1 per hour for the generator |

## Level 1: offline (no AWS)

From the repository root, with Docker running:

```bash
python src/tools/init_env.py                      # once: writes local secrets (existing files are kept)
docker compose up --build -d                      # the shop at http://127.0.0.1:8000/
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests     # the automated tests
docker compose run --rm web python manage.py check_database              # expect it to report success
```

Demo data (catalogue, history, operator login, analytics) and the analytics scripts: [src/README.md](../src/README.md) and [analytics/README.md](../analytics/README.md).

Re-derive the load-test tables from the recorded raw evidence (no cloud, any machine with Python 3):

```bash
python tests/load/analyze.py --raw evidence/raw --out /tmp/load-summary.md     # compare with evidence/load-summary.md
python tests/load/selftest.py                                                  # the harness's own checks (16)
```

## Level 2: build variant B in your own Learner Lab

**Prerequisites.** A Learner Lab (region `us-east-1`, the only one the lab offers). **A domain you control**: HTTPS needs a certificate and the app enforces HTTPS, so this is the one input that cannot be shared (our `fourtytwofactors.me` can point at only one Route 53 zone at a time). Tools: Terraform 1.10 or newer, AWS CLI v2, `jq`, `openssl`, `curl`, `git`, `python3`, Docker. Details and the `labcreds` helper: [src/infrastructure/README.md](../src/infrastructure/README.md#tools-and-credentials). Lab credentials last about 4 hours; the scripts check them first.

```bash
git clone <repo-url> && cd <repo>
labcreds                                          # paste the lab's AWS CLI block, then an empty line
src/infrastructure/scripts/status.sh              # tools and credentials ok? it says what to do next
src/infrastructure/scripts/up.sh base             # asks for an alarm email and your domain; shows the plan; type yes
```

While `up.sh base` waits for the certificate it prints four name servers: set them at your registrar (custom DNS). RDS takes about 9 minutes. Then confirm the email AWS sends, or alarms reach no one.

```bash
src/infrastructure/scripts/up.sh fargate          # image, secrets, database jobs, the service, smoke test
```

On a **fresh database** this fills the secrets, creates the stack with zero tasks, runs every database job as a one-off task (bootstrap, migrate, import the dataset, create the operator login, refresh analytics), then applies again with one task, checks the database and runs the smoke test ([ADR-019](decisions/ADR-019-variant-b-sets-up-its-own-database.md)). You do not need variant A.

**Expected result:** `All checks passed.` (smoke 8 of 8) and the shop at `https://shop-fargate.<your domain>`. The operator password is in Secrets Manager (never printed):

```bash
aws secretsmanager get-secret-value --secret-id inf2006-grp21/operator --query SecretString --output text
```

**Stop paying:** `src/infrastructure/scripts/down.sh fargate` after each session. When you are finished with everything, follow "Final teardown" in the infrastructure README (it also removes the shared base).

### What has and has not been proven

| Claim | Status |
|---|---|
| The Terraform and scripts build variant B from the repository and pass `smoke.sh` 8 of 8 | **Proven in AWS** on 9 October 2026 (first apply: 27 resources added, 0 failed): [evidence/aws-build-runbook.md](../evidence/aws-build-runbook.md) |
| The shop works under load, scales out and replaces a task with 0 errors | **Proven in AWS**, one repeat, indicative: [evidence/load-summary.md](../evidence/load-summary.md) |
| `up.sh fargate` and `jobs.sh fargate all` set up a fresh database without variant A | **Tested offline only** (a stubbed `aws` and a stubbed `boto3`: routing, skip logic, task overrides, password handling). **Not run in AWS.** |
| A rebuild from a completely empty account and a new domain | **Not done.** It needs a new domain delegation. The base and Fargate stacks were each applied from empty state on our account, but the database jobs ran against a database variant A had already set up |

If the fresh-database path fails on your account, the fallback is the order we actually ran: `up.sh base`, `up.sh ec2` (sets up the database), then `up.sh fargate`.

## Level 3: run the load test

[RUN_LOADTEST.md](RUN_LOADTEST.md).
